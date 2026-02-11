import sys
from pathlib import Path

import pytest
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent.graph import sanitize_filters


@pytest.fixture
def mock_meta_data():
    return {
        "genders": "Women, Men, Unisex",
        "seasons": "Spring, Summer, Fall, Winter",
        "occasions": "Daily, Office, Party, Date",
        "accords": "Floral, Woody, Fresh, Citrus"
    }


def test_unknown_key_in_strategy_filters_dropped_and_logged(mock_meta_data, caplog):
    with patch('agent.graph.fetch_meta_data', return_value=mock_meta_data):
        h_filters = {"gender": ["Women"]}
        s_filters = {"accord": ["Floral"], "unknown_key": "some_value"}
        
        sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
        
        assert "unknown_key" not in sanitized_strategy
        assert dropped_items["strategy_filters"]["unknown_key"] == "some_value"
        assert "Dropped filters" in caplog.text


def test_invalid_value_in_strategy_filters_accord_dropped_and_logged(mock_meta_data, caplog):
    with patch('agent.graph.fetch_meta_data', return_value=mock_meta_data):
        h_filters = {}
        s_filters = {"accord": ["Floral", "InvalidAccord", "Woody"]}
        
        sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
        
        assert sanitized_strategy["accord"] == ["Floral", "Woody"]
        assert dropped_items["strategy_filters"]["accord_invalid_values"] == ["InvalidAccord"]
        assert "Dropped filters" in caplog.text


def test_invalid_value_in_hard_filters_gender_dropped_and_logged(mock_meta_data, caplog):
    with patch('agent.graph.fetch_meta_data', return_value=mock_meta_data):
        h_filters = {"gender": ["Women", "InvalidGender"]}
        s_filters = {"accord": ["Floral"]}
        
        sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
        
        assert sanitized_hard["gender"] == ["Women"]
        assert dropped_items["hard_filters"]["gender"] == ["InvalidGender"]
        assert "Dropped filters" in caplog.text


def test_tool_receives_clean_input_no_dropped(mock_meta_data, caplog):
    with patch('agent.graph.fetch_meta_data', return_value=mock_meta_data):
        h_filters = {"gender": ["Women"]}
        s_filters = {"accord": ["Floral"], "season": ["Spring"], "occasion": ["Daily"]}
        
        sanitized_hard, sanitized_strategy, dropped_items = sanitize_filters(h_filters, s_filters)
        
        assert sanitized_hard == {"gender": ["Women"]}
        assert sanitized_strategy == {"accord": ["Floral"], "season": ["Spring"], "occasion": ["Daily"]}
        assert dropped_items == {"hard_filters": {}, "strategy_filters": {}}
        assert "Dropped filters" not in caplog.text
