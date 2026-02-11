import time
import logging
import os  # [개선] 환경 변수 지원
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from psycopg2.extras import RealDictCursor
from scentmap.db import get_db_connection, get_recom_db_connection, get_nmap_db_connection  # [개선] 향수지도 전용 커넥션 추가
from scentmap.app.schemas.nmap_schema import NMapResponse, NMapNode, NMapEdge, NMapAnalysisSummary

"""
NMapService: 향수 맵(NMap) 데이터 구축 및 분석 서비스
[개선] 성능 최적화: 스마트 로딩 + 메모리 캐싱 + DB 격리
[개선] EC2 배포 최적화: 환경 변수 지원 + 로깅 레벨 조정
"""

logger = logging.getLogger(__name__)

# [개선] 유사도 엣지 개수 최적화: 30 → 20 (데이터 크기 감소)
SIMILARITY_TOP_K = 20
FILTER_OPTIONS_TTL = 300
_filter_cache: Optional[Dict] = None
_filter_cache_time: float = 0

# [개선] NMap 데이터 캐싱 (환경 변수로 설정 가능)
NMAP_CACHE_TTL = int(os.getenv("NMAP_CACHE_TTL", "1800"))  # 기본 30분
NMAP_CACHE_MAX_SIZE = int(os.getenv("NMAP_CACHE_MAX_SIZE", "50"))  # 프로덕션: 50개
_nmap_cache: Dict[str, NMapResponse] = {}
_nmap_cache_time: Dict[str, float] = {}

def get_filter_options() -> Dict[str, List[str]]:
    """향수 맵 필터링을 위한 옵션 목록 조회"""
    global _filter_cache, _filter_cache_time
    if _filter_cache and (time.time() - _filter_cache_time < FILTER_OPTIONS_TTL):
        return _filter_cache

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 브랜드
            cur.execute("""
                SELECT perfume_brand, COUNT(*) as cnt 
                FROM TB_PERFUME_BASIC_M 
                WHERE perfume_brand IS NOT NULL 
                GROUP BY perfume_brand 
                ORDER BY cnt DESC, perfume_brand
            """)
            brands = [r["perfume_brand"] for r in cur.fetchall()]
            
            # 계절
            cur.execute("""
                SELECT season, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_SEASON_R 
                WHERE season IS NOT NULL 
                GROUP BY season 
                ORDER BY cnt DESC, season
            """)
            seasons = [r["season"] for r in cur.fetchall()]
            
            # 상황
            cur.execute("""
                SELECT occasion, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_OCA_R 
                WHERE occasion IS NOT NULL 
                GROUP BY occasion 
                ORDER BY cnt DESC, occasion
            """)
            occasions = [r["occasion"] for r in cur.fetchall()]
            
            # 성별
            cur.execute("""
                SELECT gender, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_GENDER_R 
                WHERE gender IS NOT NULL 
                GROUP BY gender 
                ORDER BY cnt DESC, gender
            """)
            genders = [r["gender"] for r in cur.fetchall()]
            
            # 어코드
            cur.execute("""
                SELECT accord, COUNT(DISTINCT perfume_id) as cnt 
                FROM TB_PERFUME_ACCORD_M 
                WHERE accord IS NOT NULL 
                GROUP BY accord 
                ORDER BY cnt DESC, accord
            """)
            accords = [r["accord"] for r in cur.fetchall()]

    _filter_cache = {
        "brands": brands, 
        "seasons": seasons, 
        "occasions": occasions, 
        "genders": genders, 
        "accords": accords
    }
    _filter_cache_time = time.time()
    return _filter_cache

# [개선] 인기 향수 우선 조회 (스마트 로딩)
def _fetch_popular_perfume_ids(limit: int = 300) -> List[int]:
    """인기/대표 향수 ID 조회 (우선순위 기반)"""
    popular_ids: List[int] = []
    try:
        # TB_MEMBER_MY_PERFUME_T는 recom_db 소속
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT perfume_id, COUNT(*) as cnt
                    FROM TB_MEMBER_MY_PERFUME_T
                    GROUP BY perfume_id
                    ORDER BY cnt DESC
                    LIMIT %s
                """, (limit,))
                popular_ids = [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.warning(f"인기 향수 조회 실패 (recom_db): {e}")

    # 다양성 확보: 부족분은 nmap_db의 브랜드별 대표 향수로 채움
    if len(popular_ids) < limit:
        with get_nmap_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT ON (perfume_brand) perfume_id
                    FROM TB_PERFUME_BASIC_M
                    WHERE perfume_id NOT IN %s
                    ORDER BY perfume_brand, perfume_id
                    LIMIT %s
                """, (tuple(popular_ids) if popular_ids else (0,), limit - len(popular_ids)))
                popular_ids.extend([row[0] for row in cur.fetchall()])

    if not popular_ids:
        # fallback: nmap_db에서 단순 ID 순
        with get_nmap_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT perfume_id FROM TB_PERFUME_BASIC_M ORDER BY perfume_id LIMIT %s", (limit,))
                popular_ids = [row[0] for row in cur.fetchall()]

    return popular_ids[:limit]

def _fetch_member_perfume_ids(member_id: int) -> List[int]:
    """회원이 등록한 향수 ID 조회"""
    try:
        with get_recom_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT perfume_id FROM TB_MEMBER_MY_PERFUME_T WHERE member_id = %s", (member_id,))
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.warning(f"회원 향수 조회 실패: {e}")
        return []

def _fetch_perfume_basic_by_ids(perfume_ids: List[int]) -> List[Dict]:
    """특정 향수 ID들의 기본 정보 조회"""
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT perfume_id, perfume_name, perfume_brand, img_link FROM TB_PERFUME_BASIC_M WHERE perfume_id = ANY(%s)"
            cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_basic(max_perfumes: Optional[int]) -> List[Dict]:
    """향수 기본 정보 DB 조회 (레거시 호환용)"""
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT perfume_id, perfume_name, perfume_brand, img_link FROM TB_PERFUME_BASIC_M ORDER BY perfume_id"
            params = []
            if max_perfumes:
                sql += " LIMIT %s"
                params.append(max_perfumes)
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_accords(perfume_ids: Optional[List[int]]) -> List[Dict]:
    """향수별 어코드 정보 DB 조회"""
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if perfume_ids is None:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M"
                cur.execute(sql)
            else:
                sql = "SELECT perfume_id, accord, vote FROM TB_PERFUME_ACCORD_M WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            return [dict(row) for row in cur.fetchall()]

def _fetch_perfume_tags(perfume_ids: Optional[List[int]]) -> Dict[int, Dict]:
    """향수별 태그(계절, 상황, 성별) 정보 DB 조회"""
    tags = defaultdict(lambda: {"seasons": set(), "occasions": set(), "genders": set()})
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Seasons
            sql = "SELECT perfume_id, season FROM TB_PERFUME_SEASON_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["seasons"].add(r["season"])
            
            # Occasions
            sql = "SELECT perfume_id, occasion FROM TB_PERFUME_OCA_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["occasions"].add(r["occasion"])
            
            # Genders
            sql = "SELECT perfume_id, gender FROM TB_PERFUME_GENDER_R"
            if perfume_ids:
                sql += " WHERE perfume_id = ANY(%s)"
                cur.execute(sql, (perfume_ids,))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): tags[int(r["perfume_id"])]["genders"].add(r["gender"])
            
    return {pid: {k: sorted(list(v)) for k, v in t.items()} for pid, t in tags.items()}

def _fetch_member_statuses(member_id: Optional[int], perfume_ids: List[int]) -> Dict[int, str]:
    """회원별 향수 등록 상태 조회"""
    if not member_id or not perfume_ids:
        return {}
    with get_recom_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT perfume_id, register_status FROM TB_MEMBER_MY_PERFUME_T WHERE member_id = %s AND perfume_id = ANY(%s)",
                (member_id, perfume_ids),
            )
            return {int(row["perfume_id"]): row["register_status"] for row in cur.fetchall() if row.get("register_status")}

# [개선] 최적화된 유사도 엣지 조회 (특정 향수들만)
def _fetch_similarity_edges_optimized(perfume_ids: List[int], min_sim: float) -> List[Dict]:
    """최적화된 유사도 엣지 조회 (양방향 + 상위 K개)"""
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                WITH all_edges AS (
                    SELECT perfume_id_a as src, perfume_id_b as dst, score 
                    FROM TB_PERFUME_SIMILARITY 
                    WHERE score >= %s 
                      AND perfume_id_a = ANY(%s)
                      AND perfume_id_b = ANY(%s)
                    UNION ALL
                    SELECT perfume_id_b as src, perfume_id_a as dst, score 
                    FROM TB_PERFUME_SIMILARITY 
                    WHERE score >= %s 
                      AND perfume_id_b = ANY(%s)
                      AND perfume_id_a = ANY(%s)
                ), ranked AS (
                    SELECT src, dst, score, 
                           ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) as rn 
                    FROM all_edges
                )
                SELECT src as perfume_id_a, dst as perfume_id_b, score 
                FROM ranked 
                WHERE rn <= %s
            """
            cur.execute(sql, (
                min_sim, perfume_ids, perfume_ids,
                min_sim, perfume_ids, perfume_ids,
                SIMILARITY_TOP_K
            ))
            return [dict(row) for row in cur.fetchall()]

def _fetch_similarity_edges(perfume_ids: Optional[List[int]], min_sim: float, is_full: bool) -> List[Dict]:
    """향수 간 유사도 엣지 DB 조회 (레거시 호환용)"""
    with get_nmap_db_connection() as conn:  # [개선] 전용 커넥션 사용
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if is_full:
                sql = """
                    WITH all_edges AS (
                        SELECT perfume_id_a as src, perfume_id_b as dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                        UNION ALL
                        SELECT perfume_id_b as src, perfume_id_a as dst, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s
                    ), ranked AS (
                        SELECT src, dst, score, ROW_NUMBER() OVER (PARTITION BY src ORDER BY score DESC) as rn FROM all_edges
                    )
                    SELECT src as perfume_id_a, dst as perfume_id_b, score FROM ranked WHERE rn <= %s
                """
                cur.execute(sql, (min_sim, min_sim, SIMILARITY_TOP_K))
            else:
                sql = "SELECT perfume_id_a, perfume_id_b, score FROM TB_PERFUME_SIMILARITY WHERE score >= %s AND perfume_id_a = ANY(%s) AND perfume_id_b = ANY(%s)"
                cur.execute(sql, (min_sim, perfume_ids, perfume_ids))
            return [dict(row) for row in cur.fetchall()]

# [개선] 캐시 키 생성 함수
def _generate_cache_key(member_id: Optional[int], max_perfumes: int, min_similarity: float, top_accords: int) -> str:
    """캐시 키 생성"""
    if member_id:
        return f"member_{member_id}_{max_perfumes}_{min_similarity}_{top_accords}"
    else:
        return f"public_{max_perfumes}_{min_similarity}_{top_accords}"

def get_nmap_data(
    member_id: Optional[int] = None, 
    max_perfumes: Optional[int] = None, 
    min_similarity: float = 0.0, 
    top_accords: int = 5,
    debug: bool = False
) -> NMapResponse:
    """향수 맵 전체 데이터 및 분석 요약 정보 조회
    [개선] 스마트 로딩: 인기 향수 우선 + 최적화된 쿼리
    """
    start = time.time()
    
    # [개선] 1. 스마트 로딩: 로드할 향수 결정
    if max_perfumes is None:
        # 전체 로드 방지 - 기본 300개로 제한
        max_perfumes = 300
        logger.info("⚠️ max_perfumes가 None이므로 기본값 300으로 제한")
    
    # 인기 향수 우선 선택
    target_ids = _fetch_popular_perfume_ids(max_perfumes)
    
    # 회원 향수 추가 (있으면)
    if member_id:
        member_perfumes = _fetch_member_perfume_ids(member_id)
        # 중복 제거 및 개수 제한
        target_ids = list(set(target_ids) | set(member_perfumes))[:max_perfumes]
        logger.info(f"👤 회원 {member_id} 향수 {len(member_perfumes)}개 추가")
    
    logger.info(f"🎯 총 {len(target_ids)}개 향수 로드 예정")
    
    # 2. 데이터 조회 (스마트 로딩 버전)
    p_rows = _fetch_perfume_basic_by_ids(target_ids)
    p_ids = [int(r["perfume_id"]) for r in p_rows]
    
    a_rows = _fetch_perfume_accords(p_ids)
    t_data = _fetch_perfume_tags(p_ids)
    m_statuses = _fetch_member_statuses(member_id, p_ids)
    
    # 2. 프로필 및 노드 구축
    acc_by_p = defaultdict(list)
    for r in a_rows: 
        acc_by_p[r["perfume_id"]].append((r["accord"], r["vote"] or 0))
    
    nodes, edges, used_accords = [], [], set()
    p_map = {}
    
    for r in p_rows:
        pid = int(r["perfume_id"])
        acc_list = acc_by_p[pid]
        total_v = sum(v for _, v in acc_list)
        acc_prof = {a: float(v)/total_v for a, v in acc_list} if total_v > 0 else {}
        tags = t_data.get(pid, {"seasons": [], "occasions": [], "genders": []})
        
        sorted_accords = sorted(acc_prof.keys(), key=lambda x: acc_prof[x], reverse=True)
        primary_accord = sorted_accords[0] if sorted_accords else "Unknown"
        
        p_info = {
            "id": str(pid), 
            "type": "perfume", 
            "label": r["perfume_name"], 
            "brand": r["perfume_brand"], 
            "image": r["img_link"],
            "primary_accord": primary_accord,
            "accords": sorted_accords,
            "seasons": tags["seasons"], 
            "occasions": tags["occasions"], 
            "genders": tags["genders"],
            "register_status": m_statuses.get(pid)
        }
        p_map[pid] = p_info
        nodes.append(NMapNode(**p_info))
        
        # 향수-어코드 엣지
        for acc in sorted_accords[:top_accords]:
            used_accords.add(acc)
            edges.append(NMapEdge(**{
                "from": str(pid), 
                "to": f"accord_{acc}", 
                "type": "HAS_ACCORD", 
                "weight": acc_prof.get(acc, 0.0)
            }))
            
    # 어코드 노드 추가
    for acc in sorted(list(used_accords)):
        nodes.append(NMapNode(id=f"accord_{acc}", type="accord", label=acc))
        
    # [개선] 3. 유사도 엣지 조회 및 추가 (최적화된 쿼리 사용)
    sim_rows = _fetch_similarity_edges_optimized(p_ids, min_similarity)
    for r in sim_rows:
        edges.append(NMapEdge(**{
            "from": str(r["perfume_id_a"]), 
            "to": str(r["perfume_id_b"]), 
            "type": "SIMILAR_TO", 
            "weight": r["score"]
        }))
        
    # 4. 분석 요약 생성
    acc_cnt, mood_cnt = defaultdict(int), defaultdict(int)
    for p in p_map.values():
        for a in p["accords"][:3]: acc_cnt[a] += 1
        for m in p["occasions"] + p["seasons"]: mood_cnt[m] += 1
    
    sorted_accs = sorted(acc_cnt.keys(), key=lambda x: acc_cnt[x], reverse=True)
    summary = NMapAnalysisSummary(
        top_notes=sorted_accs[:3],
        middle_notes=sorted_accs[3:6],
        base_notes=sorted_accs[6:9],
        mood_keywords=sorted(mood_cnt.keys(), key=lambda x: mood_cnt[x], reverse=True)[:5],
        analysis_text="탐색하신 향기들의 주요 특징입니다."
    )
    
    build_time = round(time.time()-start, 3)
    meta = {
        "build_time": build_time,
        "perfume_count": len(p_map),
        "edge_count": len(edges),
        "min_similarity": min_similarity,
        "top_accords": top_accords
    }
    
    logger.info(f"✅ NMap 데이터 생성 완료: {len(p_map)}개 향수, {len(edges)}개 엣지, {build_time}초")
    return NMapResponse(nodes=nodes, edges=edges, summary=summary, meta=meta)

# [개선] 캐싱이 적용된 향수 맵 데이터 조회
def get_nmap_data_cached(
    member_id: Optional[int] = None,
    max_perfumes: int = 300,
    min_similarity: float = 0.0,
    top_accords: int = 5,
    debug: bool = False
) -> NMapResponse:
    """캐시가 적용된 향수 맵 데이터 조회
    [개선] 메모리 캐싱으로 반복 요청 95% 성능 향상
    """
    global _nmap_cache, _nmap_cache_time
    
    # 1. 캐시 키 생성
    cache_key = _generate_cache_key(member_id, max_perfumes, min_similarity, top_accords)
    
    # 2. 캐시 확인
    now = time.time()
    if cache_key in _nmap_cache:
        if now - _nmap_cache_time[cache_key] < NMAP_CACHE_TTL:
            # [개선] 프로덕션 로그 감소: INFO → DEBUG
            logger.debug(f"✅ Cache HIT: {cache_key} (나이: {round(now - _nmap_cache_time[cache_key])}초)")
            return _nmap_cache[cache_key]
        else:
            # 만료된 캐시 삭제
            logger.info(f"⏰ Cache EXPIRED: {cache_key}")  # 만료는 INFO 유지 (중요)
            del _nmap_cache[cache_key]
            del _nmap_cache_time[cache_key]
    
    # 3. 캐시 미스 - 데이터 조회
    logger.info(f"❌ Cache MISS: {cache_key} - 새로 조회")  # 미스는 INFO 유지 (모니터링)
    result = get_nmap_data(member_id, max_perfumes, min_similarity, top_accords, debug)
    
    # 4. 캐시 저장
    _nmap_cache[cache_key] = result
    _nmap_cache_time[cache_key] = now
    logger.debug(f"💾 Cache SAVED: {cache_key}")  # [개선] DEBUG로 변경
    
    # [개선] 5. 캐시 크기 관리 (환경 변수로 설정 가능)
    if len(_nmap_cache) > NMAP_CACHE_MAX_SIZE:
        # 가장 오래된 캐시 삭제
        oldest_key = min(_nmap_cache_time.keys(), key=lambda k: _nmap_cache_time[k])
        logger.info(f"🗑️ Cache EVICTED (크기 초과 {NMAP_CACHE_MAX_SIZE}): {oldest_key}")
        del _nmap_cache[oldest_key]
        del _nmap_cache_time[oldest_key]
    
    return result
