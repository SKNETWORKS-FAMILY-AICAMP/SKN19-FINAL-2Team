from fastapi import APIRouter, Body, Query, HTTPException
from typing import List, Optional
from scentmap.app.schemas.ncard_schemas import (
    ScentCard,
    GenerateFromSummaryRequest,
    GenerateFromSummaryResponse,
)
from scentmap.app.services.ncard_service import ncard_service

"""
NCardRouter: 향기 분석 카드 관련 독립 API 엔드포인트
"""

router = APIRouter(prefix="/ncard", tags=["ncard"])

@router.get("/", response_model=List[ScentCard])
async def get_scent_cards(
    member_id: int = Query(..., description="회원 ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """회원의 저장된 향기 분석 카드 목록 조회"""
    result = ncard_service.get_member_cards(member_id, limit=limit, offset=offset)
    
    # DB에서 조회된 데이터를 ScentCard 모델 리스트로 변환
    cards = []
    for item in result.get("cards", []):
        card_data = item["card_data"]
        # card_id를 id 필드로 매핑
        card_data["id"] = int(item["card_id"])
        cards.append(ScentCard(**card_data))
        
    return cards

@router.post("/generate", response_model=ScentCard)
async def generate_scent_card(
    mbti: str = Body(..., embed=True), 
    selected_accords: List[str] = Body(..., embed=True)
):
    """사용자 입력 기반 즉석 향기 카드 생성 (세션 없이)"""
    # 세션 ID 없이 생성하는 경우를 위한 처리
    result = await ncard_service.generate_card(session_id="adhoc", mbti=mbti, selected_accords=selected_accords)
    
    # 생성된 카드 데이터 반환
    card_data = result['card']
    if result.get('card_id'):
        card_data["id"] = int(result['card_id'])
        
    return ScentCard(**card_data)

@router.post("/{card_id}/save")
async def save_card(card_id: int, member_id: int = Body(..., embed=True)):
    """생성된 카드를 회원 계정에 저장"""
    return ncard_service.save_member_card(str(card_id), member_id)


@router.post("/generate-from-summary", response_model=GenerateFromSummaryResponse)
async def generate_from_summary(req: GenerateFromSummaryRequest):
    """NMap 요약(payload) 기반 카드 생성 (정식 버전)"""
    try:
        result = await ncard_service.generate_card_from_summary(req)
        card = result["card"]
        if result.get("card_id"):
            card["id"] = int(result["card_id"])
        return {
            "card": card,
            "session_id": result.get("session_id"),
            "card_id": result.get("card_id"),
            "generation_method": result.get("generation_method", "nmap_summary"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
