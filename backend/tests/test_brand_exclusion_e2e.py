"""
브랜드 제외 기능 E2E 통합 테스트

사용자가 "바이레도 말고"라고 했을 때 실제로 바이레도가 제외되는지 검증
"""
import sys
from pathlib import Path

# backend 경로 추가
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from agent.brand_exclusion_parser import parse_brand_exclusions
from agent.database import search_perfumes


def test_brand_exclusion_end_to_end():
    """
    E2E 테스트: "바이레도, 샤넬 말고" → 실제로 제외됨
    """
    # 1. 파싱
    user_query = "바이레도, 샤넬 말고 남자 향수 추천해줘"
    exclude_brands, has_exclusion = parse_brand_exclusions(user_query)
    
    assert has_exclusion == True
    assert "Byredo" in exclude_brands
    assert "Chanel" in exclude_brands
    
    # 2. DB 검색
    results = search_perfumes(
        hard_filters={"gender": "Men"},
        strategy_filters={},
        exclude_ids=[],
        exclude_brands=exclude_brands,
        limit=10,
    )
    
    # 3. 결과 검증
    assert len(results) > 0, "Should have results"
    
    result_brands = [p.get("brand") for p in results if p.get("brand")]
    assert "Byredo" not in result_brands, "Byredo should be excluded"
    assert "Chanel" not in result_brands, "Chanel should be excluded"
    
    print(f"✅ E2E 테스트 성공: {len(results)}개 결과, Byredo/Chanel 제외됨")


def test_single_brand_exclusion():
    """단일 브랜드 제외 테스트"""
    user_query = "딥디크 제외하고 추천"
    exclude_brands, has_exclusion = parse_brand_exclusions(user_query)
    
    assert has_exclusion == True
    assert exclude_brands == ["Diptyque"]
    
    results = search_perfumes(
        hard_filters={"gender": "Women"},
        strategy_filters={},
        exclude_ids=[],
        exclude_brands=exclude_brands,
        limit=5,
    )
    
    result_brands = [p.get("brand") for p in results if p.get("brand")]
    assert "Diptyque" not in result_brands


def test_no_exclusion_normal_search():
    """제외 없는 일반 검색"""
    user_query = "향수 추천해줘"
    exclude_brands, has_exclusion = parse_brand_exclusions(user_query)
    
    assert has_exclusion == False
    assert exclude_brands == []
    
    # 일반 검색 (exclude_brands 없음)
    results = search_perfumes(
        hard_filters={"gender": "Unisex"},
        strategy_filters={},
        exclude_ids=[],
        exclude_brands=[],
        limit=5,
    )
    
    assert len(results) > 0


def test_max_5_brands_limit():
    """최대 5개 브랜드 제한 테스트"""
    user_query = "바이레도, 샤넬, 딥디크, 조말론, 톰포드, 구찌 말고"
    exclude_brands, has_exclusion = parse_brand_exclusions(user_query)
    
    assert has_exclusion == True
    assert len(exclude_brands) == 5, "Should be limited to 5 brands"


def test_slash_delimiter():
    """슬래시 구분자 테스트"""
    user_query = "바이레도/샤넬 빼고"
    exclude_brands, has_exclusion = parse_brand_exclusions(user_query)
    
    assert has_exclusion == True
    assert len(exclude_brands) == 2
    assert "Byredo" in exclude_brands
    assert "Chanel" in exclude_brands
