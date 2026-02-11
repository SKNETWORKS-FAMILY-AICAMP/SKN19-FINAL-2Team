from fastapi import APIRouter, HTTPException
from fastapi.responses import ORJSONResponse

from scentmap.app.services.label_service import (
    get_labels,
    load_labels,
    get_labels_metadata,
)


router = APIRouter(prefix="/labels", tags=["labels"])


@router.get("", response_class=ORJSONResponse)
def get_labels_endpoint():
    """
    한글 매핑 데이터 조회
    
    캐시된 라벨 데이터를 반환합니다. (서버 시작 시 자동 로드됨)
    - perfume_names: 향수 ID별 한글명
    - brands: 브랜드 영문명 -> 한글명 매핑
    - accords: 어코드 영문명 -> 한글명 매핑
    - seasons: 계절 영문명 -> 한글명 매핑
    - occasions: 상황 영문명 -> 한글명 매핑
    - genders: 성별 영문명 -> 한글명 매핑
    """
    try:
        labels = get_labels()
        return ORJSONResponse(content=labels)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reload", response_class=ORJSONResponse)
def reload_labels():
    """
    한글 매핑 데이터 수동 갱신
    
    DB에서 최신 라벨 데이터를 다시 로드합니다.
    - 사용 시점: DB에 새 향수/브랜드가 추가되었을 때
    - 관리자 또는 배치 스크립트에서 호출
    """
    try:
        labels = load_labels()
        metadata = get_labels_metadata()
        
        return ORJSONResponse(content={
            "message": "라벨 데이터 갱신 완료",
            "metadata": metadata,
            "sample_counts": {
                "perfume_names": len(labels.get("perfume_names", {})),
                "brands": len(labels.get("brands", {})),
                "accords": len(labels.get("accords", {})),
            }
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/metadata", response_class=ORJSONResponse)
def get_labels_metadata_endpoint():
    """
    라벨 캐시 메타데이터 조회
    
    현재 캐시된 라벨 데이터의 상태와 통계를 반환합니다.
    """
    try:
        metadata = get_labels_metadata()
        return ORJSONResponse(content=metadata)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
