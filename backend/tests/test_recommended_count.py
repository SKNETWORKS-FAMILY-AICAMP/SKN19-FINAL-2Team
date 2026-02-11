import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_parse_recommended_count_from_user_query():
    from agent.graph import parse_recommended_count

    assert parse_recommended_count("3개 추천") == 3
    assert parse_recommended_count("한 개만") == 1
    assert parse_recommended_count("세 개 추천해줘") == 3
    assert parse_recommended_count("다섯 개 부탁") == 5
    assert parse_recommended_count("추천해줘") is None


def test_explicit_recommended_count_overrides_parsed():
    from main import resolve_recommended_count

    assert resolve_recommended_count("한 개 추천", 4) == 4
    assert resolve_recommended_count("세 개", None) == 3
    assert resolve_recommended_count("추천해줘", None) == 3
    assert resolve_recommended_count("0개", None) == 3
