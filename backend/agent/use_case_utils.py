# backend/agent/use_case_utils.py
"""
Use case inference utilities for determining SELF vs GIFT recommendations.
"""
from typing import Dict, Literal, Optional


def infer_use_case(user_prefs: Dict) -> Literal['SELF', 'GIFT']:
    """
    Infer use case from user preferences.
    
    Priority:
    1. Explicit use_case field if present
    2. Heuristic based on target string (gift keywords)
    3. Default to SELF
    
    Args:
        user_prefs: Dictionary containing user preferences (may have 'use_case' and 'target' fields)
    
    Returns:
        'SELF' for personal use or 'GIFT' for gift recommendations
    
    Examples:
        >>> infer_use_case({'use_case': 'GIFT'})
        'GIFT'
        >>> infer_use_case({'target': '남친 선물'})
        'GIFT'
        >>> infer_use_case({'target': '20대 여성'})
        'SELF'
    """
    # Check explicit use_case first
    explicit_use_case = user_prefs.get('use_case')
    if explicit_use_case in ['SELF', 'GIFT']:
        return explicit_use_case
    
    # Heuristic: check target for gift keywords
    target = user_prefs.get('target', '').lower()
    
    # Primary gift keywords (high confidence)
    primary_gift_keywords = ['선물', '생일']
    for keyword in primary_gift_keywords:
        if keyword in target:
            return 'GIFT'
    
    # Secondary gift keywords (relationship-based - medium confidence)
    secondary_gift_keywords = [
        '남친', '여친', '남자친구', '여자친구', 
        '친구', '엄마', '어머니', '아빠', '아버지', '부모',
        '누나', '언니', '형', '오빠', '상사'
    ]
    for keyword in secondary_gift_keywords:
        if keyword in target:
            return 'GIFT'
    
    # Default to SELF
    return 'SELF'
