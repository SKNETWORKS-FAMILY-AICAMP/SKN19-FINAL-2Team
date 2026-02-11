"""Core algorithms implementing the portable layering specification."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Iterable, List, Sequence, Tuple

from .constants import (
    ACCORDS,
    ACCORD_INDEX,
    CLASH_PAIRS,
    KEYWORD_MAP,
    KEYWORD_VECTOR_BOOST,
)
from .database import PerfumeRepository
from .schemas import (
    DetectedPerfume,
    LayeringCandidate,
    PerfumeBasic,
    PerfumeVector,
    ScoreBreakdown,
)
from .tools_schemas import LayeringComputationResult


GENERIC_NAME_TOKENS = {"coco"}


def get_target_vector(keywords: Sequence[str]) -> List[float]:
    vector = [0.0] * len(ACCORDS)
    for keyword in keywords:
        if keyword is None:
            continue
        normalized = keyword.strip().lower()
        if not normalized:
            continue
        accords = KEYWORD_MAP.get(normalized)
        if not accords:
            continue
        for accord in accords:
            vector[ACCORD_INDEX[accord]] += KEYWORD_VECTOR_BOOST
    return vector


def calculate_advanced_layering(
    base: PerfumeVector,
    candidate: PerfumeVector,
    target_vector: Sequence[float],
) -> LayeringComputationResult:
    penalty, clash_detected = _clash_penalty(base.dominant_accords, candidate.dominant_accords)
    harmony = _harmony_score(base.base_notes, candidate.base_notes)
    bridge = _bridge_bonus(base.vector, candidate.vector)
    target_score = _target_match_score(base.vector, candidate.vector, target_vector)
    feasible, reason = _feasibility_guard(base.vector, target_vector, target_score)
    layered_vector = [
        (base_value + candidate_value) / 2
        for base_value, candidate_value in zip(base.vector, candidate.vector)
    ]
    total_score = 1.0 + harmony + bridge + penalty + target_score
    score_breakdown = ScoreBreakdown(
        harmony=harmony,
        bridge=bridge,
        penalty=penalty,
        target=target_score,
    )
    spray_order = _spray_order(base, candidate)
    return LayeringComputationResult(
        candidate=candidate,
        total_score=total_score,
        feasible=feasible,
        feasibility_reason=reason,
        clash_detected=clash_detected,
        spray_order=spray_order,
        score_breakdown=score_breakdown,
        layered_vector=layered_vector,
    )


def rank_recommendations(
    base_perfume_id: str,
    keywords: Sequence[str],
    repository: PerfumeRepository,
    input_name_keys: set[str] | None = None,
) -> Tuple[List[LayeringCandidate], int]:
    base = repository.get_perfume(base_perfume_id)
    target_vector = get_target_vector(keywords)
    candidates: List[LayeringCandidate] = []
    for candidate in repository.all_candidates(exclude_id=base_perfume_id):
        if input_name_keys and _matches_input_name(candidate, input_name_keys):
            continue
        if _should_exclude_candidate(base, candidate):
            continue
        result = calculate_advanced_layering(base, candidate, target_vector)
        if not result.feasible:
            continue
        candidates.append(_result_to_candidate(result))
    candidates.sort(key=lambda item: item.total_score, reverse=True)
    total_available = len(candidates)
    return candidates[:3], total_available


def rank_worst_match(
    base_perfume_id: str,
    repository: PerfumeRepository,
) -> LayeringCandidate | None:
    base = repository.get_perfume(base_perfume_id)
    target_vector: List[float] = [0.0] * len(base.vector)
    worst_result: LayeringComputationResult | None = None
    worst_score: float | None = None
    for candidate in repository.all_candidates(exclude_id=base_perfume_id):
        if _should_exclude_candidate(base, candidate):
            continue
        result = calculate_advanced_layering(base, candidate, target_vector)
        comparison_score = result.total_score - result.score_breakdown.target
        if worst_score is None or comparison_score < worst_score:
            worst_result = result
            worst_score = comparison_score
    if worst_result is None:
        return None
    return _result_to_candidate(worst_result)


def _strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _normalize_brand_name(name: str) -> str:
    cleaned = _strip_diacritics(name).casefold()
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", cleaned)
    return " ".join(cleaned.split())


def _brands_compatible(base_brand: str, candidate_brand: str) -> bool:
    base = _normalize_brand_name(base_brand)
    candidate = _normalize_brand_name(candidate_brand)
    if not base or not candidate:
        return False
    if base == candidate:
        return True
    return base in candidate or candidate in base


def _normalize_identity(name: str, brand: str) -> str:
    normalized_brand = _normalize_brand_name(brand)
    normalized_name = _normalize_perfume_name(name)
    return f"{normalized_brand}::{normalized_name}"


def _tokenize_text(text: str) -> List[str]:
    cleaned = _strip_diacritics(text).casefold()
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", cleaned)
    return [token for token in cleaned.split() if token]


def _perfume_drop_tokens() -> set[str]:
    return {
        "eau",
        "de",
        "toilette",
        "parfum",
        "perfume",
        "cologne",
        "edp",
        "edt",
        "edc",
        "intense",
        "elixir",
        "absolu",
        "absolute",
        "absolue",
        "extreme",
        "extrait",
        "spray",
        "오",
        "드",
        "오드",
        "퍼퓸",
        "퍼품",
        "뚜왈렛",
        "뚜알렛",
        "코롱",
        "오드퍼퓸",
        "오드뚜왈렛",
        "오드코롱",
    }


def _normalize_perfume_name(name: str) -> str:
    tokens = _tokenize_text(name)
    drop_tokens = _perfume_drop_tokens()
    filtered = [token for token in tokens if token not in drop_tokens]
    return " ".join(filtered)


def _normalize_core_name(name: str, concentration: str | None) -> str:
    tokens = _tokenize_text(name)
    drop_tokens = set(_perfume_drop_tokens())
    if concentration:
        drop_tokens.update(_tokenize_text(concentration))
    filtered = [token for token in tokens if token not in drop_tokens]
    return " ".join(filtered)


def _is_generic_name_key(name_key: str) -> bool:
    tokens = [token for token in name_key.split() if token]
    return bool(tokens) and set(tokens).issubset(GENERIC_NAME_TOKENS)


def build_input_name_keys(
    user_text: str | None,
    detected_perfumes: Sequence[PerfumeBasic | DetectedPerfume] | None = None,
) -> set[str]:
    keys: set[str] = set()
    if detected_perfumes:
        for perfume in detected_perfumes:
            name = getattr(perfume, "perfume_name", "")
            concentration = getattr(perfume, "concentration", None)
            name_key = _normalize_perfume_name(name)
            core_key = _normalize_core_name(name, concentration)
            if name_key:
                keys.add(name_key)
            if core_key:
                keys.add(core_key)
            matched_text = getattr(perfume, "matched_text", None)
            if matched_text:
                matched_key = _normalize_perfume_name(str(matched_text))
                if matched_key:
                    keys.add(matched_key)

    if user_text:
        tokens = _tokenize_text(user_text)
        if 1 <= len(tokens) <= 4:
            fallback_key = _normalize_perfume_name(user_text)
            if fallback_key and not _is_generic_name_key(fallback_key):
                keys.add(fallback_key)

    return {key for key in keys if key}


def _perfume_name_identity(name: str, concentration: str | None) -> str:
    return _normalize_core_name(name, concentration)


def _line_tokens(name: str, concentration: str | None) -> List[str]:
    tokens = _tokenize_text(name)
    drop_tokens = set(_perfume_drop_tokens())
    if concentration:
        drop_tokens.update(_tokenize_text(concentration))
    return [token for token in tokens if token not in drop_tokens]


def _common_prefix_length(left: Sequence[str], right: Sequence[str]) -> int:
    limit = min(len(left), len(right))
    count = 0
    for index in range(limit):
        if left[index] != right[index]:
            break
        count += 1
    return count


def _is_same_line_family(base: PerfumeVector, candidate: PerfumeVector) -> bool:
    base_tokens = _line_tokens(base.perfume_name, base.concentration)
    candidate_tokens = _line_tokens(candidate.perfume_name, candidate.concentration)
    if not base_tokens or not candidate_tokens:
        return False
    prefix_length = _common_prefix_length(base_tokens, candidate_tokens)
    if prefix_length >= 2:
        return True
    if prefix_length >= 1 and (len(base_tokens) == 1 or len(candidate_tokens) == 1):
        return True
    return False


def _is_same_or_normalized_name(base: PerfumeVector, candidate: PerfumeVector) -> bool:
    base_name = _perfume_name_identity(base.perfume_name, base.concentration)
    candidate_name = _perfume_name_identity(candidate.perfume_name, candidate.concentration)
    return bool(base_name and candidate_name and base_name == candidate_name)


def _has_generic_overlap_only(base: PerfumeVector, candidate: PerfumeVector) -> bool:
    base_tokens = set(_line_tokens(base.perfume_name, base.concentration))
    candidate_tokens = set(_line_tokens(candidate.perfume_name, candidate.concentration))
    if not base_tokens or not candidate_tokens:
        return False
    shared = base_tokens & candidate_tokens
    return bool(shared) and shared.issubset(GENERIC_NAME_TOKENS)


def _should_exclude_candidate(base: PerfumeVector, candidate: PerfumeVector) -> bool:
    if base.perfume_id == candidate.perfume_id:
        return True
    base_key = _normalize_identity(base.perfume_name, base.perfume_brand)
    candidate_key = _normalize_identity(candidate.perfume_name, candidate.perfume_brand)
    if base_key == candidate_key:
        return True
    if _is_same_or_normalized_name(base, candidate):
        return True
    if _brands_compatible(base.perfume_brand, candidate.perfume_brand):
        if _has_generic_overlap_only(base, candidate):
            return True
    if _is_same_perfume_identity(base, candidate):
        return True
    return False


def _matches_input_name(candidate: PerfumeVector, input_name_keys: set[str]) -> bool:
    if not input_name_keys:
        return False
    candidate_key = _normalize_core_name(candidate.perfume_name, candidate.concentration)
    if candidate_key and candidate_key in input_name_keys:
        return True
    candidate_name = _normalize_perfume_name(candidate.perfume_name)
    if candidate_name and candidate_name in input_name_keys:
        return True
    return False


def _is_same_perfume_identity(base: PerfumeVector, candidate: PerfumeVector) -> bool:
    base_brand = _normalize_brand_name(base.perfume_brand)
    candidate_brand = _normalize_brand_name(candidate.perfume_brand)
    if base_brand and candidate_brand:
        if not _brands_compatible(base.perfume_brand, candidate.perfume_brand):
            return False
    base_name = _normalize_core_name(base.perfume_name, base.concentration)
    candidate_name = _normalize_core_name(candidate.perfume_name, candidate.concentration)
    if base_name and candidate_name and base_name == candidate_name:
        return True
    if _is_same_line_family(base, candidate):
        return True
    if base_name and candidate_name:
        if base_name in candidate_name or candidate_name in base_name:
            base_tokens = set(base_name.split())
            candidate_tokens = set(candidate_name.split())
            drop_tokens = _perfume_drop_tokens()
            if base_tokens.issubset(candidate_tokens):
                extra = candidate_tokens - base_tokens
            else:
                extra = base_tokens - candidate_tokens
            if extra.issubset(drop_tokens):
                return True
    return False


def _build_brand_reason(
    avg_score: float,
    feasible_count: int,
    perfume: PerfumeVector,
) -> str:
    if feasible_count <= 0:
        return "브랜드 내 레이어링 후보가 제한적이라 가장 안정적인 향을 골랐습니다."

    dominant = [accord for accord in perfume.dominant_accords if accord]
    if dominant:
        accords_text = ", ".join(dominant[:3])
        detail = f"대표 어코드가 {accords_text} 계열이라 다양한 향과 조화가 좋아요."
    else:
        detail = "향의 균형이 안정적이라 다른 향과 섞었을 때 무리가 적습니다."

    return (
        f"브랜드 내 {feasible_count}개 조합에서 평균 궁합 점수 {avg_score:.2f}로 안정적인 편이라, "
        f"레이어링 범용성이 높습니다. {detail}"
    )


def evaluate_pair(
    base_perfume_id: str,
    candidate_perfume_id: str,
    keywords: Sequence[str],
    repository: PerfumeRepository,
) -> LayeringCandidate:
    base = repository.get_perfume(base_perfume_id)
    candidate = repository.get_perfume(candidate_perfume_id)
    target_vector = get_target_vector(keywords)
    result = calculate_advanced_layering(base, candidate, target_vector)
    return _result_to_candidate(result)


def calculate_compatibility_score(
    base: PerfumeVector,
    candidate: PerfumeVector,
) -> Tuple[float, bool]:
    neutral_target = [0.0] * len(base.vector)
    result = calculate_advanced_layering(base, candidate, neutral_target)
    score = result.total_score - result.score_breakdown.target
    return score, result.feasible


def rank_brand_universal_perfume(
    brand_perfumes: Sequence[PerfumeVector],
    repository: PerfumeRepository,
) -> Tuple[PerfumeVector | None, float, int, str | None]:
    all_candidates = list(repository.all_candidates())
    best_perfume: PerfumeVector | None = None
    best_score = float("-inf")
    best_count = 0

    for base in brand_perfumes:
        total_score = 0.0
        count = 0
        for candidate in all_candidates:
            if candidate.perfume_id == base.perfume_id:
                continue
            score, feasible = calculate_compatibility_score(base, candidate)
            if not feasible:
                continue
            total_score += score
            count += 1
        average_score = total_score / count if count else 0.0
        if best_perfume is None or average_score > best_score:
            best_perfume = base
            best_score = average_score
            best_count = count

    if best_perfume is None:
        return None, 0.0, 0, None
    reason = _build_brand_reason(best_score, best_count, best_perfume)
    return best_perfume, best_score, best_count, reason


def rank_similar_perfumes(
    base_perfume_id: str,
    repository: PerfumeRepository,
    limit: int = 3,
) -> List[PerfumeBasic]:
    try:
        base = repository.get_perfume(base_perfume_id)
    except KeyError:
        return []
    scored: List[tuple[PerfumeVector, float]] = []
    for candidate in repository.all_candidates(exclude_id=base_perfume_id):
        if _should_exclude_candidate(base, candidate):
            continue
        similarity = _cosine_similarity(base.vector, candidate.vector)
        if similarity <= 0:
            continue
        scored.append((candidate, similarity))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [
        PerfumeBasic(
            perfume_id=candidate.perfume_id,
            perfume_name=candidate.perfume_name,
            perfume_brand=candidate.perfume_brand,
            image_url=candidate.image_url,
            concentration=candidate.concentration,
        )
        for candidate, _ in scored[:limit]
    ]




def _clash_penalty(
    base_dominant: Iterable[str],
    candidate_dominant: Iterable[str],
) -> Tuple[float, bool]:
    base_set = set(base_dominant)
    candidate_set = set(candidate_dominant)
    for left, right in CLASH_PAIRS:
        if (base_set & left and candidate_set & right) or (base_set & right and candidate_set & left):
            return -1.0, True
    return 0.0, False


def _harmony_score(base_notes: Sequence[str], candidate_notes: Sequence[str]) -> float:
    base_set = {note.strip().lower() for note in base_notes if note}
    candidate_set = {note.strip().lower() for note in candidate_notes if note}
    if not base_set or not candidate_set:
        return 0.0
    intersection = base_set & candidate_set
    union = base_set | candidate_set
    similarity = len(intersection) / len(union) if union else 0.0
    if similarity == 0.0:
        return 0.0
    if 0.4 <= similarity <= 0.7:
        return 1.0
    if similarity > 0.7:
        return 0.5
    return 0.0


def _bridge_bonus(base_vector: Sequence[float], candidate_vector: Sequence[float]) -> float:
    bonus = 0.0
    for base_value, candidate_value in zip(base_vector, candidate_vector):
        if 5.0 <= base_value <= 15.0 and 5.0 <= candidate_value <= 15.0:
            bonus += 0.4
    return bonus


def _target_match_score(
    base_vector: Sequence[float],
    candidate_vector: Sequence[float],
    target_vector: Sequence[float],
) -> float:
    if len(target_vector) != len(base_vector):
        raise ValueError("Target vector length mismatch")
    result_vector = [
        (base_value + candidate_value) / 2
        for base_value, candidate_value in zip(base_vector, candidate_vector)
    ]
    distance = math.sqrt(
        sum((target - result) ** 2 for target, result in zip(target_vector, result_vector))
    )
    return max(0.0, 1.5 - (distance / 50.0))


def _feasibility_guard(
    base_vector: Sequence[float],
    target_vector: Sequence[float],
    target_score: float,
) -> Tuple[bool, str | None]:
    if not any(value > 0 for value in target_vector):
        return True, None

    if target_score < 0.6:
        return False, "Target alignment below threshold"

    base_top = _top_dominant(base_vector, 2)
    target_top = _top_dominant(target_vector, 2, threshold=0.0)
    if not target_top:
        return True, None

    for left, right in CLASH_PAIRS:
        if (_contains_pair(base_top, target_top, left, right)) or (
            _contains_pair(base_top, target_top, right, left)
        ):
            return False, "Dominant accords clash with target"
    return True, None


def _contains_pair(
    source: Sequence[str],
    target: Sequence[str],
    left: Iterable[str],
    right: Iterable[str],
) -> bool:
    return any(item in left for item in source) and any(item in right for item in target)


def _top_dominant(
    vector: Sequence[float],
    limit: int,
    threshold: float = 5.0,
) -> List[str]:
    ranked = sorted(
        (
            (value, ACCORDS[index])
            for index, value in enumerate(vector)
            if value > threshold
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [name for _, name in ranked[:limit]]


def _spray_order(base: PerfumeVector, candidate: PerfumeVector) -> List[str]:
    if base.persistence_score >= candidate.persistence_score:
        first, second = base, candidate
    else:
        first, second = candidate, base
    return [
        f"{first.perfume_name}",
        f"{second.perfume_name}",
    ]


def _result_to_candidate(result: LayeringComputationResult) -> LayeringCandidate:
    candidate = result.candidate
    # 추천 이유 텍스트를 바꾸려면 _build_analysis_string() 로직을 조정
    dominant_accord = _highest_accord_name(result.layered_vector)
    analysis = _build_analysis_string(result.score_breakdown, dominant_accord)
    return LayeringCandidate(
        perfume_id=candidate.perfume_id,
        perfume_name=candidate.perfume_name,
        perfume_brand=candidate.perfume_brand,
        image_url=candidate.image_url,
        concentration=candidate.concentration,
        total_score=round(result.total_score, 3),
        feasible=result.feasible,
        feasibility_reason=result.feasibility_reason,
        spray_order=result.spray_order,
        score_breakdown=result.score_breakdown,
        clash_detected=result.clash_detected,
        analysis=analysis,
        layered_vector=result.layered_vector,
    )


def _cosine_similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def _highest_accord_name(vector: Sequence[float]) -> str | None:
    if not vector:
        return None
    highest_value: float | None = None
    highest_index: int | None = None
    for index, value in enumerate(vector):
        if index >= len(ACCORDS):
            break
        if highest_value is None or value > highest_value:
            highest_value = value
            highest_index = index
    if highest_value is None or highest_value <= 0:
        return None
    if highest_index is None:
        return None
    return ACCORDS[highest_index]


def _build_analysis_string(breakdown: ScoreBreakdown, dominant_accord: str | None) -> str:
    reasons: list[str] = []
    if dominant_accord:
        reasons.append(f"대표 어코드가 {dominant_accord} 계열이라 요청한 무드에 잘 맞아요.")

    if breakdown.target >= 1.1:
        reasons.append("요청한 무드와 잘 맞는 어코드가 또렷하게 살아납니다.")
    elif breakdown.target >= 0.8:
        reasons.append("원하는 분위기에 자연스럽게 가까워지는 조합입니다.")
    else:
        reasons.append("기존 향의 균형을 크게 흐트러뜨리지 않아 부담 없이 섞기 좋습니다.")

    if breakdown.harmony >= 1.0:
        reasons.append("공통 노트가 있어 잔향이 자연스럽게 이어집니다.")
    elif breakdown.bridge >= 0.8:
        reasons.append("어코드 흐름이 매끄러워 전체 톤이 안정적으로 이어집니다.")

    if breakdown.penalty < 0:
        reasons.append("대비되는 포인트가 더해져 개성이 살아나는 레이어링입니다.")

    if len(reasons) < 2:
        reasons.append("충돌 포인트가 적어 기본 레이어링으로도 안정적인 조합입니다.")

    complementary = "서로의 향이 보완되어 잔향 보완과 지속력 강화, 밸런스 조정에 도움이 됩니다."
    if breakdown.bridge >= 0.8 or breakdown.harmony >= 1.0:
        chemistry = "베이스 공유와 어코드 조화가 뚜렷해 이질감 최소화에 유리합니다."
    else:
        chemistry = "베이스 공유가 크진 않더라도 어코드 조화로 이질감 최소화에 초점을 둔 조합입니다."
    vibe = "향의 대비가 더해져 반전 매력과 입체적인 향이 살아나며 고유한 무드를 확장합니다."

    return " ".join([*reasons[:2], complementary, vibe, chemistry])
