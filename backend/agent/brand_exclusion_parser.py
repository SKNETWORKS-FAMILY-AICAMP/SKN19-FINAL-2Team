"""
브랜드 제외 파싱 모듈

사용자 입력에서 "말고/제외/빼고" 패턴을 감지하고 브랜드를 추출합니다.
"""

import re
from typing import List, Optional, Tuple
from .database import match_brand_name


# 제외 키워드 패턴
EXCLUSION_KEYWORDS = ["말고", "빼고", "제외", "제외하고", "빼놓고"]

# 브랜드 구분자
BRAND_DELIMITERS = [",", "/", "、"]

# 최대 제외 브랜드 개수
MAX_EXCLUDE_BRANDS = 5


def parse_brand_exclusions(user_query: str) -> Tuple[List[str], bool]:
    """
    사용자 쿼리에서 브랜드 제외 패턴을 파싱합니다.
    
    Args:
        user_query: 사용자 입력 (예: "바이레도, 샤넬 말고 추천해줘")
    
    Returns:
        (exclude_brands, has_exclusion)
        - exclude_brands: 정규화된 브랜드명 리스트 (최대 5개)
        - has_exclusion: 제외 패턴이 감지되었는지 여부
    
    Examples:
        >>> parse_brand_exclusions("바이레도 말고")
        (['Byredo'], True)
        
        >>> parse_brand_exclusions("샤넬, 디올 제외하고")
        (['Chanel', 'Dior'], True)
        
        >>> parse_brand_exclusions("향수 추천해줘")
        ([], False)
    """
    query_lower = user_query.lower().strip()
    
    # 제외 키워드 찾기
    exclusion_keyword = None
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in query_lower:
            exclusion_keyword = keyword
            break
    
    if not exclusion_keyword:
        return [], False
    
    # 제외 키워드 앞의 텍스트 추출
    # 예: "바이레도, 샤넬 말고 추천해줘" -> "바이레도, 샤넬"
    parts = user_query.split(exclusion_keyword)
    if len(parts) < 2:
        return [], False
    
    brands_text = parts[0].strip()
    if not brands_text:
        return [], False
    
    # 브랜드 토큰 추출
    brand_tokens = _extract_brand_tokens(brands_text)
    
    if not brand_tokens:
        return [], False
    
    # 브랜드명 정규화
    exclude_brands = []
    for token in brand_tokens:
        matched = match_brand_name(token)
        # 정규화 성공한 것만 포함
        if matched and matched != token:
            exclude_brands.append(matched)
        elif matched:  # 이미 정확한 브랜드명인 경우
            exclude_brands.append(matched)
    
    # 최대 5개 제한
    if len(exclude_brands) > MAX_EXCLUDE_BRANDS:
        exclude_brands = exclude_brands[:MAX_EXCLUDE_BRANDS]
    
    return exclude_brands, len(exclude_brands) > 0


def _extract_brand_tokens(brands_text: str) -> List[str]:
    """
    브랜드 텍스트에서 개별 브랜드 토큰을 추출합니다.
    
    Args:
        brands_text: 브랜드 텍스트 (예: "바이레도, 샤넬")
    
    Returns:
        브랜드 토큰 리스트
    """
    # 구분자로 분리
    tokens = [brands_text]
    for delimiter in BRAND_DELIMITERS:
        new_tokens = []
        for token in tokens:
            new_tokens.extend(token.split(delimiter))
        tokens = new_tokens
    
    # 공백 제거 및 빈 토큰 제거
    tokens = [t.strip() for t in tokens if t.strip()]
    
    # 불용어 제거 (조사, 접속사 등)
    stopwords = ["이랑", "하고", "그리고", "및", "과", "와"]
    tokens = [t for t in tokens if t not in stopwords]
    
    return tokens


def should_clear_brand_fields(exclude_brands: List[str]) -> bool:
    """
    제외 브랜드가 있을 때 brand/reference_brand를 클리어해야 하는지 판단
    
    Args:
        exclude_brands: 파싱된 제외 브랜드 리스트
    
    Returns:
        True if should clear brand fields
    """
    return len(exclude_brands) > 0
