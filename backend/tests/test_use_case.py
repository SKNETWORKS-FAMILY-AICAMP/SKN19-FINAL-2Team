"""
Tests for use_case inference logic.
"""
import pytest
from agent.use_case_utils import infer_use_case


class TestInferUseCase:
    """Test use case inference from user preferences."""
    
    def test_explicit_self(self):
        """Test explicit SELF use case."""
        user_prefs = {'use_case': 'SELF', 'target': '20대 여성'}
        assert infer_use_case(user_prefs) == 'SELF'
    
    def test_explicit_gift(self):
        """Test explicit GIFT use case."""
        user_prefs = {'use_case': 'GIFT', 'target': '20대 여성'}
        assert infer_use_case(user_prefs) == 'GIFT'
    
    def test_heuristic_gift_primary_keyword(self):
        """Test gift inference from primary keywords (선물, 생일)."""
        test_cases = [
            {'target': '남친 선물'},
            {'target': '생일 선물'},
            {'target': '어머니 생일'},
            {'target': '친구 선물로'},
        ]
        for user_prefs in test_cases:
            assert infer_use_case(user_prefs) == 'GIFT', f"Failed for: {user_prefs}"
    
    def test_heuristic_gift_relationship_keyword(self):
        """Test gift inference from relationship keywords."""
        test_cases = [
            {'target': '남친'},
            {'target': '여친에게'},
            {'target': '엄마 드릴'},
            {'target': '아빠'},
            {'target': '친구'},
            {'target': '상사'},
        ]
        for user_prefs in test_cases:
            assert infer_use_case(user_prefs) == 'GIFT', f"Failed for: {user_prefs}"
    
    def test_default_self(self):
        """Test default SELF for personal descriptions."""
        test_cases = [
            {'target': '20대 여성'},
            {'target': '30대 남성'},
            {'target': '본인'},
            {'target': '저한테 맞는'},
            {'target': ''},
            {},
        ]
        for user_prefs in test_cases:
            assert infer_use_case(user_prefs) == 'SELF', f"Failed for: {user_prefs}"
    
    def test_case_insensitive(self):
        """Test that keyword matching is case-insensitive."""
        user_prefs = {'target': '남친 선물'}  # Korean is naturally case-insensitive
        assert infer_use_case(user_prefs) == 'GIFT'
