import pytest
from fastapi.testclient import TestClient

from main import app, get_repository


client = TestClient(app)


def test_recommend_endpoint_returns_note_when_under_three():
    base_perfume_id = next(iter(get_repository().all_candidates())).perfume_id
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": base_perfume_id, "keywords": ["warm"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_perfume_id"] == base_perfume_id
    assert payload["total_available"] >= len(payload["recommendations"])
    assert len(payload["recommendations"]) <= 3
    if payload["total_available"] < 3:
        assert payload["note"]
    else:
        assert payload["note"] is None
    if payload["recommendations"]:
        recommendation = payload["recommendations"][0]
        assert recommendation["feasible"] is True
        assert recommendation["analysis"]
        assert len(recommendation["spray_order"]) == 2


def test_recommend_endpoint_returns_404_for_unknown_base():
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": "UNKNOWN", "keywords": []},
    )

    assert response.status_code == 404


def test_analyze_endpoint_returns_recommendation():
    response = client.post(
        "/layering/analyze",
        json={
            "user_text": "I have CK One. Would Jo Malone Wood Sage & Sea Salt layer well?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_text"]
    assert payload["keywords"] is not None
    assert payload["detected_perfumes"]
    assert payload["recommendation"]
    assert len(payload["recommendation"]["layered_vector"]) == 21


def test_analyze_endpoint_handles_base_only():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "Tell me about CK One"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_perfume_id"]
    assert payload["recommendation"]


def test_analyze_endpoint_handles_no_match():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "completely unrelated text"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] is None
    assert payload["note"]
    assert payload["clarification_prompt"]
    assert isinstance(payload["clarification_options"], list)


def test_analyze_endpoint_handles_empty_text():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "   "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_perfumes"] == []
    assert payload["recommendation"] is None
    assert payload["note"]


def test_analyze_endpoint_handles_application_request():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "레이어링할 때 어디에 어떻게 뿌려야해?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] is None
    assert payload["note"]


def test_analyze_endpoint_handles_brand_layering_request():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "조말론 향수중에 어디에나 레이어링하기 좋은 향수 추천해줘"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["brand_best_perfume"]


def test_analyze_endpoint_handles_similarity_request():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "CK One이랑 비슷한 느낌의 향수 있어?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["similar_perfumes"]
    assert payload["recommendation"] is None
    assert payload["note"]


def test_analyze_endpoint_handles_similarity_request_with_context():
    response = client.post(
        "/layering/analyze",
        json={
            "user_text": "비슷한 향수 있어?",
            "context_recommended_perfume_id": "8701",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["similar_perfumes"]


def test_analyze_endpoint_info_request_prefers_explicit_perfume():
    response = client.post(
        "/layering/analyze",
        json={
            "user_text": "CK One 정보 알려줘",
            "context_recommended_perfume_id": "9300",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_perfume_info"]
    assert payload["recommended_perfume_info"]["perfume_id"] == "8701"


def test_analyze_endpoint_un_jardin_base_is_not_recommended():
    repo = get_repository()
    candidates = repo.find_perfume_candidates("Un Jardin Sur Le Nil", limit=1)
    if not candidates:
        pytest.skip("Un Jardin Sur Le Nil not found in dataset")
    base_id = candidates[0][0].perfume_id

    response = client.post(
        "/layering/analyze",
        json={
            "user_text": "Un Jardin Sur Le Nil Eau De Toilette에서 좀 더 플로럴한 향이 나게 레이어링 해줘",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_perfume_id"] == base_id
    if payload["recommendation"] is not None:
        assert payload["recommendation"]["perfume_id"] != base_id
