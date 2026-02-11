"""
Test for RESEARCHER_SYSTEM_PROMPT meta data injection.

Verifies that DB-valid filter values (seasons/occasions/accords/genders)
are actually injected into the prompt instead of appearing as literal placeholders.
"""

import sys
from pathlib import Path

import pytest

# Make `backend/` importable as top-level so we can `import agent.*`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.prompts import RESEARCHER_SYSTEM_PROMPT, SEASONS_STR, OCCASIONS_STR, ACCORDS_STR, GENDERS_STR


class TestPromptMetaInjection:
    """Test that meta values are properly injected into RESEARCHER_SYSTEM_PROMPT."""

    def test_no_literal_placeholder_seasons(self):
        """Assert that literal {SEASONS_STR} placeholder does not appear in prompt."""
        assert "{SEASONS_STR}" not in RESEARCHER_SYSTEM_PROMPT, \
            "Literal placeholder {SEASONS_STR} found in prompt - f-string substitution failed"

    def test_no_literal_placeholder_occasions(self):
        """Assert that literal {OCCASIONS_STR} placeholder does not appear in prompt."""
        assert "{OCCASIONS_STR}" not in RESEARCHER_SYSTEM_PROMPT, \
            "Literal placeholder {OCCASIONS_STR} found in prompt - f-string substitution failed"

    def test_no_literal_placeholder_accords(self):
        """Assert that literal {ACCORDS_STR} placeholder does not appear in prompt."""
        assert "{ACCORDS_STR}" not in RESEARCHER_SYSTEM_PROMPT, \
            "Literal placeholder {ACCORDS_STR} found in prompt - f-string substitution failed"

    def test_no_literal_placeholder_genders(self):
        """Assert that literal {GENDERS_STR} placeholder does not appear in prompt."""
        assert "{GENDERS_STR}" not in RESEARCHER_SYSTEM_PROMPT, \
            "Literal placeholder {GENDERS_STR} found in prompt - f-string substitution failed"

    def test_seasons_structure_intact(self):
        """Assert that 'Seasons:' label is present in prompt."""
        assert "Seasons:" in RESEARCHER_SYSTEM_PROMPT, \
            "Seasons label missing from prompt"

    def test_occasions_structure_intact(self):
        """Assert that 'Occasions:' label is present in prompt."""
        assert "Occasions:" in RESEARCHER_SYSTEM_PROMPT, \
            "Occasions label missing from prompt"

    def test_accords_label_correct(self):
        """Assert that label is 'Accords' (not 'Accords/Notes')."""
        assert "Accords:" in RESEARCHER_SYSTEM_PROMPT, \
            "Accords label missing from prompt"
        assert "Accords/Notes:" not in RESEARCHER_SYSTEM_PROMPT, \
            "Old 'Accords/Notes' label found - should be 'Accords' only"

    def test_genders_structure_intact(self):
        """Assert that 'Genders:' label is present in prompt."""
        assert "Genders:" in RESEARCHER_SYSTEM_PROMPT, \
            "Genders label missing from prompt"

    def test_actual_seasons_values_present(self):
        """Assert that actual season values appear in prompt (e.g., Spring, Summer)."""
        # Check that at least one common season is present
        seasons_found = any(season in RESEARCHER_SYSTEM_PROMPT 
                           for season in ["Spring", "Summer", "Fall", "Winter"])
        assert seasons_found, \
            f"No actual season values found in prompt. SEASONS_STR={SEASONS_STR}"

    def test_actual_genders_values_present(self):
        """Assert that actual gender values appear in prompt (e.g., Women, Men, Unisex)."""
        # Check that at least one gender is present
        genders_found = any(gender in RESEARCHER_SYSTEM_PROMPT 
                           for gender in ["Women", "Men", "Unisex"])
        assert genders_found, \
            f"No actual gender values found in prompt. GENDERS_STR={GENDERS_STR}"

    def test_meta_values_not_empty(self):
        """Assert that meta values are populated (not empty strings)."""
        assert SEASONS_STR, "SEASONS_STR is empty"
        assert OCCASIONS_STR, "OCCASIONS_STR is empty"
        assert ACCORDS_STR, "ACCORDS_STR is empty"
        assert GENDERS_STR, "GENDERS_STR is empty"

    def test_meta_values_are_comma_separated(self):
        """Assert that meta values follow comma-separated format."""
        # Each should contain at least one comma (multiple values)
        assert "," in SEASONS_STR, "SEASONS_STR should be comma-separated"
        assert "," in OCCASIONS_STR, "OCCASIONS_STR should be comma-separated"
        assert "," in ACCORDS_STR, "ACCORDS_STR should be comma-separated"
        # Genders might be comma-separated or single value, so we just check it's not empty
        assert GENDERS_STR, "GENDERS_STR should not be empty"
