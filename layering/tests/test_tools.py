from agent.constants import ACCORD_INDEX, ACCORDS
from agent.database import PerfumeRepository
from agent.schemas import DetectedPerfume, PerfumeVector, ScoreBreakdown
from agent.tools import (
    _build_analysis_string,
    _clash_penalty,
    _harmony_score,
    _highest_accord_name,
    _matches_input_name,
    _is_same_or_normalized_name,
    _is_same_perfume_identity,
    _should_exclude_candidate,
    build_input_name_keys,
    calculate_compatibility_score,
    calculate_advanced_layering,
    evaluate_pair,
    get_target_vector,
    rank_brand_universal_perfume,
    rank_recommendations,
    rank_similar_perfumes,
)


def _sample_pair(repo: PerfumeRepository):
    base = next(iter(repo.all_candidates()))
    candidate = next(iter(repo.all_candidates(exclude_id=base.perfume_id)))
    return base, candidate


def _make_perfume_vector(
    perfume_id: str,
    name: str,
    brand: str,
    concentration: str | None,
) -> PerfumeVector:
    return PerfumeVector(
        perfume_id=perfume_id,
        perfume_name=name,
        perfume_brand=brand,
        concentration=concentration,
        image_url=None,
        vector=[0.0] * len(ACCORDS),
        total_intensity=0.0,
        persistence_score=0.0,
        dominant_accords=[],
        base_notes=[],
    )


def test_get_target_vector_applies_keyword_boost():
    vector = get_target_vector(["citrus", "amber", "floral"])
    assert vector[ACCORD_INDEX["Citrus"]] == 30.0
    assert vector[ACCORD_INDEX["Fresh"]] == 30.0
    assert vector[ACCORD_INDEX["Resinous"]] == 30.0
    assert vector[ACCORD_INDEX["Floral"]] == 30.0


def test_get_target_vector_korean_cool_keywords():
    vector = get_target_vector(["차가운"])
    assert vector[ACCORD_INDEX["Aquatic"]] == 30.0
    assert vector[ACCORD_INDEX["Fresh"]] == 30.0
    assert vector[ACCORD_INDEX["Green"]] == 30.0


def test_calculate_advanced_layering_returns_scores():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    target = get_target_vector(["warm"])

    result = calculate_advanced_layering(base, candidate, target)

    assert result.score_breakdown.target >= 0
    assert result.total_score > 0
    assert len(result.spray_order) == 2


def test_rank_recommendations_limits_to_top_three():
    repo = PerfumeRepository()
    base, _ = _sample_pair(repo)
    recommendations, total = rank_recommendations(base.perfume_id, [], repo)

    assert len(recommendations) <= 3
    assert total >= len(recommendations)


def test_calculate_advanced_layering_flags_clash_penalty():
    penalty, clash_detected = _clash_penalty(["Aquatic"], ["Gourmand"])
    assert clash_detected is True
    assert penalty == -1.0


def test_calculate_advanced_layering_blocks_low_target_alignment():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    target = [500.0] * len(base.vector)

    result = calculate_advanced_layering(base, candidate, target)

    assert result.feasible is False
    assert result.feasibility_reason == "Target alignment below threshold"


def test_harmony_score_uses_jaccard_thresholds():
    assert _harmony_score(["Amber", "Musk"], ["Amber", "Musk", "Woody"]) == 1.0
    assert _harmony_score(["Amber", "Musk"], ["Amber", "Musk"]) == 0.5
    assert _harmony_score(["Amber"], ["Citrus"]) == 0.0


def test_evaluate_pair_returns_candidate():
    repo = PerfumeRepository()
    result = evaluate_pair("8701", "9300", ["fresh"], repo)

    assert result.perfume_id == "9300"
    assert result.total_score > 0


def test_calculate_compatibility_score_returns_value():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    score, feasible = calculate_compatibility_score(base, candidate)

    assert isinstance(score, float)
    assert isinstance(feasible, bool)


def test_rank_brand_universal_perfume_returns_top_pick():
    repo = PerfumeRepository()
    sample = next(iter(repo.all_candidates()))
    brand_perfumes = repo.get_brand_perfumes(sample.perfume_brand)

    best_perfume, avg_score, count, reason = rank_brand_universal_perfume(brand_perfumes, repo)

    assert best_perfume is not None
    assert isinstance(avg_score, float)
    assert isinstance(count, int)
    assert isinstance(reason, str)


def test_rank_brand_universal_perfume_handles_empty_list():
    repo = PerfumeRepository()
    best_perfume, avg_score, count, reason = rank_brand_universal_perfume([], repo)

    assert best_perfume is None
    assert avg_score == 0.0
    assert count == 0
    assert reason is None


def test_get_target_vector_spicy_keyword():
    vector = get_target_vector(["spicy"])
    assert vector[ACCORD_INDEX["Spicy"]] == 30.0


def test_rank_recommendations_excludes_base_name_brand():
    repo = PerfumeRepository()
    base = next(iter(repo.all_candidates()))
    recommendations, _ = rank_recommendations(base.perfume_id, [], repo)

    base_name = base.perfume_name.lower()
    base_brand = base.perfume_brand.lower()
    assert all(
        not (
            rec.perfume_name.lower() == base_name
            and rec.perfume_brand.lower() == base_brand
        )
        for rec in recommendations
    )


def test_rank_similar_perfumes_excludes_base():
    repo = PerfumeRepository()
    base = next(iter(repo.all_candidates()))
    similars = rank_similar_perfumes(base.perfume_id, repo, limit=3)

    assert all(similar.perfume_id != base.perfume_id for similar in similars)


def test_rank_similar_perfumes_handles_unknown_base():
    repo = PerfumeRepository()
    similars = rank_similar_perfumes("UNKNOWN", repo)

    assert similars == []


def test_is_same_perfume_identity_handles_concentration_variants():
    base = _make_perfume_vector(
        "base",
        "Ange Ou Demon",
        "Givenchy",
        "Eau de Parfum",
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Ange Ou Demon",
        "Givenchy",
        "Eau de Toilette",
    )

    assert _is_same_perfume_identity(base, candidate) is True


def test_is_same_perfume_identity_handles_elixir_variants_without_concentration():
    base = _make_perfume_vector(
        "base",
        "Pure Poison",
        "Dior",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Pure Poison Elixir",
        "Christian Dior",
        None,
    )

    assert _is_same_perfume_identity(base, candidate) is True


def test_is_same_perfume_identity_detects_same_line_flankers():
    base = _make_perfume_vector(
        "base",
        "Poison",
        "Dior",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Poison Girl",
        "Dior",
        None,
    )

    assert _is_same_perfume_identity(base, candidate) is True


def test_is_same_perfume_identity_detects_jadore_line_variants():
    base = _make_perfume_vector(
        "base",
        "J Adore L Or",
        "Dior",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "J Adore In Joy",
        "Dior",
        None,
    )

    assert _is_same_perfume_identity(base, candidate) is True


def test_is_same_or_normalized_name_matches_case_spacing():
    base = _make_perfume_vector(
        "base",
        "Coco Noir",
        "Chanel",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "coco  noir",
        "CHANEL",
        None,
    )

    assert _is_same_or_normalized_name(base, candidate) is True


def test_should_exclude_candidate_blocks_same_name():
    base = _make_perfume_vector(
        "base",
        "Coco Noir",
        "Chanel",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Coco Noir",
        "Chanel",
        "Extrait de Parfum",
    )

    assert _should_exclude_candidate(base, candidate) is True


def test_should_exclude_candidate_blocks_same_name_with_concentration_in_name():
    base = _make_perfume_vector(
        "base",
        "Coco Noir",
        "Chanel",
        "Eau de Parfum",
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Coco Noir Extrait de Parfum",
        "Chanel",
        None,
    )

    assert _should_exclude_candidate(base, candidate) is True


def test_should_exclude_candidate_blocks_generic_overlap_same_brand():
    base = _make_perfume_vector(
        "base",
        "Coco Mademoiselle",
        "Chanel",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Coco Noir",
        "Chanel",
        None,
    )

    assert _should_exclude_candidate(base, candidate) is True


def test_build_input_name_keys_uses_detected_perfume_and_matched_text():
    detected = [
        DetectedPerfume(
            perfume_id="base",
            perfume_name="Coco Noir",
            perfume_brand="Chanel",
            match_score=1.0,
            matched_text="샤넬 코코 느와르",
        )
    ]
    keys = build_input_name_keys("샤넬 코코 느와르랑 어울리는 향수 추천해줘", detected)

    assert "coco noir" in keys
    assert "샤넬 코코 느와르" in keys


def test_matches_input_name_blocks_candidate():
    keys = {"coco noir"}
    candidate = _make_perfume_vector(
        "candidate",
        "Coco Noir",
        "Some Brand",
        "Eau de Parfum",
    )

    assert _matches_input_name(candidate, keys) is True


def test_should_exclude_candidate_allows_generic_overlap_different_brand():
    base = _make_perfume_vector(
        "base",
        "Coco Mademoiselle",
        "Chanel",
        None,
    )
    candidate = _make_perfume_vector(
        "candidate",
        "Coco",
        "Generic Brand",
        None,
    )

    assert _should_exclude_candidate(base, candidate) is False


def test_highest_accord_name_and_analysis_mentions_dominant():
    vector = [0.0] * len(ACCORDS)
    vector[ACCORD_INDEX["Citrus"]] = 12.0
    dominant = _highest_accord_name(vector)
    breakdown = ScoreBreakdown(harmony=0.0, bridge=0.0, penalty=0.0, target=0.5)
    analysis = _build_analysis_string(breakdown, dominant)

    assert dominant == "Citrus"
    assert "Citrus" in analysis
    assert "잔향 보완" in analysis
    assert "지속력 강화" in analysis
    assert "밸런스 조정" in analysis
    assert "반전 매력" in analysis
    assert "입체적인 향" in analysis
    assert "고유한 무드" in analysis
    assert "베이스 공유" in analysis
    assert "어코드 조화" in analysis
    assert "이질감 최소화" in analysis
