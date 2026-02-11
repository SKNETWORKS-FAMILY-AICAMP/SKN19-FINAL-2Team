from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class SessionStartRequest(BaseModel):
    """세션 시작 요청"""
    member_id: Optional[int] = None
    mbti: Optional[str] = None


class SessionStartResponse(BaseModel):
    """세션 시작 응답"""
    session_id: str


class ActivityLogRequest(BaseModel):
    """활동 로그 요청"""
    accord_selected: Optional[str] = None
    filter_changed: Optional[str] = None
    selected_accords: Optional[List[str]] = None  # 현재 선택된 모든 어코드
    perfume_id: Optional[int] = None  # 클릭한 향수 ID
    dwell_time: Optional[int] = None
    interaction_count: Optional[int] = None


class UpdateContextRequest(BaseModel):
    """분석 컨텍스트 업데이트 요청"""
    member_id: Optional[int] = None
    mbti: Optional[str] = None
    selected_accords: List[str] = []
    filters: dict = {}
    visible_perfume_ids: List[int] = []


class ActivityLogResponse(BaseModel):
    """활동 로그 응답"""
    logged: bool
    card_trigger_ready: bool
    trigger_message: Optional[str] = None
    daily_limit_reached: Optional[bool] = None
    daily_limit_remaining: Optional[int] = None


class AccordInfo(BaseModel):
    """어코드 정보"""
    name: str
    description: str


class ScentCard(BaseModel):
    """향기카드 (템플릿 버전)"""
    title: str
    story: str
    accords: List[AccordInfo]
    created_at: str


class GenerateCardResponse(BaseModel):
    """카드 생성 응답"""
    card: dict  # dict로 변경하여 유연한 구조 허용
    session_id: str
    card_id: str
    generation_method: str  # 'template' or 'llm_light' or 'llm_full'
    generation_time_ms: Optional[int] = None  # 생성 소요 시간 (밀리초)


class SaveCardRequest(BaseModel):
    """카드 저장 요청"""
    card_id: str  # UUID


class SaveCardResponse(BaseModel):
    """카드 저장 응답"""
    success: bool
    message: str
    card_id: str
    new_session_id: str  # 카드 저장 후 발급된 새 세션 ID


class MyCardsResponse(BaseModel):
    """내 카드 조회 응답"""
    cards: List[dict]
    total_count: int
