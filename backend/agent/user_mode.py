"""
User mode normalization and logging utilities.

This module provides centralized handling for user_mode values to ensure
consistent behavior across the agent system.
"""

from typing import Any, Literal
import logging

logger = logging.getLogger(__name__)

UserMode = Literal["BEGINNER", "EXPERT"]


def normalize_user_mode(raw: Any) -> UserMode:
    """
    Normalize user_mode input to BEGINNER or EXPERT.
    
    Handles various input formats and provides safe fallback to BEGINNER
    for any invalid or missing values.
    
    Args:
        raw: Any input value (str, None, int, etc.)
        
    Returns:
        "BEGINNER" or "EXPERT" (always uppercase)
        
    Examples:
        >>> normalize_user_mode("expert")
        'EXPERT'
        >>> normalize_user_mode(" Beginner ")
        'BEGINNER'
        >>> normalize_user_mode(None)
        'BEGINNER'
        >>> normalize_user_mode("invalid")
        'BEGINNER'
    """
    # Handle None or empty values
    if raw is None or raw == "":
        logger.debug("user_mode is None or empty, defaulting to BEGINNER")
        return "BEGINNER"
    
    # Convert to string and normalize
    try:
        normalized = str(raw).strip().upper()
    except Exception as e:
        logger.warning(f"Failed to normalize user_mode '{raw}': {e}, defaulting to BEGINNER")
        return "BEGINNER"
    
    # Validate against allowed values
    if normalized == "EXPERT":
        return "EXPERT"
    elif normalized == "BEGINNER":
        return "BEGINNER"
    else:
        logger.warning(f"Invalid user_mode value '{raw}', defaulting to BEGINNER")
        return "BEGINNER"


def format_mode_log(node: str, user_mode: str, prompt_id: str) -> str:
    """
    Format a standardized log message for mode selection.
    
    This ensures consistent logging format across all graph nodes for easier
    debugging and verification.
    
    Args:
        node: Name of the graph node (e.g., "writer", "perfume_describer")
        user_mode: The selected user mode ("BEGINNER" or "EXPERT")
        prompt_id: Identifier of the prompt being used
        
    Returns:
        Formatted log string
        
    Example:
        >>> format_mode_log("writer", "EXPERT", "WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE")
        '[Mode] node=writer user_mode=EXPERT prompt=WRITER_RECOMMENDATION_PROMPT_EXPERT_SINGLE'
    """
    return f"[Mode] node={node} user_mode={user_mode} prompt={prompt_id}"
