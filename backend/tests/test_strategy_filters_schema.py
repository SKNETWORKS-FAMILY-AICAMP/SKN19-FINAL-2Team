"""
Test suite for StrategyFilters schema validation.

Ensures that:
1. StrategyFilters does NOT have 'style' field (removed to prevent LLM generation)
2. UserPreferences still HAS 'style' field (for reasoning/description purposes)
3. StrategyFilters can be instantiated without style
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.schemas import StrategyFilters, UserPreferences


class TestStrategyFiltersSchema:
    """Test StrategyFilters schema structure and validation."""

    def test_strategy_filters_no_style_field(self):
        """Verify that 'style' field is NOT in StrategyFilters schema."""
        schema = StrategyFilters.model_json_schema()
        properties = schema.get("properties", {})
        
        assert "style" not in properties, (
            "StrategyFilters should NOT have 'style' field. "
            "This prevents LLM from generating style in strategy_filters."
        )

    def test_strategy_filters_has_other_fields(self):
        """Verify that StrategyFilters still has accord, occasion, note fields."""
        schema = StrategyFilters.model_json_schema()
        properties = schema.get("properties", {})
        
        expected_fields = {"accord", "occasion", "note"}
        actual_fields = set(properties.keys())
        
        assert expected_fields == actual_fields, (
            f"StrategyFilters should have exactly {expected_fields}, "
            f"but has {actual_fields}"
        )

    def test_strategy_filters_instantiation_without_style(self):
        """Verify that StrategyFilters can be instantiated without style."""
        # Should not raise any error
        filters = StrategyFilters(
            accord=["Woody", "Floral"],
            occasion=["Evening", "Casual"],
            note=["Rose", "Vetiver"]
        )
        
        assert filters.accord == ["Woody", "Floral"]
        assert filters.occasion == ["Evening", "Casual"]
        assert filters.note == ["Rose", "Vetiver"]
        assert not hasattr(filters, "style") or filters.style is None

    def test_strategy_filters_with_none_values(self):
        """Verify that StrategyFilters accepts None for all fields."""
        filters = StrategyFilters()
        
        assert filters.accord is None
        assert filters.occasion is None
        assert filters.note is None

    def test_user_preferences_still_has_style(self):
        """Verify that UserPreferences STILL has 'style' field (for reasoning)."""
        schema = UserPreferences.model_json_schema()
        properties = schema.get("properties", {})
        
        assert "style" in properties, (
            "UserPreferences should still have 'style' field. "
            "It's used for reasoning and description purposes."
        )

    def test_user_preferences_style_is_optional(self):
        """Verify that UserPreferences.style is optional."""
        # Should not raise error without style
        prefs = UserPreferences(
            target="20대 여성",
            gender="Women"
        )
        
        assert prefs.style is None
        
        # Should accept style when provided
        prefs_with_style = UserPreferences(
            target="20대 여성",
            gender="Women",
            style="Elegant"
        )
        
        assert prefs_with_style.style == "Elegant"

    def test_strategy_filters_rejects_style_field(self):
        """Verify that StrategyFilters rejects 'style' if provided (extra='forbid')."""
        # This test documents the current behavior
        # If extra='forbid' is set in StrategyFilters, this should raise ValidationError
        
        # For now, Pydantic by default ignores extra fields
        # This test can be enhanced if we add extra='forbid' to StrategyFilters
        filters = StrategyFilters(
            accord=["Woody"],
            style=["Elegant"]  # Extra field
        )
        
        # Currently, Pydantic ignores the extra 'style' field
        assert not hasattr(filters, "style") or filters.style is None


class TestSchemaIntegration:
    """Integration tests for schema consistency."""

    def test_strategy_filters_vs_user_preferences_style_difference(self):
        """Verify the intentional difference between StrategyFilters and UserPreferences."""
        strategy_schema = StrategyFilters.model_json_schema()
        user_schema = UserPreferences.model_json_schema()
        
        strategy_props = set(strategy_schema.get("properties", {}).keys())
        user_props = set(user_schema.get("properties", {}).keys())
        
        # StrategyFilters should NOT have style
        assert "style" not in strategy_props
        
        # UserPreferences should have style
        assert "style" in user_props
        
        # This is the key difference: style is for reasoning, not for DB filtering
