from pydantic import BaseModel, Field
from typing import List, Optional

# MBTI 축별 분석
class MBTIComponent(BaseModel):
    axis: str = Field(..., description="축 이름 (예: 존재방식 E/I)")
    code: str = Field(..., description="선택된 코드 (E, I, N, S 등)")
    desc: str = Field(..., description="향 관련 설명")

# 향기 어코드 상세
class AccordDetail(BaseModel):
    name: str = Field(..., description="어코드 이름")
    reason: str = Field(..., description="선정/상극 이유")
    notes: Optional[List[str]] = Field(None, description="주요 재료")

# 대표 향수 정보
class RepresentativePerfume(BaseModel):
    id: int
    name: str
    brand: str
    image: Optional[str] = None

# 향기 분석 카드 (메인)
class ScentCardBase(BaseModel):
    mbti: str = Field(..., description="MBTI 타입")
    persona_title: str = Field(..., description="페르소나 타이틀 (예: 새벽 안개 속의 숲)")
    image_url: str = Field(..., description="선택된 테마 이미지 URL")
    keywords: List[str] = Field(..., description="감성 키워드 리스트")
    components: List[MBTIComponent] = Field(..., description="4가지 축 분석")
    recommends: List[AccordDetail] = Field(..., description="추천 어코드")
    avoids: List[AccordDetail] = Field(..., description="상극 어코드")
    story: str = Field(..., description="감성 스토리")
    summary: str = Field(..., description="마무리 요약")
    recommended_perfume: Optional[RepresentativePerfume] = Field(None, description="대표 향수 정보")
    suggested_accords: Optional[List[str]] = Field(None, description="다음 탐색 제안 어코드")
    scent_type: Optional[dict] = Field(None, description="상세 분석 데이터")
    created_at: Optional[str] = Field(None, description="생성 일시")

# 향기 분석 카드 생성 스키마
class ScentCardCreate(ScentCardBase):
    pass

# 향기 분석 카드 저장용 스키마
class ScentCard(ScentCardBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True

# [추가] NMap 요약(payload) 기반 카드 생성 요청/응답 스키마
class GenerateFromSummaryRequest(BaseModel):
    top_notes: List[str]
    middle_notes: List[str]
    base_notes: List[str]
    mood_keywords: Optional[List[str]] = None
    analysis_text: Optional[str] = None
    representative_color: Optional[str] = None
    member_id: Optional[int] = None
    mbti: Optional[str] = None

class GenerateFromSummaryResponse(BaseModel):
    card: ScentCard
    session_id: str
    card_id: Optional[str] = None
    generation_method: str
