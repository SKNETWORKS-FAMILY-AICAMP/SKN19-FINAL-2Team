from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class NetworkNode(BaseModel):
    """네트워크 그래프 노드(향수/어코드 공통)"""
    id: str  # 노드 식별자
    type: str  # perfume | accord
    label: str  # 시각화용 라벨
    brand: Optional[str] = None
    image: Optional[str] = None
    primary_accord: Optional[str] = None  # 대표 어코드
    accords: Optional[List[str]] = None   
    seasons: Optional[List[str]] = None  
    occasions: Optional[List[str]] = None  
    genders: Optional[List[str]] = None 
    register_status: Optional[str] = None  # 회원 향수 등록 상태


class NetworkEdge(BaseModel):
    """노드 간 관계 엣지"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    from_: str = Field(alias="from")  # 시작 노드
    to: str
    type: str  # HAS_ACCORD | SIMILAR_TO
    weight: Optional[float] = None  # 유사도/비중
    value: Optional[float] = None  # 시각화 두께
    title: Optional[str] = None  # 시각화 툴팁


class NetworkMeta(BaseModel):
    """네트워크 구성 및 생성 메타 정보"""
    perfume_count: Optional[int] = None
    accord_count: Optional[int] = None
    edge_count: Optional[int] = None

    accord_edges: Optional[int] = None
    similarity_edges: Optional[int] = None
    similarity_edges_high: Optional[int] = None

    min_similarity: Optional[float] = None  # 유사도 필터
    top_accords: Optional[int] = None  # 향수당 표시 어코드 수
    candidate_pairs: Optional[int] = None  # 유사도 후보 수
    
    built_at: Optional[str] = None  # 생성 시각
    build_seconds: Optional[float] = None  # 생성 소요 시간
    max_perfumes: Optional[int] = None  # 노드 상한
    debug_samples: Optional[Dict[str, List[Dict]]] = None  # 디버그 샘플


class NetworkResponse(BaseModel):
    """API 응답 루트 스키마"""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    meta: NetworkMeta
