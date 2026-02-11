"""
향수 검색 API 라우터 (Re-created, 한글 검색 지원 Ver)
"""

import importlib
import os
from typing import Any,Optional,List

from pydantic import BaseModel
# [수정: 2026-01-28] DB 커넥션 풀 사용을 위한 임포트 추가
# database.py에서 정의한 풀(Pool) 관리 함수를 가져옵니다.
from agent.database import get_db_connection, release_db_connection

psycopg2: Any = importlib.import_module("psycopg2")
RealDictCursor: Any = importlib.import_module("psycopg2.extras").RealDictCursor
_fastapi: Any = importlib.import_module("fastapi")
APIRouter: Any = _fastapi.APIRouter
HTTPException: Any = _fastapi.HTTPException
Query: Any = _fastapi.Query

router = APIRouter(prefix="/perfumes", tags=["Perfumes"])

# ============================================================
# DB 연결
# ============================================================

def _get_env(key: str, default: str) -> str:
    return os.environ.get(key, default)

PERFUME_DB_PARAMS = {
    "dbname": "perfume_db",
    "user": _get_env("DB_USER", "scentence"),
    "password": _get_env("DB_PASSWORD", "scentence"),
    # Docker 내부 통신용: host.docker.internal 또는 서비스명 사용
    "host": _get_env("DB_HOST", "host.docker.internal"),
    "port": _get_env("DB_PORT", "5432"),
}

# def get_perfume_db():
#     try:
#         conn = psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)
#         return conn
#     except Exception as e:
#         print(f"❌ DB Connection Error: {e}")
#         raise e

def get_perfume_db():
    conn = psycopg2.connect(**PERFUME_DB_PARAMS, cursor_factory=RealDictCursor)
    return conn


# ============================================================
# 모델 & 유틸리티 (검색 편의 기능)
# ============================================================

class PerfumeSearchResult(BaseModel):
    perfume_id: int
    name: str
    name_kr: Optional[str] = None
    brand: str
    brand_kr: Optional[str] = None
    image_url: Optional[str] = None

class RatioItem(BaseModel):
    """Ratio 항목 (어코드/계절/상황)"""
    name: str
    ratio: int  # 0~100 정수 (정규화됨)


class PerfumeNotes(BaseModel):
    """향수 노트 (Top/Middle/Base)"""
    top: list[str]
    middle: list[str]
    base: list[str]


class PerfumeDetailResponse(BaseModel):
    """향수 상세 정보 응답"""
    perfume_id: int
    name: str
    brand: str
    image_url: str | None = None
    release_year: int | None = None
    concentration: str | None = None
    perfumer: str | None = None
    notes: PerfumeNotes
    accords: list[RatioItem]
    seasons: list[RatioItem]
    occasions: list[RatioItem]

def normalize_query(q: str):
    """
    검색어 정규화:
    1. 공백 제거 (Space-Insensitive)
    2. 소문자 변환
    3. 특수문자 일부 처리 (옵션)
    """
    return q.replace(" ", "").lower()
def get_search_variants(q: str) -> List[str]:
    """
    검색어 확장 (동의어 처리):
    - 5 -> five, no.5, v
    - no.5 -> 5
    - jomalone -> jo malone (띄어쓰기는 SQL REPLACE로 해결되지만, 특정 키워드는 추가)
    """
    variants = {q} # 기본 검색어 포함
    q_norm = normalize_query(q)
    
    # 1. 공백 제거 버전 추가
    variants.add(q_norm)
    # 2. 동의어 매핑 (Synonyms) - 필요시 확장
    synonyms = {
        "5": ["five", "no.5", "number5", "v"],
        "five": ["5", "no.5"],
        "no.5": ["5", "five"],
        "coco": ["koko"],
        "chanel": ["channel"], # 오타 보정
        "ck": ["calvin klein", "calvinklein"],
        "calvin klein": ["ck"],
        "calvinklein": ["ck"],
        "ysl": ["yves saint laurent", "saint laurent"],
        "yves saint laurent": ["ysl"],
    }
    # 정확히 일치하거나 포함된 경우 변형 추가
    for key, vals in synonyms.items():
        if key in q_norm:
            for v in vals:
                variants.add(v)
    
    return list(variants)

# ============================================================
# API & 검색 편의기능
# ============================================================

def normalize_ratio(ratio: float | None) -> int:
    if ratio is None:
        return 0
    if ratio <= 1.0:
        value = ratio * 100
    else:
        value = ratio
    return int(max(0, min(value, 100)))

@router.get("/search", response_model=list[PerfumeSearchResult])
def search_perfumes(q: str = Query(..., min_length=1, description="검색어")):
    search_term = f"%{q}%"

    # 1. 검색어 변형 생성 (띄어쓰기 무시, 동의어 등)
    # SQL에서 REPLACE(col, ' ', '')로 비교하므로, 입력값도 공백을 제거해서 비교하는 것이 가장 정확함.
    # 하지만 '5' -> 'Five' 같은 변형은 별도로 OR 조건이 필요함.
    
    # 공백 제거 검색어 생성
    # "캘빈 클라인" -> "캘빈클라인"으로 만들어서 DB에서도 공백을 제거한 값과 비교
    search_term_clean = q.replace(" ", "").lower()
    
    # SQL 파라미터 생성: 공백 제거된 검색어에 % 앞뒤로 붙임
    term = f"%{search_term_clean}%" 
    
    conditions = []
    params = []

    # 검색 조건: DB 컬럼의 공백을 제거(REPLACE)하고, 검색어(term)와 비교(ILIKE)
    # 이렇게 하면 "Calvin Klein" (DB) vs "calvinklein" (검색어) 매칭 성공
    conditions.append("""
        (REPLACE(b.perfume_name, ' ', '') ILIKE %s 
            OR REPLACE(b.perfume_brand, ' ', '') ILIKE %s
            OR REPLACE(COALESCE(k.name_kr, ''), ' ', '') ILIKE %s
            OR REPLACE(COALESCE(k.brand_kr, ''), ' ', '') ILIKE %s)
    """)
    params.extend([term, term, term, term])
    
    query_where = " OR ".join(conditions)

    try:
        # [수정: 2026-01-28] Connection Pool 적용
        # AS-IS: conn = get_perfume_db() (매번 생성)
        # TO-BE: conn = get_db_connection() (풀에서 대여)
        conn = get_db_connection()
        
        # [주의] with conn: 블록은 트랜잭션(commit/rollback)만 관리하고
        # close()는 해주지 않습니다. 그래서 try...finally가 필수입니다.
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT
                        b.perfume_id,
                        b.perfume_name,
                        b.perfume_brand,
                        b.img_link,
                        k.name_kr,
                        k.brand_kr
                    FROM tb_perfume_basic_m b
                    LEFT JOIN tb_perfume_name_kr k ON b.perfume_id = k.perfume_id
                    WHERE
                        b.perfume_name ILIKE %s
                        OR b.perfume_brand ILIKE %s
                        OR k.name_kr ILIKE %s
                        OR k.brand_kr ILIKE %s
                    LIMIT 20
                """, (search_term, search_term, search_term, search_term))
                results = cur.fetchall()
        
        # 여기 있던 conn.close()는 위험해서 제거했습니다. (에러나면 실행 안 됨)
        return [
            PerfumeSearchResult(
                perfume_id=r["perfume_id"],
                name=r["perfume_name"],
                name_kr=r["name_kr"],
                brand=r["perfume_brand"],
                brand_kr=r["brand_kr"],
                image_url=r["img_link"],
            )
            for r in results
        ]
        
    except Exception as e:
        print(f"Error searching perfumes: {e}")
        return []
    finally:
        # [중요] 어떤 에러가 나도 DB 연결은 반드시 반납해야 합니다.
        # 반납하지 않으면 AWS RDS의 연결 제한(Max Connections)이 꽉 차서 서버가 멈춥니다.
        if 'conn' in locals() and conn:
            release_db_connection(conn)

# 자동완성 기능 추가
# ============================================================
# [NEW] Autocomplete API
# ============================================================

@router.get("/autocomplete")
def autocomplete_perfumes(q: str = Query(..., min_length=1, description="검색어")):
    """
    검색어 자동완성 (브랜드 & 향수 이름 추천)
    Example:
    {
        "brands": ["Chanel", "Chloé"],
        "keywords": ["Chance", "Chanel No.5"]
    }
    """
    search_term = f"%{q}%"
    response = {"brands": [], "keywords": []}

    # 검색어 전처리 (공백 제거) - 자동완성은 빠른 반응을 위해 복잡한 동의어보다는 공백 무시 정도만 적용
    q_clean = normalize_query(q) 
    search_term = f"%{q_clean}%"


    try:
        # [수정] 자동완성 기능에도 Connection Pool 및 Safe Release 적용
        conn = get_db_connection()
        
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                 # 1. 브랜드 검색 (Space-Insensitive)
                cur.execute("""
                    SELECT DISTINCT COALESCE(k.brand_kr, b.perfume_brand) as brand
                    FROM tb_perfume_basic_m b
                    LEFT JOIN tb_perfume_name_kr k ON b.perfume_id = k.perfume_id
                    WHERE 
                        REPLACE(b.perfume_brand, ' ', '') ILIKE %s 
                        OR REPLACE(COALESCE(k.brand_kr, ''), ' ', '') ILIKE %s
                    LIMIT 5
                """, (search_term, search_term))
                response["brands"] = [r['brand'] for r in cur.fetchall()]
                # 2. 향수 이름 검색 (Space-Insensitive)
                cur.execute("""
                    SELECT DISTINCT COALESCE(k.name_kr, b.perfume_name) as name
                    FROM tb_perfume_basic_m b
                    LEFT JOIN tb_perfume_name_kr k ON b.perfume_id = k.perfume_id
                    WHERE 
                        REPLACE(b.perfume_name, ' ', '') ILIKE %s 
                        OR REPLACE(COALESCE(k.name_kr, ''), ' ', '') ILIKE %s
                    LIMIT 5
                """, (search_term, search_term))
                response["keywords"] = [r['name'] for r in cur.fetchall()]


        # conn.close() -> 제거 (finally에서 반납)
        return response

    except Exception as e:
        print(f"Error autocompleting: {e}")
        return {"brands": [], "keywords": []}
    finally:
        # [중요] 반드시 연결 반납 (자원 누수 방지)
        if 'conn' in locals() and conn:
            release_db_connection(conn)

@router.get("/detail", response_model=PerfumeDetailResponse)
def get_perfume_detail(
    perfume_id: int = Query(..., description="향수 ID"),
):
    try:
        conn = get_perfume_db()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT perfume_id, perfume_name, perfume_brand, release_year,
                           concentration, perfumer, img_link
                    FROM tb_perfume_basic_m
                    WHERE perfume_id = %s;
                    """,
                    (perfume_id,),
                )
                basic = cur.fetchone()
                if not basic:
                    raise HTTPException(status_code=404, detail="Perfume not found")

                cur.execute(
                    """
                    SELECT note, type
                    FROM tb_perfume_notes_m
                    WHERE perfume_id = %s;
                    """,
                    (perfume_id,),
                )
                note_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT accord, ratio
                    FROM tb_perfume_accord_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                accord_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT season, ratio
                    FROM tb_perfume_season_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                season_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT occasion, ratio
                    FROM tb_perfume_oca_r
                    WHERE perfume_id = %s
                    ORDER BY ratio DESC NULLS LAST
                    LIMIT 5;
                    """,
                    (perfume_id,),
                )
                occasion_rows = cur.fetchall()

        conn.close()

        notes_map = {"TOP": [], "MIDDLE": [], "BASE": []}
        for row in note_rows:
            note = (row.get("note") or "").strip()
            note_type = (row.get("type") or "").strip().upper()
            if not note or note_type not in notes_map:
                continue
            if note not in notes_map[note_type]:
                notes_map[note_type].append(note)

        notes = PerfumeNotes(
            top=notes_map["TOP"],
            middle=notes_map["MIDDLE"],
            base=notes_map["BASE"],
        )

        accords = [
            RatioItem(name=row["accord"], ratio=normalize_ratio(row.get("ratio")))
            for row in accord_rows
        ]
        seasons = [
            RatioItem(name=row["season"], ratio=normalize_ratio(row.get("ratio")))
            for row in season_rows
        ]
        occasions = [
            RatioItem(name=row["occasion"], ratio=normalize_ratio(row.get("ratio")))
            for row in occasion_rows
        ]

        return PerfumeDetailResponse(
            perfume_id=basic["perfume_id"],
            name=basic["perfume_name"],
            brand=basic["perfume_brand"],
            image_url=basic["img_link"],
            release_year=basic.get("release_year"),
            concentration=basic.get("concentration"),
            perfumer=basic.get("perfumer"),
            notes=notes,
            accords=accords,
            seasons=seasons,
            occasions=occasions,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching perfume detail: {e}")
        raise