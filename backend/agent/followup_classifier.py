"""
Follow-up 판별기

목적: "후속 요청 vs 새 요청"을 구분하여 컨텍스트 유지/리셋 결정

사용처:
- 사용자 요청이 들어올 때 이전 대화와의 관계 판단
- 프레임(frame) 유지/리셋 결정
- 제약 조건 carryover 정책 적용
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =================================================================
# 1. 판별 스키마
# =================================================================

class FollowUpIntent(BaseModel):
    """
    Follow-up 판별 결과

    Fields:
        is_followup: 이전 요청과 연속성이 있는가?
        intent: 사용자 의도 분류
        keep_slots: 유지할 제약 조건 필드명 리스트
        drop_slots: 제거할 제약 조건 필드명 리스트
        confidence: 판별 신뢰도 (0.0 ~ 1.0)
        reason: 판별 근거 (한글, 디버깅용)
    """
    is_followup: bool = Field(description="이전 대화와 연속성이 있는가?")

    intent: Literal[
        "MORE_RECO",      # 더 추천해줘 (동일 조건)
        "MODIFY_RECO",    # 조건 일부 변경 추천
        "NEW_RECO",       # 완전히 새로운 추천
        "INFO_QUERY",     # 정보 질문 (추천 아님)
        "RESET"           # 명시적 리셋 요청
    ] = Field(description="사용자 의도 분류")

    keep_slots: List[str] = Field(
        default_factory=list,
        description="유지할 제약 조건 (예: ['brand', 'season'])"
    )

    drop_slots: List[str] = Field(
        default_factory=list,
        description="제거할 제약 조건 (예: ['target', 'occasion'])"
    )

    confidence: float = Field(
        ge=0.0, le=1.0,
        description="판별 신뢰도 (0.0 ~ 1.0)"
    )

    reason: str = Field(
        description="판별 근거 (한글, 로깅용)"
    )


# =================================================================
# 2. 규칙 기반 패턴
# =================================================================

# 후속 요청 키워드 (MORE_RECO 또는 MODIFY_RECO)
FOLLOWUP_KEYWORDS = [
    # 더 추천
    "더 추천", "더", "다른 거", "다른 것", "다른것", "또", "추가로",
    "비슷한", "유사한", "이거 말고", "이것 말고", "다른 향수",

    # 변형
    "대신", "그 외", "다른", "더 보여",
]

# 새 요청 키워드 (NEW_RECO 또는 RESET)
NEW_REQUEST_KEYWORDS = [
    # 명시적 리셋
    "새로", "처음부터", "다시", "아까 건", "아까거", "전에 건", "잊고",

    # 주제 전환 신호
    "이번엔", "근데", "그리고", "참고로",
]

# 대상 전환 키워드 (NEW_RECO 강력 신호)
TARGET_CHANGE_KEYWORDS = [
    # 수신자 변경
    "부모님", "엄마", "아빠", "어머니", "아버지",
    "남자친구", "남친", "여자친구", "여친",
    "친구", "동생", "언니", "오빠", "형", "누나",
    "선배", "후배", "동료", "상사",

    # 상황 변경
    "선물", "gift", "present",
    "회사", "데이트", "모임", "파티",
]

# 정보 질문 키워드 (INFO_QUERY)
INFO_KEYWORDS = [
    "뭐야", "뭔가", "어떤", "무슨", "설명", "알려",
    "어때", "차이", "비교", "vs", "대",
    "성분", "노트", "향", "지속", "확산",
]


# =================================================================
# 3. 규칙 기반 판별 함수
# =================================================================

def classify_followup_rule_based(
    current_query: str,
    previous_context: Optional[dict] = None,
) -> FollowUpIntent:
    """
    규칙 기반 follow-up 판별

    Args:
        current_query: 현재 사용자 쿼리
        previous_context: 이전 대화 컨텍스트 (user_preferences 등)

    Returns:
        FollowUpIntent: 판별 결과
    """
    query_lower = current_query.lower().strip()

    # 이전 컨텍스트가 없으면 무조건 NEW_RECO
    if not previous_context or not previous_context.get("user_preferences"):
        return FollowUpIntent(
            is_followup=False,
            intent="NEW_RECO",
            keep_slots=[],
            drop_slots=[],
            confidence=1.0,
            reason="이전 대화 기록 없음 (첫 요청)"
        )

    # === 규칙 1: 정보 질문 감지 ===
    if any(keyword in query_lower for keyword in INFO_KEYWORDS):
        return FollowUpIntent(
            is_followup=False,
            intent="INFO_QUERY",
            keep_slots=[],
            drop_slots=[],
            confidence=0.8,
            reason=f"정보 질문 키워드 감지: {[k for k in INFO_KEYWORDS if k in query_lower]}"
        )

    # === 규칙 2: 명시적 리셋 ===
    reset_matches = [k for k in NEW_REQUEST_KEYWORDS if k in query_lower]
    if reset_matches:
        return FollowUpIntent(
            is_followup=False,
            intent="RESET",
            keep_slots=[],
            drop_slots=["accord", "brand", "gender", "like", "note", "occasion", "reference_brand", "season", "situation", "style", "target"],
            confidence=0.9,
            reason=f"리셋 키워드 감지: {reset_matches}"
        )

    # === 규칙 3: 대상 전환 감지 (강력한 NEW_RECO 신호) ===
    target_matches = [k for k in TARGET_CHANGE_KEYWORDS if k in query_lower]
    if target_matches:
        return FollowUpIntent(
            is_followup=False,
            intent="NEW_RECO",
            keep_slots=[],  # 모든 제약 제거
            drop_slots=["accord", "brand", "gender", "like", "note", "occasion", "reference_brand", "season", "situation", "style", "target"],
            confidence=0.95,
            reason=f"대상 전환 키워드 감지: {target_matches}"
        )

    # === 규칙 4: 후속 요청 (MORE_RECO) ===
    followup_matches = [k for k in FOLLOWUP_KEYWORDS if k in query_lower]
    if followup_matches:
        # 모든 기존 제약 유지
        prev_prefs = previous_context.get("user_preferences", {})
        keep_slots = [k for k, v in prev_prefs.items() if v is not None]

        return FollowUpIntent(
            is_followup=True,
            intent="MORE_RECO",
            keep_slots=keep_slots,
            drop_slots=[],
            confidence=0.85,
            reason=f"후속 요청 키워드 감지: {followup_matches}"
        )

    # === 규칙 5: 애매한 경우 (기본값: NEW_RECO, 낮은 신뢰도) ===
    # 짧은 쿼리면 후속일 가능성
    if len(query_lower) < 10:
        prev_prefs = previous_context.get("user_preferences", {})
        keep_slots = [k for k, v in prev_prefs.items() if v is not None]

        return FollowUpIntent(
            is_followup=True,
            intent="MORE_RECO",
            keep_slots=keep_slots,
            drop_slots=[],
            confidence=0.5,  # 낮은 신뢰도
            reason="짧은 쿼리 → 후속 추정 (낮은 신뢰도)"
        )

    # 기본값: NEW_RECO (중간 신뢰도)
    return FollowUpIntent(
        is_followup=False,
        intent="NEW_RECO",
        keep_slots=[],
        drop_slots=["brand", "season", "occasion", "target", "style", "accord", "note"],
        confidence=0.6,
        reason="명확한 패턴 없음 → 새 요청으로 간주"
    )


# =================================================================
# 4. Public API (Wrapper for graph integration)
# =================================================================

def classify_followup(
    current_query: str,
    recent_messages: Optional[list] = None,
    current_constraints: Optional[dict] = None,
) -> FollowUpIntent:
    """
    Follow-up 판별 공개 API
    
    Graph에서 호출하는 안정적인 인터페이스.
    내부적으로 규칙 기반 분류기를 호출함.
    
    Args:
        current_query: 현재 사용자 쿼리
        recent_messages: 최근 대화 메시지 리스트 (선택)
        current_constraints: 현재 제약 조건 dict (선택)
    
    Returns:
        FollowUpIntent: 판별 결과
    """
    # Build previous_context for rule-based classifier
    previous_context = {
        "messages": recent_messages or [],
        "user_preferences": current_constraints or {},
    }
    
    return classify_followup_rule_based(current_query, previous_context)


# =================================================================
# 5. 확인 질문이 필요한지 판단
# =================================================================

def should_ask_confirmation(result: FollowUpIntent) -> bool:
    """
    사용자에게 확인 질문을 해야 하는가?

    낮은 신뢰도(< 0.7)일 때 확인 질문 권장
    단, 질문 상한 정책과 충돌하지 않도록 주의
    """
    return result.confidence < 0.7


# =================================================================
# 6. 사용 예시 (주석)
# =================================================================

"""
예시 1: "더 추천해줘"
→ FollowUpIntent(
    is_followup=True,
    intent="MORE_RECO",
    keep_slots=["brand", "season", "gender"],
    drop_slots=[],
    confidence=0.85,
    reason="후속 요청 키워드 감지: ['더 추천']"
)

예시 2: "부모님 선물로"
→ FollowUpIntent(
    is_followup=False,
    intent="NEW_RECO",
    keep_slots=[],
    drop_slots=["brand", "season", "occasion", "target", ...],
    confidence=0.95,
    reason="대상 전환 키워드 감지: ['부모님', '선물']"
)

예시 3: "아까 건 잊고 다시"
→ FollowUpIntent(
    is_followup=False,
    intent="RESET",
    keep_slots=[],
    drop_slots=[...],
    confidence=0.9,
    reason="리셋 키워드 감지: ['아까 건', '잊고', '다시']"
)
"""
