from typing import Dict
from datetime import datetime
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

# 라벨 메모리 캐시 (서버 시작 시 로드, 수동 갱신)
_labels_cache: Dict | None = None
_labels_loaded_at: datetime | None = None

# 한글 매핑 상수 (DB에 없을 경우 폴백용)
ACCORD_MAPPING = {
    "Animal": "애니멀",
    "Aquatic": "아쿠아틱",
    "Chypre": "시프레",
    "Citrus": "시트러스",
    "Creamy": "크리미",
    "Earthy": "얼씨",
    "Floral": "플로럴",
    "Fougère": "푸제르",
    "Fruity": "프루티",
    "Gourmand": "구르망",
    "Green": "그린",
    "Leathery": "레더리",
    "Oriental": "오리엔탈",
    "Powdery": "파우더리",
    "Resinous": "수지향",
    "Smoky": "스모키",
    "Spicy": "스파이시",
    "Sweet": "스위트",
    "Synthetic": "인공향",
    "Woody": "우디",
    "Fresh": "프레시",
}

SEASON_MAPPING = {
    "Spring": "봄",
    "Summer": "여름",
    "Fall": "가을",
    "Winter": "겨울",
}

OCCASION_MAPPING = {
    "Business": "업무/비즈니스",
    "Daily": "데일리",
    "Evening": "저녁 모임",
    "Leisure": "여가/휴식",
    "Night Out": "밤 외출",
    "Sport": "운동",
}

GENDER_MAPPING = {
    "Feminine": "여성",
    "Masculine": "남성",
    "Unisex": "남녀 공용",
}


def _load_labels_from_db() -> Dict:
    """DB에서 모든 라벨 데이터를 한 번에 조회 (최적화)"""
    logger.info("🔄 DB에서 라벨 데이터 일괄 조회 시작...")
    
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. 향수명 + 브랜드 한글 매핑 (한 번의 조인으로 처리)
            cur.execute("""
                SELECT 
                    k.perfume_id, 
                    k.name_kr,
                    b.perfume_brand,
                    k.brand_kr
                FROM tb_perfume_name_kr k
                LEFT JOIN TB_PERFUME_BASIC_M b ON k.perfume_id = b.perfume_id
                WHERE k.name_kr IS NOT NULL OR k.brand_kr IS NOT NULL
            """)
            perfume_brand_rows = cur.fetchall()
            
            # 2. 어코드 목록
            cur.execute("""
                SELECT DISTINCT accord
                FROM TB_PERFUME_ACCORD_M
                WHERE accord IS NOT NULL
            """)
            accord_rows = cur.fetchall()
            
            # 3. 계절 목록
            cur.execute("""
                SELECT DISTINCT season
                FROM TB_PERFUME_SEASON_R
                WHERE season IS NOT NULL
            """)
            season_rows = cur.fetchall()
            
            # 4. 상황 목록
            cur.execute("""
                SELECT DISTINCT occasion
                FROM TB_PERFUME_OCA_R
                WHERE occasion IS NOT NULL
            """)
            occasion_rows = cur.fetchall()
            
            # 5. 성별 목록
            cur.execute("""
                SELECT DISTINCT gender
                FROM TB_PERFUME_GENDER_R
                WHERE gender IS NOT NULL
            """)
            gender_rows = cur.fetchall()
    
    # 향수명 및 브랜드 매핑 처리
    perfume_labels = {}
    brand_labels = {}
    
    for row in perfume_brand_rows:
        if row["name_kr"]:
            perfume_labels[str(row["perfume_id"])] = row["name_kr"]
        
        if row["perfume_brand"] and row["brand_kr"]:
            brand_labels[row["perfume_brand"]] = row["brand_kr"]
    
    # 어코드/계절/상황/성별 매핑 처리
    accords = {row["accord"]: ACCORD_MAPPING.get(row["accord"], row["accord"]) 
               for row in accord_rows}
    
    seasons = {row["season"]: SEASON_MAPPING.get(row["season"], row["season"]) 
               for row in season_rows}
    
    occasions = {row["occasion"]: OCCASION_MAPPING.get(row["occasion"], row["occasion"]) 
                 for row in occasion_rows}
    
    genders = {row["gender"]: GENDER_MAPPING.get(row["gender"], row["gender"]) 
               for row in gender_rows}
    
    labels = {
        "perfume_names": perfume_labels,
        "brands": brand_labels,
        "accords": accords,
        "seasons": seasons,
        "occasions": occasions,
        "genders": genders,
    }
    
    logger.info(
        f"✅ 라벨 데이터 로드 완료 - "
        f"향수: {len(perfume_labels)}, 브랜드: {len(brand_labels)}, "
        f"어코드: {len(accords)}, 계절: {len(seasons)}, "
        f"상황: {len(occasions)}, 성별: {len(genders)}"
    )
    
    return labels


def load_labels() -> Dict:
    """라벨 데이터를 DB에서 로드하고 캐시에 저장"""
    global _labels_cache, _labels_loaded_at
    
    _labels_cache = _load_labels_from_db()
    _labels_loaded_at = datetime.now()
    
    return _labels_cache.copy()


def get_labels() -> Dict:
    """캐시된 라벨 데이터 반환 (없으면 자동 로드)"""
    global _labels_cache, _labels_loaded_at
    
    if _labels_cache is None:
        logger.warning("⚠️ 라벨 캐시가 비어있어 자동 로드합니다.")
        return load_labels()
    
    logger.debug(f"✅ 라벨 캐시 사용 (로드 시간: {_labels_loaded_at.strftime('%Y-%m-%d %H:%M:%S')})")
    return _labels_cache.copy()


def get_labels_metadata() -> Dict:
    """라벨 캐시 메타데이터 반환"""
    global _labels_cache, _labels_loaded_at
    
    if _labels_cache is None:
        return {
            "loaded": False,
            "loaded_at": None,
            "counts": {}
        }
    
    return {
        "loaded": True,
        "loaded_at": _labels_loaded_at.isoformat() if _labels_loaded_at else None,
        "counts": {
            "perfume_names": len(_labels_cache.get("perfume_names", {})),
            "brands": len(_labels_cache.get("brands", {})),
            "accords": len(_labels_cache.get("accords", {})),
            "seasons": len(_labels_cache.get("seasons", {})),
            "occasions": len(_labels_cache.get("occasions", {})),
            "genders": len(_labels_cache.get("genders", {})),
        }
    }
