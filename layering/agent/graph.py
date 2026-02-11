"""Graph-based orchestration helpers for user-driven layering flows."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from .constants import KEYWORD_MAP
from .database import PerfumeRepository, get_perfume_info
from .prompts import USER_PREFERENCE_PROMPT
from .schemas import (
    DetectedPair,
    DetectedPerfume,
    PairingAnalysis,
    PerfumeBasic,
    UserQueryAnalysis,
)
from .tools import (
    _matches_input_name,
    _should_exclude_candidate,
    build_input_name_keys,
    evaluate_pair,
    rank_brand_universal_perfume,
    rank_recommendations,
    rank_worst_match,
    rank_similar_perfumes,
)


class PreferenceSummary(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    intensity: float = 0.5
    raw_text: str = ""


def _normalize_keywords(raw_keywords: Any) -> list[str]:
    if isinstance(raw_keywords, str):
        raw_items = [raw_keywords]
    elif isinstance(raw_keywords, list):
        raw_items = raw_keywords
    else:
        raw_items = []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if item is None:
            continue
        text = str(item)
        parts = [chunk.strip().lower() for chunk in text.replace(";", ",").split(",") if chunk.strip()]
        for part in parts:
            if part in seen:
                continue
            seen.add(part)
            normalized.append(part)
    return normalized


def _split_query_segments(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    separators = [" and ", "&", ",", ";", " 그리고 ", " 또는 ", " 혹은 "]
    segments = [lowered]
    for sep in separators:
        next_segments: list[str] = []
        for segment in segments:
            next_segments.extend(segment.split(sep))
        segments = next_segments
    cleaned = [segment.strip() for segment in segments if segment.strip()]
    return cleaned


def _heuristic_preferences(user_text: str) -> PreferenceSummary:
    normalized = user_text.lower()
    matched = [key for key in KEYWORD_MAP if key in normalized]
    keywords = []
    for key in matched:
        if any(other != key and key in other for other in matched):
            if len(key) < max(len(other) for other in matched if key in other):
                continue
        keywords.append(key)
    intensity = 0.5
    high_tokens = [
        "매우",
        "아주",
        "진하게",
        "강렬하게",
        "강하게",
        "intense",
        "strong",
        "bold",
    ]
    mid_tokens = ["적당히", "중간", "보통", "적당한", "무난하게"]
    low_tokens = ["살짝", "은은하게", "가볍게", "약하게", "soft", "light"]
    if any(token in normalized for token in high_tokens):
        intensity = 0.9
    elif any(token in normalized for token in low_tokens):
        intensity = 0.3
    elif any(token in normalized for token in mid_tokens):
        intensity = 0.55
    return PreferenceSummary(keywords=keywords, intensity=intensity, raw_text=user_text)


def _normalize_text_for_match(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9가-힣]+", " ", text.casefold())
    return " ".join(cleaned.split())


def _extract_base_hint(user_text: str) -> str | None:
    if not user_text:
        return None
    patterns = [
        r"(.+?)과\s*비슷",
        r"(.+?)와\s*비슷",
        r"(.+?)랑\s*비슷",
        r"(.+?)하고\s*비슷",
        r"(.+?)에서",
        r"(.+?)을\s*기반",
        r"(.+?)를\s*기반",
        r"(.+?)을\s*베이스",
        r"(.+?)를\s*베이스",
        r"(.+?)을\s*바탕",
        r"(.+?)를\s*바탕",
        r"(.+?)을\s*가지고",
        r"(.+?)를\s*가지고",
        r"(.+?)이\s*있",
        r"(.+?)가\s*있",
    ]
    earliest = None
    for pattern in patterns:
        match = re.search(pattern, user_text, flags=re.IGNORECASE)
        if not match:
            continue
        hint = match.group(1).strip()
        if not hint:
            continue
        if earliest is None or match.start() < earliest[0]:
            earliest = (match.start(), hint)
    return earliest[1] if earliest else None


def _prioritize_base_hint(
    user_text: str,
    repository: PerfumeRepository,
    detected_perfumes: list[DetectedPerfume],
) -> list[DetectedPerfume]:
    base_hint = _extract_base_hint(user_text)
    if not base_hint:
        return detected_perfumes
    hint_candidates = repository.find_perfume_candidates(
        base_hint,
        limit=3,
        min_score=0.6,
    )
    if not hint_candidates:
        return detected_perfumes
    perfume, score, matched_text = hint_candidates[0]
    if detected_perfumes and detected_perfumes[0].perfume_id == perfume.perfume_id:
        return detected_perfumes
    hinted = DetectedPerfume(
        perfume_id=perfume.perfume_id,
        perfume_name=perfume.perfume_name,
        perfume_brand=perfume.perfume_brand,
        match_score=score,
        matched_text=matched_text,
    )
    remaining = [
        item for item in detected_perfumes if item.perfume_id != perfume.perfume_id
    ]
    return [hinted, *remaining]


def _merge_candidate_hits(
    hits: list[tuple[Any, float, str]],
) -> list[tuple[Any, float, str]]:
    merged: dict[str, tuple[Any, float, str]] = {}
    for perfume, score, matched_text in hits:
        current = merged.get(perfume.perfume_id)
        if current is None or score > current[1]:
            merged[perfume.perfume_id] = (perfume, score, matched_text)
    return list(merged.values())


def _extract_perfume_query_llm(user_text: str) -> list[str]:
    if not os.getenv("OPENAI_API_KEY"):
        return []
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
    except ImportError:
        return []

    system_prompt = (
        "You are a perfume database expert. Extract a perfume brand and name from the user input. "
        "Return JSON with keys: brand, name. Use English names when possible. "
        "If no perfume is mentioned, return empty strings."
    )
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_text)]
    try:
        response = model.invoke(messages)
        raw_text = response.content
        if isinstance(raw_text, str):
            payload_text = raw_text
        else:
            payload_text = (
                json.dumps(raw_text, ensure_ascii=False) if raw_text is not None else ""
            )
        payload_text = payload_text or ""
        start = payload_text.find("{")
        end = payload_text.rfind("}")
        if start == -1 or end == -1:
            return []
        payload = json.loads(payload_text[start : end + 1])
    except Exception:
        return []

    if not isinstance(payload, dict):
        return []
    brand = str(payload.get("brand", "")).strip()
    name = str(payload.get("name", "")).strip()
    queries: list[str] = []
    if brand and name:
        queries.append(f"{brand} {name}")
    if name:
        queries.append(name)
    return queries



def _collect_perfume_candidates(
    user_text: str,
    repository: PerfumeRepository,
    limit: int = 6,
) -> list[tuple[Any, float, str]]:
    hits: list[tuple[Any, float, str]] = []
    
    # 1. Detect explicit brands from user text
    detected_brands = set(repository.find_brand_candidates(user_text))
    
    # 2. Collect initial candidates
    hits.extend(repository.find_perfume_candidates(user_text, limit=limit))

    segments = _split_query_segments(user_text)
    for segment in segments:
        if segment == user_text:
            continue
        hits.extend(repository.find_perfume_candidates(segment, limit=limit))

    if not hits:
        normalized = _normalize_text_for_match(user_text)
        tokens = normalized.split()
        if 2 <= len(tokens) <= 8:
            for size in range(2, min(5, len(tokens)) + 1):
                for idx in range(len(tokens) - size + 1):
                    phrase = " ".join(tokens[idx : idx + size])
                    hits.extend(repository.find_perfume_candidates(phrase, limit=limit))

    llm_queries = _extract_perfume_query_llm(user_text)
    if not hits:
        for query in llm_queries:
            hits.extend(repository.find_perfume_candidates(query, limit=limit))
            


    # [Start of Brand Bias Logic]
    # If LLM found a brand, add it to detected brands
    # (Note: _extract_perfume_query_llm returns strings like "Brand Name" or "Name". 
    # capturing the brand separately would require changing that function, 
    # but we can try to infer from the query or rely on find_brand_candidates)
    
    adjusted_hits = []
    for perfume, score, matched_text in hits:
        # Check if the perfume's brand matches any detected brand
        perfume_brand_norm = perfume.perfume_brand.strip().lower()
        
        is_brand_match = False
        for brand in detected_brands:
            if brand.lower() in perfume_brand_norm or perfume_brand_norm in brand.lower():
                is_brand_match = True
                break
        
        # Apply strict boost/penalty
        final_score = score
        if detected_brands:
            if is_brand_match:
                # Boost significant brand matches
                final_score *= 1.5 
            else:
                # Penalize non-matching brands when a brand is explicitly requested
                final_score *= 0.5
                
        adjusted_hits.append((perfume, final_score, matched_text))
        
    return _merge_candidate_hits(adjusted_hits)


def analyze_user_input(user_text: str) -> PreferenceSummary:
    """Analyze free-form user text to extract accord keywords and intensity."""

    if not user_text or not user_text.strip():
        return PreferenceSummary(raw_text=user_text or "")
    if not os.getenv("OPENAI_API_KEY"):
        return _heuristic_preferences(user_text)

    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
    except ImportError:
        return _heuristic_preferences(user_text)

    prompt = ChatPromptTemplate.from_template(USER_PREFERENCE_PROMPT)
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    chain = prompt | model | StrOutputParser()
    response = ""
    try:
        response = chain.invoke({"user_input": user_text})
        payload = json.loads(response)
    except Exception:
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                payload = json.loads(response[start : end + 1])
            else:
                return _heuristic_preferences(user_text)
        except Exception:
            return _heuristic_preferences(user_text)

    raw_keywords = payload.get("keywords", []) if isinstance(payload, dict) else []
    keywords = _normalize_keywords(raw_keywords)
    keywords = [keyword for keyword in keywords if keyword in KEYWORD_MAP]
    intensity = payload.get("intensity", 0.5) if isinstance(payload, dict) else 0.5
    try:
        intensity_value = float(intensity)
    except (TypeError, ValueError):
        intensity_value = 0.5
    intensity_value = max(0.0, min(1.0, intensity_value))
    return PreferenceSummary(keywords=keywords, intensity=intensity_value, raw_text=user_text)


def _build_detected_perfumes(
    candidates: list[tuple[Any, float, str]],
) -> list[DetectedPerfume]:
    detected: list[DetectedPerfume] = []
    seen: set[str] = set()
    for perfume, score, matched_text in candidates:
        perfume_id = perfume.perfume_id
        if perfume_id in seen:
            continue
        seen.add(perfume_id)
        detected.append(
            DetectedPerfume(
                perfume_id=perfume_id,
                perfume_name=perfume.perfume_name,
                perfume_brand=perfume.perfume_brand,
                match_score=score,
                matched_text=matched_text,
            )
        )
    return detected


def _filter_detected_perfumes(
    detected_perfumes: list[DetectedPerfume],
    repository: PerfumeRepository,
) -> list[DetectedPerfume]:
    if len(detected_perfumes) < 2:
        return detected_perfumes
    filtered: list[DetectedPerfume] = []
    cache: dict[str, Any] = {}
    for item in detected_perfumes:
        if item.perfume_id not in cache:
            try:
                cache[item.perfume_id] = repository.get_perfume(item.perfume_id)
            except KeyError:
                continue
        candidate_vector = cache[item.perfume_id]
        duplicate = False
        for kept in filtered:
            if kept.perfume_id not in cache:
                try:
                    cache[kept.perfume_id] = repository.get_perfume(kept.perfume_id)
                except KeyError:
                    continue
            base_vector = cache[kept.perfume_id]
            if _should_exclude_candidate(base_vector, candidate_vector):
                duplicate = True
                break
            if _should_exclude_candidate(candidate_vector, base_vector):
                duplicate = True
                break
        if not duplicate:
            filtered.append(item)
    return filtered


def is_info_request(user_text: str) -> bool:
    normalized = user_text.lower()
    if _is_layering_intent(normalized):
        return False
    keywords = [
        "정보",
        "알려",
        "노트",
        "어코드",
        "향조",
        "구성",
        "details",
        "note",
        "accord",
    ]
    return any(token in normalized for token in keywords)


def _is_layering_intent(normalized_text: str) -> bool:
    layering_terms = [
        "레이어링",
        "궁합",
        "조합",
        "섞",
        "layering",
        "mix",
        "pair",
    ]
    return any(term in normalized_text for term in layering_terms)


def is_application_request(user_text: str) -> bool:
    normalized = user_text.lower()
    if "어디에나" in normalized:
        return False
    action_terms = ["뿌려", "분사", "바르", "바르는", "레이어링할 때"]
    location_terms = ["어디", "부위", "피부", "손목", "목", "귀 뒤"]
    return any(term in normalized for term in action_terms) and any(
        term in normalized for term in location_terms
    )


def _is_context_pairing_request(user_text: str) -> bool:
    normalized = user_text.lower()
    triggers = [
        "방금",
        "아까",
        "이전",
        "지난",
        "추천한",
        "추천해준",
        "추천받은",
        "그 향수",
        "저 향수",
    ]
    pairing_terms = ["레이어링", "섞", "같이", "조합", "어때", "가능"]
    return any(token in normalized for token in triggers) and any(
        token in normalized for token in pairing_terms
    )


def is_similarity_request(user_text: str) -> bool:
    normalized = user_text.lower()
    if "레이어링" in normalized:
        return False
    triggers = ["비슷", "같은 느낌", "대체", "유사", "similar", "same vibe", "같은 향"]
    return any(token in normalized for token in triggers)


def is_worst_match_request(user_text: str) -> bool:
    normalized = user_text.lower()
    triggers = [
        "최악",
        "최저",
        "worst",
        "안 어울",
        "안어울",
        "안맞",
        "별로",
        "낮은 점수",
    ]
    pairing_terms = ["궁합", "레이어링", "조합", "같이", "섞", "pair"]
    return any(token in normalized for token in triggers) and any(
        term in normalized for term in pairing_terms
    )


def is_brand_layering_request(user_text: str) -> bool:
    normalized = user_text.lower()
    if "향수" not in normalized and "브랜드" not in normalized:
        return False
    if "어디에나" in normalized:
        return True
    if "레이어링" in normalized and "좋" in normalized:
        return True
    return False


def analyze_user_query(
    user_text: str,
    repository: PerfumeRepository,
    preferences: PreferenceSummary | None = None,
    context_recommended_perfume_id: str | None = None,
) -> UserQueryAnalysis:
    if not user_text or not user_text.strip():
        return UserQueryAnalysis(raw_text=user_text or "", detected_perfumes=[])

    if preferences is None:
        preferences = _heuristic_preferences(user_text)

    if is_info_request(user_text):
        info_candidates = _collect_perfume_candidates(user_text, repository, limit=3)
        detected = _build_detected_perfumes(info_candidates)
        if detected:
            info = get_perfume_info(detected[0].perfume_id)
            return UserQueryAnalysis(
                raw_text=user_text,
                detected_perfumes=detected,
                recommended_perfume_info=info,
            )
        if context_recommended_perfume_id:
            info = get_perfume_info(context_recommended_perfume_id)
            return UserQueryAnalysis(
                raw_text=user_text,
                detected_perfumes=[],
                recommended_perfume_info=info,
            )
        return UserQueryAnalysis(raw_text=user_text, detected_perfumes=[])

    candidates = _collect_perfume_candidates(user_text, repository, limit=6)
    detected_perfumes = _build_detected_perfumes(candidates)
    detected_perfumes = _prioritize_base_hint(user_text, repository, detected_perfumes)
    detected_perfumes = _filter_detected_perfumes(detected_perfumes, repository)
    input_name_keys = build_input_name_keys(user_text, detected_perfumes)

    if is_similarity_request(user_text):
        if detected_perfumes:
            base_candidate = detected_perfumes[0]
            similar = rank_similar_perfumes(base_candidate.perfume_id, repository)
            return UserQueryAnalysis(
                raw_text=user_text,
                detected_perfumes=detected_perfumes,
                similar_perfumes=similar,
            )
        if context_recommended_perfume_id:
            similar = rank_similar_perfumes(context_recommended_perfume_id, repository)
            return UserQueryAnalysis(
                raw_text=user_text,
                detected_perfumes=[],
                similar_perfumes=similar,
            )
        return UserQueryAnalysis(raw_text=user_text, detected_perfumes=[])

    if is_worst_match_request(user_text):
        if detected_perfumes:
            base_candidate = detected_perfumes[0]
            worst = rank_worst_match(base_candidate.perfume_id, repository)
            if worst:
                candidate_id = worst.perfume_id
                return UserQueryAnalysis(
                    raw_text=user_text,
                    detected_perfumes=detected_perfumes,
                    detected_pair=DetectedPair(
                        base_perfume_id=base_candidate.perfume_id,
                        candidate_perfume_id=candidate_id,
                    ),
                    pairing_analysis=PairingAnalysis(
                        base_perfume_id=base_candidate.perfume_id,
                        candidate_perfume_id=candidate_id,
                        result=worst,
                    ),
                )
        if context_recommended_perfume_id:
            worst = rank_worst_match(context_recommended_perfume_id, repository)
            if worst:
                return UserQueryAnalysis(
                    raw_text=user_text,
                    detected_perfumes=[],
                    detected_pair=DetectedPair(
                        base_perfume_id=context_recommended_perfume_id,
                        candidate_perfume_id=worst.perfume_id,
                    ),
                    pairing_analysis=PairingAnalysis(
                        base_perfume_id=context_recommended_perfume_id,
                        candidate_perfume_id=worst.perfume_id,
                        result=worst,
                    ),
                )
        return UserQueryAnalysis(raw_text=user_text, detected_perfumes=detected_perfumes)

    detected_pair = None
    pairing_analysis = None
    context_pairing_request = _is_context_pairing_request(user_text)
    if context_recommended_perfume_id and context_pairing_request and detected_perfumes:
        base_candidate = detected_perfumes[0]
        candidate_id = context_recommended_perfume_id
        if base_candidate.perfume_id != candidate_id:
            try:
                base_vector = repository.get_perfume(base_candidate.perfume_id)
                candidate_vector = repository.get_perfume(candidate_id)
            except KeyError:
                base_vector = None
                candidate_vector = None
            if base_vector and candidate_vector:
                if not _should_exclude_candidate(base_vector, candidate_vector):
                    detected_pair = DetectedPair(
                        base_perfume_id=base_candidate.perfume_id,
                        candidate_perfume_id=candidate_id,
                    )
                    pairing_result = evaluate_pair(
                        base_candidate.perfume_id,
                        candidate_id,
                        preferences.keywords,
                        repository,
                    )
                    pairing_analysis = PairingAnalysis(
                        base_perfume_id=base_candidate.perfume_id,
                        candidate_perfume_id=candidate_id,
                        result=pairing_result,
                    )
    elif len(detected_perfumes) >= 2:
        base_candidate = detected_perfumes[0]
        candidate = detected_perfumes[1]
        try:
            base_vector = repository.get_perfume(base_candidate.perfume_id)
            candidate_vector = repository.get_perfume(candidate.perfume_id)
        except KeyError:
            base_vector = None
            candidate_vector = None
        if base_vector and candidate_vector:
            if not _should_exclude_candidate(base_vector, candidate_vector):
                detected_pair = DetectedPair(
                    base_perfume_id=base_candidate.perfume_id,
                    candidate_perfume_id=candidate.perfume_id,
                )
                pairing_result = evaluate_pair(
                    base_candidate.perfume_id,
                    candidate.perfume_id,
                    preferences.keywords,
                    repository,
                )
                pairing_analysis = PairingAnalysis(
                    base_perfume_id=base_candidate.perfume_id,
                    candidate_perfume_id=candidate.perfume_id,
                    result=pairing_result,
                )
    if pairing_analysis and input_name_keys:
        try:
            candidate_vector = repository.get_perfume(pairing_analysis.candidate_perfume_id)
        except KeyError:
            candidate_vector = None
        if candidate_vector and _matches_input_name(candidate_vector, input_name_keys):
            pairing_analysis = None
            detected_pair = None

    if not detected_perfumes and is_brand_layering_request(user_text):
        brand_candidates = repository.find_brand_candidates(user_text)
        if brand_candidates:
            brand_name = brand_candidates[0]
            brand_perfumes = repository.get_brand_perfumes(brand_name)
            best_perfume, avg_score, _, reason = rank_brand_universal_perfume(
                brand_perfumes,
                repository,
            )
            if best_perfume is not None:
                return UserQueryAnalysis(
                    raw_text=user_text,
                    detected_perfumes=[],
                    brand_name=brand_name,
                    brand_best_perfume=PerfumeBasic(
                        perfume_id=best_perfume.perfume_id,
                        perfume_name=best_perfume.perfume_name,
                        perfume_brand=best_perfume.perfume_brand,
                        image_url=best_perfume.image_url,
                        concentration=best_perfume.concentration,
                    ),
                    brand_best_score=round(avg_score, 3),
                    brand_best_reason=reason,
                )

    return UserQueryAnalysis(
        raw_text=user_text,
        detected_perfumes=detected_perfumes,
        detected_pair=detected_pair,
        pairing_analysis=pairing_analysis,
    )


def suggest_perfume_options(
    user_text: str,
    repository: PerfumeRepository,
    limit: int = 5,
) -> list[str]:
    if not user_text or not user_text.strip():
        return []
    candidates = _collect_perfume_candidates(user_text, repository, limit=limit)
    detected = _build_detected_perfumes(candidates)
    return [f"{item.perfume_name} ({item.perfume_brand})" for item in detected]


def preview_layering_paths(
    base_perfume_id: str,   
    user_text: str,
    repository: PerfumeRepository,
) -> dict[str, Any]:
    """Analyze user input then fetch recommendations for graph previews."""

    preferences = analyze_user_input(user_text)
    keywords = preferences.keywords
    if preferences.intensity >= 0.85:
        keywords = keywords + keywords
    input_name_keys = build_input_name_keys(user_text, None)
    recommendations, _ = rank_recommendations(
        base_perfume_id,
        keywords,
        repository,
        input_name_keys=input_name_keys,
    )
    return {
        "preferences": preferences.model_dump(),
        "recommendations": recommendations,
    }
