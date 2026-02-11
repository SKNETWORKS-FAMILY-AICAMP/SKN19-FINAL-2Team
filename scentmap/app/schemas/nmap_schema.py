from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

"""
NMapSchema: 향수 맵(NMap) 시각화 및 분석 데이터 스키마
"""

class NMapNode(BaseModel):
    """향수 맵 노드 정보"""
    id: str
    type: str  # "perfume" | "accord"
    label: str
    brand: Optional[str] = None
    image: Optional[str] = None
    primary_accord: Optional[str] = None
    accords: Optional[List[str]] = None
    seasons: Optional[List[str]] = None
    occasions: Optional[List[str]] = None
    genders: Optional[List[str]] = None
    register_status: Optional[str] = None

class NMapEdge(BaseModel):
    """향수 맵 엣지 정보"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    type: str  # "HAS_ACCORD" | "SIMILAR_TO"
    weight: float

class NMapAnalysisSummary(BaseModel):
    """향기 카드용 분석 요약 정보"""
    top_notes: List[str]
    middle_notes: List[str]
    base_notes: List[str]
    mood_keywords: List[str]
    representative_color: Optional[str] = None
    analysis_text: Optional[str] = None

class NMapResponse(BaseModel):
    """향수 맵 전체 응답 구조"""
    nodes: List[NMapNode]
    edges: List[NMapEdge]
    summary: NMapAnalysisSummary
    meta: Dict[str, Optional[float | int | str]]

class FilterOptionsResponse(BaseModel):
    """향수 맵 필터 옵션 응답 구조"""
    brands: List[str]
    seasons: List[str]
    occasions: List[str]
    genders: List[str]
    accords: List[str]
