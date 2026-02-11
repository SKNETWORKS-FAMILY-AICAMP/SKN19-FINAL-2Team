from fastapi import APIRouter, HTTPException, Query
from scentmap.app.schemas.session_schema import (
    SessionStartRequest, SessionStartResponse, ActivityLogRequest, ActivityLogResponse,
    UpdateContextRequest, GenerateCardResponse, SaveCardRequest, SaveCardResponse, MyCardsResponse
)
from scentmap.app.services.session_service import (
    create_session, update_session_activity, update_session_context, check_card_trigger
)
from scentmap.app.services.ncard_service import ncard_service

"""
SessionRouter: 세션 관리 및 카드 생성 관련 API 엔드포인트
"""

router = APIRouter(prefix="/session", tags=["session"])

@router.post("/start", response_model=SessionStartResponse)
def start_session(request: SessionStartRequest):
    """탐색 세션 시작 및 ID 발급"""
    try:
        session = create_session(member_id=request.member_id, mbti=request.mbti)
        return SessionStartResponse(session_id=session["session_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/activity", response_model=ActivityLogResponse)
def log_activity(session_id: str, request: ActivityLogRequest):
    """사용자 활동 기록 및 카드 생성 트리거 확인"""
    try:
        update_session_activity(
            session_id,
            accord_selected=request.accord_selected,
            selected_accords=request.selected_accords,
            perfume_id=request.perfume_id,
            dwell_time=request.dwell_time
        )
        trigger = check_card_trigger(session_id)
        return ActivityLogResponse(logged=True, card_trigger_ready=trigger["ready"], trigger_message=trigger.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/update-context")
def update_context(session_id: str, request: UpdateContextRequest):
    """분석용 세션 컨텍스트 업데이트"""
    try:
        update_session_context(session_id, request.member_id, request.mbti, request.selected_accords, request.filters, request.visible_perfume_ids)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/generate-card", response_model=GenerateCardResponse)
async def generate_card(session_id: str):
    """향기 분석 카드 생성 요청"""
    try:
        # 세션 데이터 조회 로직은 서비스 내부로 캡슐화 권장 (여기서는 직접 전달 예시)
        # 실제 구현 시 ncard_service.generate_card(session_id) 내부에서 세션 조회 수행
        result = await ncard_service.generate_card(session_id)
        return GenerateCardResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/save-card", response_model=SaveCardResponse)
def save_generated_card(session_id: str, request: SaveCardRequest, member_id: int = Query(...)):
    """생성된 카드 저장"""
    try:
        result = ncard_service.save_member_card(request.card_id, member_id)
        return SaveCardResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-cards", response_model=MyCardsResponse)
def get_member_cards(member_id: int = Query(...), limit: int = 20, offset: int = 0):
    """저장된 내 카드 목록 조회"""
    try:
        result = ncard_service.get_member_cards(member_id, limit, offset)
        return MyCardsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
