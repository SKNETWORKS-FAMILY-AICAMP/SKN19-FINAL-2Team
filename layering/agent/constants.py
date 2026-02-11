"""Portable perfume layering constants.

These values are sourced from docs/request.md and shared across the
layering service. Accord ordering is critical because vectors rely on a
fixed index per accord.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Set, Tuple

ACCORDS: List[str] = [
    "Fresh",
    "Citrus",
    "Fruity",
    "Sweet",
    "Floral",
    "Powdery",
    "Creamy",
    "Gourmand",
    "Oriental",
    "Spicy",
    "Animal",
    "Leathery",
    "Smoky",
    "Woody",
    "Resinous",
    "Earthy",
    "Chypre",
    "Fougère",
    "Green",
    "Aquatic",
    "Synthetic",
]

ACCORD_INDEX: Dict[str, int] = {name: idx for idx, name in enumerate(ACCORDS)}

PERSISTENCE_MAP: Dict[str, int] = {
    "Leathery": 10,
    "Animal": 9,
    "Oriental": 9,
    "Resinous": 9,
    "Smoky": 9,
    "Woody": 9,
    "Earthy": 8,
    "Gourmand": 8,
    "Spicy": 7,
    "Chypre": 7,
    "Fougère": 7,
    "Powdery": 6,
    "Creamy": 6,
    "Sweet": 6,
    "Floral": 5,
    "Synthetic": 5,
    "Fruity": 4,
    "Green": 4,
    "Fresh": 3,
    "Aquatic": 3,
    "Citrus": 2,
}

CLASH_PAIRS: Tuple[Tuple[Set[str], Set[str]], ...] = (
    ({"Aquatic"}, {"Gourmand", "Sweet"}),
    ({"Animal"}, {"Green", "Fresh"}),
    ({"Synthetic"}, {"Earthy"}),
    ({"Aquatic"}, {"Oriental", "Spicy"}),
)

KEYWORD_MAP: Dict[str, Sequence[str]] = {
    "citrus": ["Citrus", "Fresh"],
    "cool": ["Aquatic", "Fresh", "Green"],
    "cold": ["Aquatic", "Fresh", "Green"],
    "fresh": ["Fresh", "Green"],
    "green": ["Green", "Fresh"],
    "green tea": ["Green", "Fresh"],
    "floral": ["Floral"],
    "warm": ["Oriental", "Spicy", "Resinous"],
    "spicy": ["Spicy"],
    "sweet": ["Gourmand", "Sweet", "Fruity"],
    "amber": ["Resinous"],
    "차가운": ["Aquatic", "Fresh", "Green"],
    "시원한": ["Aquatic", "Fresh", "Green"],
    "청량": ["Aquatic", "Fresh", "Green"],
    "쿨": ["Aquatic", "Fresh", "Green"],
    "플로럴": ["Floral"],
    "꽃향": ["Floral"],
    "꽃내음": ["Floral"],
    "스파이시": ["Spicy"],
    "알싸": ["Spicy"],
    "매콤": ["Spicy"],
    "매운": ["Spicy"],
    "톡쏘는": ["Spicy"],
    "자극적": ["Spicy"],
    "무거운": ["Woody", "Resinous", "Oriental"],
    "무겁게": ["Woody", "Resinous", "Oriental"],
    "묵직": ["Woody", "Resinous", "Oriental"],
    "딥": ["Resinous", "Oriental"],
    "deep": ["Resinous", "Oriental"],
    "heavy": ["Woody", "Resinous", "Oriental"],
}

KEYWORD_VECTOR_BOOST: float = 30.0
MATCH_SCORE_THRESHOLD: float = 0.7

PERFUME_ALIAS_MAP: Dict[str, Dict[str, str]] = {
    "운 자르뎅 수르뜨와": {"name": "Un Jardin Sur Le Toit", "brand": "Hermes"},
    "디올 소바쥬": {"name": "Sauvage", "brand": "Dior"},
    "디올 소바주": {"name": "Sauvage", "brand": "Dior"},
    "소바쥬": {"name": "Sauvage", "brand": "Dior"},
    "우드 세이지 시솔트": {"name": "Wood Sage & Sea Salt", "brand": "Jo Malone"},
    "우드 세이지 씨솔트": {"name": "Wood Sage & Sea Salt", "brand": "Jo Malone"},
    "우드 세이지 앤 씨 솔트": {"name": "Wood Sage & Sea Salt", "brand": "Jo Malone"},
    "조말론 우드 세이지 시솔트": {"name": "Wood Sage & Sea Salt", "brand": "Jo Malone"},
    "ck one": {"name": "CK One", "brand": "Calvin Klein"},
    "ck one": {"name": "CK One", "brand": "Calvin Klein"},
    "씨케이 원": {"name": "CK One", "brand": "Calvin Klein"},
    "느와르": {"name": "Noir", "brand": ""},

}

BRAND_ALIAS_MAP: Dict[str, str] = {
    "조말론": "Jo Malone",
    "조 말론": "Jo Malone",
    "디올": "Dior",
    "에르메스": "Hermes",
    "샤넬": "Chanel",

}


def accord_index(name: str) -> int:
    """Return the configured index for an accord, raising if missing."""

    return ACCORD_INDEX[name]


