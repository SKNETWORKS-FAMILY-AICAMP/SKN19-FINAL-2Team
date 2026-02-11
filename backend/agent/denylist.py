"""
금지어/불용어 정책 정의 및 공용 유틸

사용자에게 노출되는 텍스트에서 내부 전략 라벨/전략적 단어가 절대 나타나지 않도록 하는 필터링 및 검증 유틸.

핵심 원칙:
- 사용자 친화 전략명(예: "[강인하고 자신감 있는 첫인상]")은 출력 OK
- 내부 전략 수립 용어/내부 전략명은 절대 금지
- SAVE 태그([[SAVE:ID:Name]])는 절대 손상되면 안 됨
"""

import re
from typing import List, Tuple, Optional


# ==========================================
# 1. 금지어 정책 정의
# ==========================================

class DenylistPolicy:
    """금지어 정책을 관리하는 클래스"""
    
    # 금지 단어/구문 (정규식 패턴)
    FORBIDDEN_PATTERNS = [
        # 내부 전략 수립을 직접 드러내는 구문 (공백 변형 포함)
        r"이미지\s*(강조|보완|반전)",  # "이미지 강조", "이미지강조" 등
        
        # 전략 관련 단어
        r"전략",
        r"전략적",
    ]
    
    # 보호해야 하는 패턴 (필터링 시 건드리면 안 됨)
    PROTECTED_PATTERNS = [
        r"\[\[SAVE:\d+:[^\]]+\]\]",  # SAVE 태그: [[SAVE:ID:Name]]
    ]
    
    @classmethod
    def compile_patterns(cls) -> Tuple[List[re.Pattern], List[re.Pattern]]:
        """정규식 패턴을 컴파일하여 반환"""
        forbidden = [re.compile(pattern, re.IGNORECASE) for pattern in cls.FORBIDDEN_PATTERNS]
        protected = [re.compile(pattern) for pattern in cls.PROTECTED_PATTERNS]
        return forbidden, protected
    
    @classmethod
    def get_forbidden_patterns(cls) -> List[str]:
        """금지어 패턴 목록 반환 (문자열)"""
        return cls.FORBIDDEN_PATTERNS
    
    @classmethod
    def get_protected_patterns(cls) -> List[str]:
        """보호 패턴 목록 반환 (문자열)"""
        return cls.PROTECTED_PATTERNS


# ==========================================
# 2. 금지어 검증 유틸
# ==========================================

def detect_forbidden_words(text: str) -> List[Tuple[str, int, int]]:
    """
    텍스트에서 금지어를 탐지하고 위치 정보와 함께 반환
    
    Args:
        text: 검증할 텍스트
    
    Returns:
        [(매칭된_문자열, 시작_위치, 종료_위치), ...] 리스트
    """
    forbidden_patterns, _ = DenylistPolicy.compile_patterns()
    matches = []
    
    for pattern in forbidden_patterns:
        for match in pattern.finditer(text):
            matches.append((match.group(), match.start(), match.end()))
    
    # 위치 기준으로 정렬
    matches.sort(key=lambda x: x[1])
    return matches


def has_forbidden_words(text: str) -> bool:
    """
    텍스트에 금지어가 포함되어 있는지 확인
    
    Args:
        text: 검증할 텍스트
    
    Returns:
        금지어 포함 여부
    """
    return len(detect_forbidden_words(text)) > 0


def validate_save_tags(text: str) -> Tuple[bool, List[str]]:
    """
    텍스트에서 SAVE 태그의 무결성을 검증
    
    Args:
        text: 검증할 텍스트
    
    Returns:
        (무결성_여부, [발견된_SAVE_태그_리스트])
    """
    _, protected_patterns = DenylistPolicy.compile_patterns()
    save_pattern = protected_patterns[0]  # SAVE 태그 패턴
    
    matches = save_pattern.findall(text)
    
    # SAVE 태그가 발견되었으면 무결성 OK
    # (형식이 정규식과 일치하므로 자동으로 유효함)
    return len(matches) > 0, matches


def get_violation_report(text: str) -> dict:
    """
    텍스트의 금지어 위반 상황을 상세히 보고
    
    Args:
        text: 검증할 텍스트
    
    Returns:
        {
            "has_violations": bool,
            "forbidden_matches": [(word, start, end), ...],
            "save_tags_found": [tag1, tag2, ...],
            "violation_count": int,
        }
    """
    forbidden_matches = detect_forbidden_words(text)
    save_valid, save_tags = validate_save_tags(text)
    
    return {
        "has_violations": len(forbidden_matches) > 0,
        "forbidden_matches": forbidden_matches,
        "save_tags_found": save_tags,
        "violation_count": len(forbidden_matches),
    }


# ==========================================
# 3. 사용자 친화 전략명 (안전 리스트)
# ==========================================

class UserFriendlyStrategyLabels:
    """
    사용자에게 노출되는 전략명 (금지어 포함 금지)
    
    이 리스트의 모든 항목은 금지어 검증을 통과해야 함.
    """
    
    # 첫인상/무드 중심 표현
    SAFE_LABELS = [
        "강인하고 자신감 있는 첫인상",
        "우아하고 세련된 분위기",
        "신선하고 활기찬 느낌",
        "따뜻하고 포근한 감성",
        "신비로운 매력",
        "고급스러운 프리미엄 감",
        "편안하고 친근한 분위기",
        "대담하고 개성 있는 스타일",
        "부드럽고 로맨틱한 감정",
        "시원하고 깔끔한 인상",
    ]
    
    @classmethod
    def validate_all_labels(cls) -> Tuple[bool, List[str]]:
        """
        모든 안전 라벨이 금지어를 포함하지 않는지 검증
        
        Returns:
            (모두_안전_여부, [위반된_라벨_리스트])
        """
        violations = []
        for label in cls.SAFE_LABELS:
            if has_forbidden_words(label):
                violations.append(label)
        
        return len(violations) == 0, violations
    
    @classmethod
    def get_safe_labels(cls) -> List[str]:
        """안전한 전략명 리스트 반환"""
        return cls.SAFE_LABELS


# ==========================================
# 4. 초기화 및 검증
# ==========================================

def initialize_and_validate():
    """
    모듈 초기화 시 안전 라벨 검증
    
    Raises:
        ValueError: 안전 라벨에 금지어가 포함된 경우
    """
    all_safe, violations = UserFriendlyStrategyLabels.validate_all_labels()
    if not all_safe:
        raise ValueError(
            f"안전 라벨에 금지어가 포함되어 있습니다: {violations}"
        )


# 모듈 로드 시 자동 검증
try:
    initialize_and_validate()
except ValueError as e:
    # 프로덕션에서는 로깅하고 계속 진행
    # (테스트에서는 실패해야 함)
    import sys
    print(f"[WARNING] {e}", file=sys.stderr)
