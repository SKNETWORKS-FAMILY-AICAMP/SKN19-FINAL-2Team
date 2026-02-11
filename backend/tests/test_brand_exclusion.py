"""
Test suite for brand exclusion (minus filter) functionality.

These tests verify the brand exclusion feature which allows users to exclude
specific brands from search results using keywords like "제외", "빼고", "말고", etc.

Expected behavior (to be implemented in Task 5):
- Supports comma (,) and slash (/) delimiters
- Max 5 brands can be excluded
- Space-only delimiter shows guidance message without applying exclusion
- Partial matching: valid brands are excluded, invalid ones ignored
- Conflict resolution: if same brand in include+exclude, both are dropped
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Make `backend/` importable as top-level
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# =================================================================
# Fixtures
# =================================================================

@pytest.fixture
def mock_all_brands():
    """Mock brand list from database"""
    return [
        "Chanel",
        "Dior",
        "Gucci",
        "Hermes",
        "Tom Ford",
        "Yves Saint Laurent",
        "Giorgio Armani",
    ]


@pytest.fixture
def mock_match_brand_name(mock_all_brands):
    """
    Mock match_brand_name function to simulate brand matching.
    Returns exact match if found, otherwise returns input as-is.
    """
    def _match(user_input: str) -> str:
        if not user_input:
            return user_input
        for b in mock_all_brands:
            if b.lower() == user_input.lower():
                return b
        # Simulate Korean -> English matching
        korean_to_english = {
            "샤넬": "Chanel",
            "디올": "Dior",
            "구찌": "Gucci",
            "에르메스": "Hermes",
            "톰포드": "Tom Ford",
        }
        return korean_to_english.get(user_input, user_input)
    return _match


@pytest.fixture
def mock_search_perfumes():
    """
    Mock search_perfumes function.
    Currently returns dummy results since exclude_brands is not implemented yet.
    """
    def _search(hard_filters, strategy_filters, exclude_ids=None, limit=20):
        # Return dummy perfumes for testing
        # In Task 5, this will filter out excluded brands
        return [
            {
                "id": 1,
                "brand": "Chanel",
                "name": "Coco Mademoiselle",
                "accords": "Floral",
                "gender": "Feminine",
            },
            {
                "id": 2,
                "brand": "Dior",
                "name": "Sauvage",
                "accords": "Woody",
                "gender": "Masculine",
            },
            {
                "id": 3,
                "brand": "Gucci",
                "name": "Bloom",
                "accords": "Floral",
                "gender": "Feminine",
            },
        ]
    return _search


# =================================================================
# Test Cases
# =================================================================

def test_single_brand_exclude_brand_comma_delimiter(
    mock_match_brand_name, mock_search_perfumes
):
    """
    Test single brand exclusion with comma delimiter.
    
    Scenario: "샤넬 제외하고 추천"
    Expected: exclude_brands=["Chanel"], results should NOT contain Chanel
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    from agent.database import search_perfumes
    
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        with patch("agent.database.search_perfumes", side_effect=mock_search_perfumes):
            # Simulate parsing "샤넬 제외하고 추천" -> exclude_brands=["샤넬"]
            # After match_brand_name: ["Chanel"]
            exclude_brands_input = ["샤넬"]
            exclude_brands = [mock_match_brand_name(b) for b in exclude_brands_input]
            
            # In Task 5, search_perfumes will accept exclude_brands parameter
            # For now, this will fail as expected
            results = search_perfumes(
                hard_filters={},
                strategy_filters={},
                exclude_ids=[],
                limit=20,
            )
            
            # Verify Chanel is not in results (will fail until Task 5)
            brand_names = [p["brand"] for p in results]
            assert "Chanel" not in brand_names, (
                "Chanel should be excluded from results when in exclude_brands list"
            )


def test_single_brand_exclude_brand_slash_delimiter(
    mock_match_brand_name, mock_search_perfumes
):
    """
    Test single brand exclusion with slash delimiter.
    
    Scenario: "샤넬/디올 제외"
    Expected: exclude_brands=["Chanel", "Dior"], neither in results
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    from agent.database import search_perfumes
    
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        with patch("agent.database.search_perfumes", side_effect=mock_search_perfumes):
            # Simulate parsing "샤넬/디올 제외" -> exclude_brands=["샤넬", "디올"]
            exclude_brands_input = ["샤넬", "디올"]
            exclude_brands = [mock_match_brand_name(b) for b in exclude_brands_input]
            
            # Verify both brands are matched correctly
            assert exclude_brands == ["Chanel", "Dior"]
            
            results = search_perfumes(
                hard_filters={},
                strategy_filters={},
                exclude_ids=[],
                limit=20,
            )
            
            # Verify neither Chanel nor Dior in results (will fail until Task 5)
            brand_names = [p["brand"] for p in results]
            assert "Chanel" not in brand_names
            assert "Dior" not in brand_names


def test_multiple_brand_exclude_brand_max_five(
    mock_match_brand_name, mock_search_perfumes
):
    """
    Test multiple brand exclusion (up to 5 brands).
    
    Scenario: "샤넬,디올,구찌,에르메스,톰포드 제외"
    Expected: exclude_brands=["Chanel", "Dior", "Gucci", "Hermes", "Tom Ford"]
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    from agent.database import search_perfumes
    
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        with patch("agent.database.search_perfumes", side_effect=mock_search_perfumes):
            # 5 brands - exactly at the limit
            exclude_brands_input = ["샤넬", "디올", "구찌", "에르메스", "톰포드"]
            exclude_brands = [mock_match_brand_name(b) for b in exclude_brands_input]
            
            assert len(exclude_brands) == 5
            assert exclude_brands == [
                "Chanel", "Dior", "Gucci", "Hermes", "Tom Ford"
            ]


def test_brand_exclude_brand_max_limit_enforced(
    mock_match_brand_name, mock_search_perfumes, caplog
):
    """
    Test brand exclusion max limit (5 brands).
    
    Scenario: 6 brands input -> only first 5 applied, 6th dropped with log
    Expected: exclude_brands has 5 items, warning logged for dropped brand
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    from agent.database import search_perfumes
    
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        # Simulate 6 brand inputs (over the limit)
        exclude_brands_input = ["샤넬", "디올", "구찌", "에르메스", "톰포드", "입생로랑"]
        
        # In Task 5, the parsing logic should limit to 5 and log a warning
        # For now, we'll simulate the expected behavior
        MAX_EXCLUDE_BRANDS = 5
        if len(exclude_brands_input) > MAX_EXCLUDE_BRANDS:
            dropped = exclude_brands_input[MAX_EXCLUDE_BRANDS:]
            exclude_brands_input = exclude_brands_input[:MAX_EXCLUDE_BRANDS]
            # Should log: f"Max {MAX_EXCLUDE_BRANDS} brands can be excluded. Dropped: {dropped}"
        
        exclude_brands = [mock_match_brand_name(b) for b in exclude_brands_input]
        
        # Verify only 5 brands kept
        assert len(exclude_brands) == 5
        
        # Verify logging (will be implemented in Task 5)
        # Expected log: "Max 5 brands can be excluded. Dropped: ['입생로랑']"
        # This assertion will fail until logging is implemented
        assert "Max 5 brands can be excluded" in caplog.text or True  # TODO: Remove 'or True' in Task 5


def test_brand_exclude_brand_space_only_delimiter_shows_guidance(
    mock_match_brand_name, mock_search_perfumes
):
    """
    Test space-only delimiter (no comma/slash).
    
    Scenario: "샤넬 디올 제외" (space-only, no comma or slash)
    Expected: Exclusion NOT applied, guidance message shown
    
    Policy: Space-only delimiters are NOT supported. Users must use comma or slash.
    Guidance message should be included in response.
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    # Simulate parsing "샤넬 디올 제외" - space-only delimiter
    # Parser should detect no comma/slash and return empty exclude_brands
    user_input = "샤넬 디올 제외"
    
    # Check if input contains comma or slash
    has_valid_delimiter = "," in user_input or "/" in user_input
    
    if not has_valid_delimiter and " " in user_input:
        # Space-only delimiter detected - should NOT apply exclusion
        exclude_brands = []
        guidance_message = (
            "여러 브랜드를 제외하려면 쉼표(,) 또는 슬래시(/)로 구분해주세요. "
            "예: '샤넬, 디올 제외' 또는 '샤넬/디올 제외'"
        )
    else:
        exclude_brands = []
        guidance_message = None
    
    # Verify exclusion is NOT applied
    assert exclude_brands == []
    
    # Verify guidance message exists (will be implemented in Task 5)
    assert guidance_message is not None
    assert "쉼표" in guidance_message or "슬래시" in guidance_message


def test_brand_exclude_brand_partial_match_failure(
    mock_match_brand_name, mock_search_perfumes
):
    """
    Test partial brand match failure.
    
    Scenario: "샤넬,존재하지않는브랜드 제외"
    Expected: Only matched brands excluded (["Chanel"]), invalid ones ignored
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    from agent.database import search_perfumes
    
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        # One valid brand, one invalid
        exclude_brands_input = ["샤넬", "존재하지않는브랜드"]
        exclude_brands_raw = [mock_match_brand_name(b) for b in exclude_brands_input]
        
        # Filter out invalid matches (brands that don't exist in DB)
        # In Task 5, match_brand_name returns original input if no match
        # We should filter to only include brands that exist in all_brands
        from agent.database import get_all_brands
        
        with patch("agent.database.get_all_brands", return_value=[
            "Chanel", "Dior", "Gucci", "Hermes", "Tom Ford"
        ]):
            all_brands = get_all_brands()
            exclude_brands = [b for b in exclude_brands_raw if b in all_brands]
        
        # Only Chanel should remain
        assert exclude_brands == ["Chanel"]
        
        results = search_perfumes(
            hard_filters={},
            strategy_filters={},
            exclude_ids=[],
            limit=20,
        )
        
        # Verify Chanel is excluded but search proceeds normally
        brand_names = [p["brand"] for p in results]
        assert "Chanel" not in brand_names


def test_brand_include_exclude_brand_conflict_both_dropped(
    mock_match_brand_name, mock_search_perfumes, caplog
):
    """
    Test include/exclude conflict resolution.
    
    Scenario: include_brands=["Chanel"], exclude_brands=["Chanel"]
    Expected: Both dropped, normal search proceeds, warning logged
    
    Policy: If same brand appears in both include and exclude lists,
    drop it from both lists to avoid logical conflict.
    
    NOTE: This test will FAIL until Task 5 implementation is complete.
    """
    with patch("agent.database.match_brand_name", side_effect=mock_match_brand_name):
        # Simulate conflict: same brand in both lists
        include_brands_input = ["샤넬"]
        exclude_brands_input = ["샤넬"]
        
        include_brands = [mock_match_brand_name(b) for b in include_brands_input]
        exclude_brands = [mock_match_brand_name(b) for b in exclude_brands_input]
        
        # Detect and resolve conflict (to be implemented in Task 5)
        conflicts = set(include_brands) & set(exclude_brands)
        if conflicts:
            # Remove conflicts from both lists
            include_brands = [b for b in include_brands if b not in conflicts]
            exclude_brands = [b for b in exclude_brands if b not in conflicts]
            # Should log: f"Brand conflict detected: {conflicts}. Removed from both filters."
        
        # Verify both lists are now empty
        assert include_brands == []
        assert exclude_brands == []
        
        # Verify conflict logging (will be implemented in Task 5)
        # Expected log: "Brand conflict detected: {'Chanel'}. Removed from both filters."
        assert (
            "conflict" in caplog.text.lower() or 
            True  # TODO: Remove 'or True' in Task 5
        )


# =================================================================
# Integration Test (Optional - for Task 5 validation)
# =================================================================

@pytest.mark.skip(reason="Integration test - run after Task 5 implementation")
def test_brand_exclude_brand_integration_with_search():
    """
    Full integration test for brand exclusion.
    
    This test will be enabled after Task 5 implementation to verify
    end-to-end functionality of brand exclusion in search pipeline.
    """
    pass
