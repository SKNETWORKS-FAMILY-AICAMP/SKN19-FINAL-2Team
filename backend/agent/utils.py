# backend/agent/utils.py
"""
Utility functions for agent operations.
Centralized helper functions used across graph.py, graph_info.py, and tools.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Literal

logger = logging.getLogger(__name__)


# =================================================================
# [A] Text Normalization (Special Character Removal)
# =================================================================

def remove_special_chars(text: str) -> str:
    """
    모든 특수문자를 제거하여 검색 매칭률을 높입니다.
    영문자, 숫자, 한글만 남기고 나머지(공백, 하이픈, 어포스트로피 등) 제거

    Args:
        text: 원본 텍스트 (예: "J'adore L'Or", "자도르 로르")

    Returns:
        정규화된 텍스트 (예: "JadoreLOr", "자도르로르")

    Examples:
        >>> remove_special_chars("J'adore L'Or")
        'JadoreLOr'
        >>> remove_special_chars("자도르 로르")
        '자도르로르'
        >>> remove_special_chars("Chanel N°5")
        'ChanelN5'
    """
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', text)


# =================================================================
# [B] Recommendation Count Parsing (from graph.py)
# =================================================================

def parse_recommended_count(query: str) -> Optional[int]:
    """Parse 'N개' from user query."""
    if not query:
        return None
    # Map words to numbers
    word_map = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5}
    match_word = re.search(r"(한|두|세|네|다섯)\s*개", query)
    match_digit = re.search(r"(\d+)\s*개", query)

    if match_digit:
        return int(match_digit.group(1))
    elif match_word:
        return word_map.get(match_word.group(1))
    return None


def normalize_recommended_count(count: Optional[int]) -> int:
    """Normalize recommendation count to be between 1 and 5."""
    if count is None:
        return 3
    return max(1, min(count, 5))


# =================================================================
# [B] Filter Sanitization (from graph.py)
# =================================================================

def sanitize_filters(h_filters: dict, s_filters: dict) -> tuple:
    """
    Sanitize filters by dropping unknown keys and invalid values.

    Args:
        h_filters: Hard filters (gender, etc.)
        s_filters: Strategy filters (accord, occasion, note, season)

    Returns:
        Tuple of (sanitized_hard_filters, sanitized_strategy_filters, dropped_items)
    """
    from .database import fetch_meta_data

    meta = fetch_meta_data()

    allowed_genders = {g.strip() for g in meta.get("genders", "").split(",") if g.strip()}
    allowed_seasons = {s.strip() for s in meta.get("seasons", "").split(",") if s.strip()}
    allowed_occasions = {o.strip() for o in meta.get("occasions", "").split(",") if o.strip()}
    allowed_accords = {a.strip() for a in meta.get("accords", "").split(",") if a.strip()}

    allowed_strategy_keys = {"accord", "occasion", "note", "season"}

    dropped_items = {
        "hard_filters": {},
        "strategy_filters": {}
    }

    sanitized_hard = {}
    for key, value in h_filters.items():
        if key == "gender":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_genders]
                invalid_values = [v for v in value if v not in allowed_genders]
                if invalid_values:
                    dropped_items["hard_filters"][key] = invalid_values
                if valid_values:
                    sanitized_hard[key] = valid_values
            elif value in allowed_genders:
                sanitized_hard[key] = value
            else:
                dropped_items["hard_filters"][key] = value
        else:
            sanitized_hard[key] = value

    sanitized_strategy = {}
    for key, value in s_filters.items():
        if key not in allowed_strategy_keys:
            dropped_items["strategy_filters"][key] = value
            continue

        if key == "note":
            sanitized_strategy[key] = value
        elif key == "season":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_seasons]
                invalid_values = [v for v in value if v not in allowed_seasons]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_seasons:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value
        elif key == "occasion":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_occasions]
                invalid_values = [v for v in value if v not in allowed_occasions]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_occasions:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value
        elif key == "accord":
            if isinstance(value, list):
                valid_values = [v for v in value if v in allowed_accords]
                invalid_values = [v for v in value if v not in allowed_accords]
                if invalid_values:
                    dropped_items["strategy_filters"][f"{key}_invalid_values"] = invalid_values
                if valid_values:
                    sanitized_strategy[key] = valid_values
            elif value in allowed_accords:
                sanitized_strategy[key] = value
            else:
                dropped_items["strategy_filters"][key] = value

    if dropped_items["hard_filters"] or dropped_items["strategy_filters"]:
        logger.warning(f"Dropped filters: {dropped_items}")

    return sanitized_hard, sanitized_strategy, dropped_items


# =================================================================
# [C] Save Reference Parsing (from graph_info.py)
# =================================================================

def extract_save_refs(messages: List) -> List[Dict[str, Any]]:
    """
    Extract SAVE tags with section numbers from messages.
    Returns list of {number: int, id: int, name: str}.
    """
    from langchain_core.messages import AIMessage

    save_pattern = re.compile(r'\[\[SAVE:(\d+):([^\]]+)\]\]')
    section_pattern = re.compile(r'##\s*(\d+)\.')
    
    all_refs = []
    
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            save_matches = save_pattern.findall(content)
            
            if save_matches:
                section_matches = section_pattern.findall(content)
                
                for i, (perfume_id, name) in enumerate(save_matches):
                    number = int(section_matches[i]) if i < len(section_matches) else i + 1
                    all_refs.append({
                        "number": number,
                        "id": int(perfume_id),
                        "name": name
                    })
    
    return all_refs


def parse_ordinal(user_query: str) -> Optional[int]:
    """
    Parse ordinal numbers from Korean text (supports 1-10).
    Returns 1-based index (1, 2, 3, ...) or None if not found.
    """
    query_lower = user_query.lower()

    numeric_match = re.search(r'(\d+)\s*(번째|번)\b', query_lower)
    if numeric_match:
        return int(numeric_match.group(1))

    korean_ordinals = {
        '첫': 1, '첫번째': 1, '1번째': 1, '1번': 1,
        '두': 2, '두번째': 2, '둘째': 2, '2번째': 2, '2번': 2,
        '세': 3, '세번째': 3, '셋째': 3, '3번째': 3, '3번': 3,
        '네': 4, '네번째': 4, '넷째': 4, '4번째': 4, '4번': 4,
        '다섯': 5, '다섯번째': 5, '다섯째': 5, '5번째': 5, '5번': 5,
        '여섯': 6, '여섯번째': 6, '여섯째': 6, '6번째': 6, '6번': 6,
        '일곱': 7, '일곱번째': 7, '일곱째': 7, '7번째': 7, '7번': 7,
        '여덟': 8, '여덟번째': 8, '여덟째': 8, '8번째': 8, '8번': 8,
        '아홉': 9, '아홉번째': 9, '아홉째': 9, '9번째': 9, '9번': 9,
        '열': 10, '열번째': 10, '열째': 10, '10번째': 10, '10번': 10,
    }

    for pattern, num in korean_ordinals.items():
        if pattern in query_lower:
            return num

    return None


def resolve_target_from_ordinal_or_pronoun(
    user_query: str,
    router_target_name: str,
    save_refs: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Resolve target perfume from ordinal numbers or pronouns.
    Returns {number: int, id: int, name: str} or None if resolution fails.
    """
    pronouns = ['이거', '그거', '이 향수', '저거']
    generic_terms = ['추천해줘', '비슷한거']

    ordinal = parse_ordinal(user_query)
    is_pronoun = any(p in user_query for p in pronouns)
    is_generic = router_target_name in generic_terms or any(g in router_target_name for g in generic_terms)

    if ordinal:
        # number 필드를 기준으로 검색
        for ref in save_refs:
            if ref.get("number") == ordinal:
                return ref
        return None

    if is_pronoun or is_generic:
        if save_refs:
            return save_refs[-1]

    return None


# =================================================================
# [D] Info Status Classification (from graph_info.py)
# =================================================================

def classify_info_status(result: Any) -> Literal['OK', 'NO_RESULTS', 'ERROR']:
    """
    검색 결과(객체 또는 문자열)를 분석하여 상태를 분류합니다.

    분기 기준:
    - ERROR: 기술적 오류 (DB 에러, 예외 등)
    - NO_RESULTS: 데이터 부재 (빈 결과, 검색 실패)
    - OK: 정상 데이터 존재

    Args:
        result: 검색 결과 (list, dict, str)

    Returns:
        'ERROR' | 'NO_RESULTS' | 'OK'
    """
    # [객체 기반 판정] 리스트인 경우
    if isinstance(result, list):
        return 'NO_RESULTS' if len(result) == 0 else 'OK'

    # [객체 기반 판정] 딕셔너리인 경우
    if isinstance(result, dict):
        return 'NO_RESULTS' if not result else 'OK'

    # [하위 호환] 문자열 기반 판정 (기존 코드와의 호환성)
    if isinstance(result, str):
        # 에러 키워드 체크
        if any(keyword in result for keyword in ["DB 에러", "Error"]):
            return 'ERROR'

        # 빈 결과 체크
        if (
            not result
            or result in ["{}", "[]", ""]
            or any(keyword in result for keyword in ["찾을 수 없습니다", "찾지 못했습니다", "검색 실패", "결과가 없습니다"])
        ):
            return 'NO_RESULTS'

        return 'OK'

    # None 또는 기타 타입
    return 'NO_RESULTS' if not result else 'OK'


# =================================================================
# [E] Accord Description Enrichment (from tools_info.py)
# =================================================================

def enrich_accord_description(text: str) -> str:
    """
    텍스트 내에 'Woody', 'Citrus' 같은 어코드 키워드가 있으면
    CSV 사전의 묘사를 괄호 안에 넣어 풍성하게 만듭니다.
    """
    from .expression_loader import ExpressionLoader

    if not text:
        return ""

    enriched_text = text

    # 일반적인 어코드 키워드 목록 (CSV에 있는 것들)
    common_accords = [
        "Animal", "Aquatic", "Chypre", "Citrus", "Creamy", "Earthy",
        "Floral", "Fougère", "Fresh", "Fruity", "Gourmand", "Green",
        "Leathery", "Oriental", "Powdery", "Resinous", "Smoky", "Spicy",
        "Sweet", "Synthetic", "Woody"
    ]

    _expression_loader = ExpressionLoader()

    for accord in common_accords:
        desc = _expression_loader.get_accord_desc(accord)
        if desc:
            pattern = re.compile(f"\\b{accord}\\b", re.IGNORECASE)
            replacement = f"{accord}({desc})"

            # 이미 괄호 설명이 붙어있는지 확인 후 치환
            if f"{accord}(" not in enriched_text:
                enriched_text = pattern.sub(replacement, enriched_text)

    return enriched_text
