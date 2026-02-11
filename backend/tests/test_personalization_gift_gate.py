"""
Tests for personalization gate in parallel_reco_node (Wave 2).
Tests that GIFT use case disables member personalization.
"""
import pytest
from unittest.mock import patch, MagicMock
from agent.use_case_utils import infer_use_case


class TestPersonalizationGate:
    """Test personalization gating based on use_case."""
    
    def test_self_use_case_enables_personalization(self):
        """SELF use case with member_id > 0 should enable personalization."""
        user_prefs = {'target': '20대 여성', 'use_case': 'SELF'}
        use_case = infer_use_case(user_prefs)
        assert use_case == 'SELF'
        
        # Personalization should be called for SELF
        # (This will be tested in integration test)
    
    def test_gift_use_case_disables_personalization(self):
        """GIFT use case should disable personalization."""
        user_prefs = {'target': '남친 선물', 'use_case': 'GIFT'}
        use_case = infer_use_case(user_prefs)
        assert use_case == 'GIFT'
        
        # Personalization should NOT be called for GIFT
        # (This will be tested in integration test)
    
    def test_gift_heuristic_disables_personalization(self):
        """Gift detection via heuristic should also disable personalization."""
        user_prefs = {'target': '여자친구 생일 선물'}
        use_case = infer_use_case(user_prefs)
        assert use_case == 'GIFT'
    
    def test_self_default_enables_personalization(self):
        """Default case (no gift keywords) should enable personalization."""
        user_prefs = {'target': '30대 남성'}
        use_case = infer_use_case(user_prefs)
        assert use_case == 'SELF'


# Note: Full integration test would require mocking the entire graph state
# and verifying that get_personalization_summary is called conditionally.
# For now, we verify the use_case inference logic is correct.
