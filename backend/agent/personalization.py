"""
개인화 신호 요약 및 주입

tb_member_my_perfume_t 기반 사용자 취향을 분석하여
추천 시스템에 주입할 수 있는 형태로 요약합니다.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from .archive_db import get_my_perfumes, get_perfume_notes_and_accords

# =================================================================
# 개인화 신호 가중치 설정
# =================================================================

# 1. 선호도 가중치 (preference)
PREFERENCE_WEIGHTS = {
    "GOOD": 2.0,      # 좋아하는 향수 (양수)
    "NEUTRAL": 0.0,   # 중립 (영향 없음)
    "BAD": -3.0,      # 싫어하는 향수 (음수, 더 강한 패널티)
}

# 기본값 (DB에 없는 값이 들어올 경우)
DEFAULT_PREFERENCE_WEIGHT = 0.0


# 2. 등록 상태 가중치 (register_status)
# 최종 점수 = PREFERENCE_WEIGHT × REGISTER_STATUS_MULTIPLIER
REGISTER_STATUS_MULTIPLIERS = {
    "HAVE": 1.0,         # 현재 소유 중 (최대 신뢰도)
    "HAD": 0.5,          # 과거 소유 (중간 신뢰도)
    "RECOMMENDED": 0.7,  # 추천받았던 향수 (중상 신뢰도)
}

# 기본값
DEFAULT_REGISTER_STATUS_MULTIPLIER = 0.3


# 3. 최근성 가중치 (recency)
RECENT_COUNT = 10          # 최신 10개
RECENT_MULTIPLIER = 1.2    # 최신 향수는 20% 가중치 증가
OLD_MULTIPLIER = 1.0       # 기본 가중치


# 4. 집계 설정
MAX_LIKED_PERFUMES = 5     # 좋아하는 향수 Top 5
MAX_DISLIKED_PERFUMES = 5  # 싫어하는 향수 Top 5
QUERY_LIMIT = 20           # 최근 20개 향수만 조회 (성능)


# [★추가] Notes/Accords 개인화 설정
TOP_N_NOTES_ACCORDS = 3  # 프롬프트에 노출할 최대 개수
MIN_SUPPORT_COUNT = 2    # 최소 N개 향수에서 등장해야 신뢰할 수 있음


def calculate_personalization_score(
    preference: str,
    register_status: str,
    recency_rank: int,
) -> float:
    """
    개인화 점수 계산

    Args:
        preference: GOOD/NEUTRAL/BAD
        register_status: HAVE/HAD/RECOMMENDED
        recency_rank: 0부터 시작 (0이 가장 최근)

    Returns:
        float: 개인화 점수 (양수=선호, 음수=비선호)
    """
    # 1. 선호도 점수
    pref_weight = PREFERENCE_WEIGHTS.get(preference, DEFAULT_PREFERENCE_WEIGHT)

    # 2. 등록 상태 배수
    status_mult = REGISTER_STATUS_MULTIPLIERS.get(
        register_status, DEFAULT_REGISTER_STATUS_MULTIPLIER
    )

    # 3. 최근성 배수
    recency_mult = RECENT_MULTIPLIER if recency_rank < RECENT_COUNT else OLD_MULTIPLIER

    # 최종 점수
    return pref_weight * status_mult * recency_mult


def get_personalization_summary(member_id: int) -> Dict[str, Any]:
    """
    사용자의 개인화 취향 요약 생성

    Args:
        member_id: 사용자 ID (0이면 비로그인 → 빈 요약 반환)

    Returns:
        Dict containing:
        - liked_perfumes: List[Dict] - 좋아하는 향수 Top N
        - disliked_perfumes: List[Dict] - 싫어하는 향수 Top N
        - liked_brands: Dict[str, float] - 좋아하는 브랜드와 점수
        - disliked_brands: Dict[str, float] - 싫어하는 브랜드와 점수
        - total_count: int - 전체 개인화 데이터 개수
        - summary_text: str - 프롬프트용 한 줄 요약

    Example:
        >>> summary = get_personalization_summary(member_id=123)
        >>> print(summary['summary_text'])
        "딥디크, 조말론 브랜드를 선호하시는 것 같아요. 강한 시트러스 향수는 피하시는 편이네요."
    """
    # 비로그인 사용자
    if not member_id or member_id == 0:
        return _empty_summary()

    # DB에서 개인화 데이터 조회
    try:
        my_perfumes = get_my_perfumes(member_id)
    except Exception as e:
        print(f"⚠️ [Personalization] Error fetching my_perfumes: {e}")
        return _empty_summary()

    if not my_perfumes:
        return _empty_summary()

    # 최근 N개만 사용 (성능)
    my_perfumes = my_perfumes[:QUERY_LIMIT]

    # [★추가] Notes/Accords 조회
    perfume_ids = [p['perfume_id'] for p in my_perfumes]
    notes_accords_map = get_perfume_notes_and_accords(perfume_ids)

    # 점수 계산
    scored_perfumes = []
    brand_scores = defaultdict(float)
    note_scores = defaultdict(float)       # [★추가] 노트별 점수 집계
    accord_scores = defaultdict(float)     # [★추가] 어코드별 점수 집계

    for idx, perfume in enumerate(my_perfumes):
        # [★수정] preference 필드 사용 (archive_db.py에서 추가됨)
        preference = perfume.get("preference", "NEUTRAL")
        register_status = perfume.get("register_status", "RECOMMENDED")

        score = calculate_personalization_score(
            preference=preference,
            register_status=register_status,
            recency_rank=idx,
        )

        scored_perfumes.append({
            **perfume,
            "personalization_score": score,
        })

        # 브랜드별 집계
        brand = perfume.get("brand", "Unknown")
        if brand and brand != "Unknown":
            brand_scores[brand] += score
        
        # [★추가] Notes/Accords 점수 집계
        perfume_id = perfume.get("perfume_id")
        if perfume_id in notes_accords_map:
            # 노트 점수 누적
            for note in notes_accords_map[perfume_id].get("notes", []):
                note_scores[note] += score
            
            # 어코드 점수 누적
            for accord in notes_accords_map[perfume_id].get("accords", []):
                accord_scores[accord] += score

    # 정렬
    scored_perfumes.sort(key=lambda x: x["personalization_score"], reverse=True)

    # Top N 추출
    liked = [p for p in scored_perfumes if p["personalization_score"] > 0][:MAX_LIKED_PERFUMES]
    disliked = [p for p in scored_perfumes if p["personalization_score"] < 0][:MAX_DISLIKED_PERFUMES]
    disliked.sort(key=lambda x: x["personalization_score"])  # 가장 싫어하는 것부터

    # 브랜드 Top N
    liked_brands = {k: v for k, v in sorted(brand_scores.items(), key=lambda x: x[1], reverse=True) if v > 0}
    disliked_brands = {k: v for k, v in sorted(brand_scores.items(), key=lambda x: x[1]) if v < 0}
    
    # [★추가] Notes/Accords Top N 추출 (신뢰도 가드 적용)
    liked_notes = _extract_top_n_with_support(note_scores, positive=True)
    disliked_notes = _extract_top_n_with_support(note_scores, positive=False)
    liked_accords = _extract_top_n_with_support(accord_scores, positive=True)
    disliked_accords = _extract_top_n_with_support(accord_scores, positive=False)

    # 한 줄 요약 생성
    summary_text = _generate_summary_text(
        liked_brands,
        disliked_brands,
        liked_notes=liked_notes,
        liked_accords=liked_accords,
        disliked_accords=disliked_accords,
    )

    return {
        "liked_perfumes": liked,
        "disliked_perfumes": disliked,
        "liked_brands": liked_brands,
        "disliked_brands": disliked_brands,
        "liked_notes": liked_notes,              # [★추가]
        "disliked_notes": disliked_notes,        # [★추가]
        "liked_accords": liked_accords,          # [★추가]
        "disliked_accords": disliked_accords,    # [★추가]
        "total_count": len(my_perfumes),
        "summary_text": summary_text,
    }


def _empty_summary() -> Dict[str, Any]:
    """빈 개인화 요약 (비로그인 또는 데이터 없음)"""
    return {
        "liked_perfumes": [],
        "disliked_perfumes": [],
        "liked_brands": {},
        "disliked_brands": {},
        "liked_notes": [],          # [★추가]
        "disliked_notes": [],       # [★추가]
        "liked_accords": [],        # [★추가]
        "disliked_accords": [],     # [★추가]
        "total_count": 0,
        "summary_text": "",
    }


def _extract_top_n_with_support(
    scores: Dict[str, float],
    positive: bool = True,
    top_n: int = TOP_N_NOTES_ACCORDS,
) -> List[str]:
    """
    신뢰도 가드 적용하여 Top-N 추출
    
    Args:
        scores: 항목별 점수 dict
        positive: True면 양수(선호), False면 음수(기피)
        top_n: 최대 개수
    
    Returns:
        Top-N 항목 리스트
    """
    if positive:
        filtered = {k: v for k, v in scores.items() if v > 0}
        sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    else:
        filtered = {k: v for k, v in scores.items() if v < 0}
        sorted_items = sorted(filtered.items(), key=lambda x: x[1])
    
    return [k for k, _ in sorted_items[:top_n]]


def _generate_summary_text(
    liked_brands: Dict[str, float],
    disliked_brands: Dict[str, float],
    liked_notes: Optional[List[str]] = None,
    liked_accords: Optional[List[str]] = None,
    disliked_accords: Optional[List[str]] = None,
) -> str:
    """
    프롬프트 주입용 한 줄 요약 생성
    
    민감정보 최소화: 브랜드명/노트/어코드만 사용, 향수 전체 이름은 포함하지 않음
    """
    parts = []

    # 좋아하는 브랜드 (최대 3개)
    if liked_brands:
        top_brands = list(liked_brands.keys())[:3]
        brands_str = ", ".join(top_brands)
        parts.append(f"{brands_str} 브랜드를 선호하시는 것 같아요")
    
    # [★추가] 좋아하는 어코드 (최대 2개)
    if liked_accords:
        accords_str = ", ".join(liked_accords[:2])
        parts.append(f"{accords_str} 계열을 선호하시는 편이네요")
    
    # [★추가] 좋아하는 노트 (최대 2개)
    if liked_notes:
        notes_str = ", ".join(liked_notes[:2])
        parts.append(f"{notes_str} 향을 좋아하시는 것 같아요")

    # 싫어하는 브랜드 (최대 2개)
    if disliked_brands:
        bottom_brands = list(disliked_brands.keys())[:2]
        brands_str = ", ".join(bottom_brands)
        parts.append(f"{brands_str} 브랜드는 피하시는 편이네요")
    
    # [★추가] 싫어하는 어코드/노트 (최대 2개씩)
    if disliked_accords:
        accords_str = ", ".join(disliked_accords[:2])
        parts.append(f"{accords_str} 계열은 피하시는 편이네요")

    if not parts:
        return ""

    return ". ".join(parts) + "."


# =================================================================
# 사용 예시
# =================================================================

"""
Example usage:

    from agent.personalization import get_personalization_summary

    # 로그인 사용자
    summary = get_personalization_summary(member_id=123)
    print(summary['summary_text'])
    # → "딥디크, 조말론 브랜드를 선호하시는 것 같아요"

    # 비로그인 사용자
    summary = get_personalization_summary(member_id=0)
    print(summary['total_count'])  # → 0

    # 프롬프트 주입
    if summary['summary_text']:
        prompt += f"\\n\\n사용자 취향: {summary['summary_text']}"
"""
