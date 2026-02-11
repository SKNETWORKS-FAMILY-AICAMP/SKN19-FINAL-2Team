from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import os  # [개선] 환경 변수 지원
from scentmap.app.schemas.nmap_schema import NMapResponse, FilterOptionsResponse
from scentmap.app.services.nmap_service import get_nmap_data, get_nmap_data_cached, get_filter_options  # [개선] 캐싱 버전 추가
from slowapi import Limiter
from slowapi.util import get_remote_address

"""
NMapRouter: 향수 맵(NMap) 시각화 및 필터 옵션 관련 API 엔드포인트
[개선] 성능 최적화: 캐싱 + Rate Limiting + 스마트 로딩
[개선] EC2 배포 최적화: Rate Limiting 환경 변수 지원
"""

router = APIRouter(prefix="/nmap", tags=["nmap"])

# [개선] Rate Limiter 설정 (환경 변수로 설정 가능)
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
RATE_LIMIT_STRING = f"{RATE_LIMIT_PER_MINUTE}/minute"
limiter = Limiter(key_func=get_remote_address)

@router.get("/filter-options", response_model=FilterOptionsResponse)
def get_nmap_filters():
    """향수 맵 필터링을 위한 브랜드, 계절, 상황 등 옵션 목록 조회"""
    try:
        return get_filter_options()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/perfumes", response_model=NMapResponse)
@limiter.limit(RATE_LIMIT_STRING)  # [개선] Rate Limiting (환경 변수로 설정 가능)
async def get_nmap_perfumes(
    request: Request,  # [개선] Rate Limiting을 위해 필요
    min_similarity: float = Query(0.0, ge=0.0, le=1.0),
    top_accords: int = Query(5, ge=1, le=5),
    max_perfumes: int = Query(300, ge=50, le=500, description="최대 향수 개수 (기본 300)"),  # [개선] 기본값 300, 최대 500으로 제한
    member_id: Optional[int] = Query(None, ge=1),
    debug: bool = False,
):
    """향수 네트워크 데이터 조회 (캐싱 적용)
    [개선] 스마트 로딩 + 메모리 캐싱으로 성능 향상
    """
    try:
        return get_nmap_data_cached(  # [개선] 캐싱 버전 사용
            member_id=member_id,
            max_perfumes=max_perfumes,
            min_similarity=min_similarity,
            top_accords=top_accords,
            debug=debug
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/result", response_model=NMapResponse)
@limiter.limit(RATE_LIMIT_STRING)  # [개선] Rate Limiting (환경 변수로 설정 가능)
async def get_nmap_result(
    request: Request,  # [개선] Rate Limiting을 위해 필요
    member_id: Optional[int] = Query(None, description="회원 ID"),
    max_perfumes: int = Query(300, description="최대 향수 개수"),  # [개선] 기본값 300으로 증가
    min_similarity: float = Query(0.45, description="유사도 필터 기준"),
    top_accords: int = Query(2, description="표시할 상위 어코드 개수")
):
    """향수 맵 분석 결과 및 시각화 데이터 조회 (기존 호환용)
    [개선] 캐싱 적용 버전
    """
    try:
        return get_nmap_data_cached(  # [개선] 캐싱 버전 사용
            member_id=member_id,
            max_perfumes=max_perfumes,
            min_similarity=min_similarity,
            top_accords=top_accords
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
