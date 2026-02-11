# backend/agent/tools.py
import asyncio
import itertools
import json
from typing import List, Dict, Any, Tuple, Optional

from langchain_core.tools import tool  # type: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # type: ignore[reportMissingImports]
from psycopg2.extras import RealDictCursor

from .database import (
    get_db_connection,
    release_db_connection,
    lookup_note_by_string,
    lookup_note_by_vector,
    search_perfumes,
    rerank_perfumes_async,
    get_perfumes_by_note,
)
from .expression_loader import ExpressionLoader
from .schemas import (
    LookupNoteInput,
    AdvancedSearchInput,
    NoteSearchInput,
    AccordSearchInput,
    PerfumeIdSearchInput,
)
from .utils import enrich_accord_description, sanitize_filters, remove_special_chars


NORMALIZER_LLM = ChatOpenAI(
    model="gpt-4o-mini", temperature=0, tags=["internal_helper"]
)

_expression_loader = ExpressionLoader()


def format_perfume_name(perfume: Dict) -> str:
    """향수명 포맷팅 (concentration 포함)"""
    name = perfume.get("name", "")
    concentration = perfume.get("concentration")
    if concentration and str(concentration).strip() and str(concentration).lower() != "nan":
        return f"{name} ({concentration})"
    return name


@tool(args_schema=LookupNoteInput)
async def lookup_note_by_string_tool(keyword: str) -> List[str]:
    """
    사용자가 직접 입력한 구체적인 향료 이름의 오탈자를 교정합니다.
    - 명시적 노드를 Hard Filter용 표준 명칭으로 바꿀 때 사용하세요.
    """
    # [최적화] 동기 DB 함수를 별도 스레드에서 실행하여 이벤트 루프 블로킹 방지
    return await asyncio.to_thread(lookup_note_by_string, keyword)


@tool(args_schema=LookupNoteInput)
async def lookup_note_by_vector_tool(keyword: str) -> List[str]:
    """
    추상적인 향기 느낌이나 키워드와 관련된 실제 향료 후보군 10개를 검색합니다.
    - AI가 제안한 키워드를 실제 DB 노드로 변환할 때 사용하세요.
    """
    # [최적화] 동기 함수를 비동기 스레드에서 처리
    return await asyncio.to_thread(lookup_note_by_vector, keyword)


@tool(args_schema=AdvancedSearchInput)
async def advanced_perfume_search_tool(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: Optional[List[int]] = None,
    exclude_brands: Optional[List[str]] = None,
    query_text: str = "",
    rank_mode: str = "DEFAULT",
) -> List[Dict[str, Any]]:
    """
    [고도화된 비동기 검색 도구]
    1. DB에서 조건에 맞는 향수 20개를 1차로 검색합니다. (병렬 처리 지원)
    2. 비동기 LLM을 이용해 리뷰 데이터와 전략 의도를 매칭하여 재정렬합니다.
    3. 최종 상위 5개를 반환합니다.
    """

    safe_exclude_ids: List[int] = exclude_ids or []
    safe_exclude_brands: List[str] = exclude_brands or []

    # 1. Broad Retrieval (Thread Pool 사용으로 병렬성 확보)
    candidates = await asyncio.to_thread(
        search_perfumes,
        hard_filters=hard_filters,
        strategy_filters=strategy_filters,
        exclude_ids=safe_exclude_ids,
        exclude_brands=safe_exclude_brands,
        limit=20,
    )

    if not candidates:
        return []

    # 2. Semantic Reranking (비동기 LLM 호출)
    # [최적화] rerank_perfumes_async를 호출하여 검색 중 발생하는 지연을 최소화합니다.
    final_results = await rerank_perfumes_async(
        candidates, query_text, top_k=5, rank_mode=rank_mode
    )

    return final_results


async def smart_perfume_search(
    h_filters: dict,
    s_filters: dict,
    exclude_ids: Optional[List[int]],
    query_text: str,
    rank_mode: str = "DEFAULT",
) -> Tuple[List[dict], str]:
    sanitized_hard, sanitized_strategy, _dropped_items = sanitize_filters(
        h_filters, s_filters
    )

    priority_order = ["note", "accord", "occasion"]
    active_keys = [
        k for k in priority_order if k in sanitized_strategy and sanitized_strategy[k]
    ]

    tool_runner: Any = advanced_perfume_search_tool
    results = await tool_runner.ainvoke(
        {
            "hard_filters": sanitized_hard,
            "strategy_filters": sanitized_strategy,
            "exclude_ids": exclude_ids,
            "query_text": query_text,
            "rank_mode": rank_mode,
        }
    )
    if results:
        return results, "Perfect Match"

    for r in range(len(active_keys) - 1, 0, -1):
        for combo_keys in itertools.combinations(active_keys, r):
            temp_filters = {k: sanitized_strategy[k] for k in combo_keys}
            results = await tool_runner.ainvoke(
                {
                    "hard_filters": sanitized_hard,
                    "strategy_filters": temp_filters,
                    "exclude_ids": exclude_ids,
                    "query_text": query_text,
                    "rank_mode": rank_mode,
                }
            )
            if results:
                return results, f"Relaxed (Level {len(active_keys) - r})"

    return [], "No Results"


@tool
def lookup_perfume_info_tool(user_input: str) -> Dict[str, Any] | List:
    """
    사용자가 입력한 향수 이름을 DB(영어명, 한글명, 별칭 포함)에서 정확히 찾아 상세 정보를 반환합니다.

    Returns:
        Dict: 향수 정보 (성공)
        List: 빈 리스트 [] (결과 없음)
    Raises:
        Exception: DB 에러 또는 검색 실패
    """
    normalization_prompt = f"""
    You are a Perfume Database Expert.
    User Input: "{user_input}"
    Task: Identify Brand and Name, Convert to English.
    Example: "조말론 우드세이지" -> {{"brand": "Jo Malone", "name": "Wood Sage & Sea Salt"}}
    Output strictly JSON.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned_json = norm_result.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_json)
        target_brand = " ".join(parsed.get("brand", "").split()).strip()
        target_name = " ".join(parsed.get("name", "").split()).strip()
    except Exception as e:
        raise Exception(f"검색어 분석 실패: {e}")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # [Phase 1] 특수문자 완전 제거
        normalized_name = remove_special_chars(target_name)

        sql = """
            SELECT
                p.perfume_id, p.perfume_brand, p.perfume_name, p.img_link,
                (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = p.perfume_id LIMIT 1) as gender,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='BASE') as base_notes,
                (SELECT STRING_AGG(accord, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_ACCORD_R WHERE perfume_id = p.perfume_id) as accords,
                (SELECT STRING_AGG(season, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_SEASON_R WHERE perfume_id = p.perfume_id) as seasons,
                (SELECT STRING_AGG(occasion, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_OCA_R WHERE perfume_id = p.perfume_id) as occasions
            FROM TB_PERFUME_BASIC_M p
            LEFT JOIN TB_PERFUME_NAME_KR n ON p.perfume_id = n.perfume_id

            WHERE p.perfume_brand ILIKE %s
              AND (
                  REGEXP_REPLACE(p.perfume_name, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                  OR REGEXP_REPLACE(n.name_kr, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                  OR REGEXP_REPLACE(n.search_keywords, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
              )

            ORDER BY
                CASE
                    WHEN REGEXP_REPLACE(p.perfume_name, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s THEN 0
                    WHEN REGEXP_REPLACE(n.name_kr, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s THEN 1
                    ELSE 2
                END,
                LENGTH(p.perfume_name) ASC
            LIMIT 1
        """

        brand_pattern = f"%{target_brand}%"
        normalized_pattern = f"%{normalized_name}%"

        params = (
            brand_pattern,
            normalized_pattern,
            normalized_pattern,
            normalized_pattern,
            normalized_pattern,
            normalized_pattern,
        )

        cur.execute(sql, params)
        result = cur.fetchone()

        if result:
            return dict(result)  # 객체 반환
        return []  # 빈 리스트 반환
    except Exception as e:
        raise Exception(f"DB 에러: {e}")
    finally:
        cur.close()
        release_db_connection(conn)


@tool(args_schema=PerfumeIdSearchInput)
def lookup_perfume_by_id_tool(perfume_id: int) -> Dict[str, Any] | List:
    """
    perfume_id를 받아 향수 상세 정보를 반환합니다.

    Returns:
        Dict: 향수 정보 (성공)
        List: 빈 리스트 [] (결과 없음)
    Raises:
        Exception: DB 에러
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        sql = """
            SELECT
                p.perfume_id, p.perfume_brand, p.perfume_name, p.img_link,
                (SELECT gender FROM TB_PERFUME_GENDER_R WHERE perfume_id = p.perfume_id LIMIT 1) as gender,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT note, ', ') FROM TB_PERFUME_NOTES_M WHERE perfume_id = p.perfume_id AND type='BASE') as base_notes,
                (SELECT STRING_AGG(accord, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_ACCORD_R WHERE perfume_id = p.perfume_id) as accords,
                (SELECT STRING_AGG(season, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_SEASON_R WHERE perfume_id = p.perfume_id) as seasons,
                (SELECT STRING_AGG(occasion, ', ' ORDER BY ratio DESC) FROM TB_PERFUME_OCA_R WHERE perfume_id = p.perfume_id) as occasions
            FROM TB_PERFUME_BASIC_M p
            WHERE p.perfume_id = %s
        """

        cur.execute(sql, (perfume_id,))
        result = cur.fetchone()

        if result:
            return dict(result)  # 객체 반환
        return []  # 빈 리스트 반환
    except Exception as e:
        raise Exception(f"DB 에러: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)


@tool(args_schema=NoteSearchInput)
def lookup_note_info_tool(keywords: List[str]) -> Dict[str, Any] | List:
    """
    노트(원료) 리스트를 받아 [감각적 묘사]와 [관련 어코드 설명]을 포함한 상세 정보를 반환합니다.

    Returns:
        Dict: 노트별 정보 (성공)
        List: 빈 리스트 [] (결과 없음)
    Raises:
        Exception: DB 에러
    """
    normalization_prompt = f"""
    You are a Fragrance Ingredient Expert.
    User Keywords: {keywords}
    Task: Translate keywords to official English Perfumery Notes (Singular, Capitalized).
    Strictly interpret in PERFUME context (e.g., '통카' -> "Tonka Bean").
    Output strictly JSON List.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned = norm_result.replace("```json", "").replace("```", "").strip()
        target_notes = json.loads(cleaned)
    except Exception:
        target_notes = keywords

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    final_info = {}

    try:
        for note in target_notes:
            sql_perfumes = """
                SELECT
                    m.perfume_brand,
                    m.perfume_name
                FROM TB_PERFUME_NOTES_M n
                JOIN TB_PERFUME_BASIC_M m ON n.perfume_id = m.perfume_id
                LEFT JOIN (
                    SELECT PERFUME_ID, SUM(VOTE) as total_votes
                    FROM TB_PERFUME_ACCORD_M
                    GROUP BY PERFUME_ID
                ) pop ON m.perfume_id = pop.PERFUME_ID
                WHERE n.note ILIKE %s
                GROUP BY m.perfume_id, m.perfume_brand, m.perfume_name, pop.total_votes
                ORDER BY pop.total_votes DESC NULLS LAST
                LIMIT 3
            """
            cur.execute(sql_perfumes, (f"%{note}%",))
            examples = [
                f"{r['perfume_brand']} {r['perfume_name']}" for r in cur.fetchall()
            ]

            if not examples:
                continue

            dict_desc = _expression_loader.get_note_desc(note)

            sql_desc = "SELECT description FROM TB_NOTE_EMBEDDING_M WHERE note ILIKE %s LIMIT 1"
            cur.execute(sql_desc, (note,))
            row = cur.fetchone()
            db_desc = row["description"] if row else ""

            enriched_db_desc = enrich_accord_description(db_desc)

            if dict_desc and enriched_db_desc:
                full_description = f"{dict_desc}\n\n[상세 특징]: {enriched_db_desc}"
            elif dict_desc:
                full_description = dict_desc
            elif enriched_db_desc:
                full_description = enriched_db_desc
            else:
                full_description = "상세 설명 정보가 없습니다."

            final_info[note] = {
                "description": full_description,
                "representative_perfumes": examples,
            }

        if not final_info:
            return []  # 빈 리스트 반환

        return final_info  # 객체 반환
    except Exception as e:
        raise Exception(f"Error: {e}")
    finally:
        cur.close()
        release_db_connection(conn)


@tool(args_schema=AccordSearchInput)
def lookup_accord_info_tool(keywords: List[str]) -> Dict[str, Any] | List:
    """
    어코드(향조) 리스트를 받아 [사전적 분위기 묘사]와 [대표 향수]를 반환합니다.

    Returns:
        Dict: 어코드별 정보 (성공)
        List: 빈 리스트 [] (결과 없음)
    Raises:
        Exception: DB 에러
    """
    normalization_prompt = f"""
    You are a Fragrance Accord Expert.
    User Keywords: {keywords}
    Task: Translate to official English Accords.
    Output strictly JSON List.
    """
    try:
        norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
        cleaned = norm_result.replace("```json", "").replace("```", "").strip()
        target_accords = json.loads(cleaned)
    except Exception:
        target_accords = keywords

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    final_info = {}

    try:
        for accord in target_accords:
            sql = """
                SELECT m.perfume_brand, m.perfume_name
                FROM TB_PERFUME_ACCORD_M a
                JOIN TB_PERFUME_BASIC_M m ON a.perfume_id = m.perfume_id
                WHERE a.accord ILIKE %s
                GROUP BY m.perfume_id, m.perfume_brand, m.perfume_name
                ORDER BY MAX(a.vote) DESC NULLS LAST
                LIMIT 3
            """
            cur.execute(sql, (f"%{accord}%",))
            examples = [
                f"{r['perfume_brand']} {r['perfume_name']}" for r in cur.fetchall()
            ]

            if not examples:
                continue

            desc = _expression_loader.get_accord_desc(accord)
            if not desc:
                desc = "특정한 분위기를 자아내는 향의 계열입니다."
            else:
                desc = f"{accord}: {desc}"

            final_info[accord] = {
                "description": desc,
                "representative_perfumes": examples,
            }

        if not final_info:
            return []  # 빈 리스트 반환

        return final_info  # 객체 반환
    except Exception as e:
        raise Exception(f"Error: {e}")
    finally:
        cur.close()
        release_db_connection(conn)


@tool
def lookup_similar_perfumes_tool(user_input: str) -> Dict[str, Any] | List:
    """
    사용자가 언급한 향수와 '가장 유사한 향수' 3개를 찾아서 반환합니다.
    (기준: 어코드와 노트의 구성이 얼마나 겹치는지 분석)

    Args:
        user_input: "브랜드|영어명|한글명" 형식 또는 단순 문자열

    Returns:
        Dict: {"target_perfume": str, "similar_list": List[Dict]} (성공)
        List: 빈 리스트 [] (결과 없음)
    Raises:
        Exception: DB 에러 또는 검색 실패
    """

    # [Phase 0] 노트 이름인지 확인하고 변환
    note_perfumes = get_perfumes_by_note(user_input)
    if note_perfumes:
        # 노트가 포함된 향수가 있으면 첫 번째 향수를 기준으로 검색
        search_input = note_perfumes[0]['name']
        print(f"📝 [Note Detected] '{user_input}' 노트가 포함된 향수로 검색: {search_input}", flush=True)
    else:
        search_input = user_input

    # [Phase 4] 파이프 구분자 파싱 (브랜드|영어명|한글명)
    if "|" in search_input:
        parts = search_input.split("|")
        target_brand = parts[0].strip() if len(parts) > 0 and parts[0] else ""
        target_name = parts[1].strip() if len(parts) > 1 and parts[1] else ""
        target_name_kr = parts[2].strip() if len(parts) > 2 and parts[2] else ""

        # 한글명이 있으면 우선 사용, 없으면 영어명 사용
        search_name = target_name_kr if target_name_kr else target_name
    else:
        # 기존 로직 (하위 호환): LLM으로 파싱
        normalization_prompt = f"""
        User Input: "{search_input}"
        Task: Extract the Target Perfume Name user likes.
        Output JSON: {{"brand": "Brand", "name": "Name"}}
        """
        try:
            norm_result = NORMALIZER_LLM.invoke(normalization_prompt).content
            cleaned_json = norm_result.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned_json)
            target_brand = parsed.get("brand", "")
            target_name = parsed.get("name", "")
            search_name = target_name
        except Exception as e:
            # LLM 변환 실패 시 원본 입력 사용
            target_brand = ""
            target_name = search_input
            search_name = search_input

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # [Phase 1] 특수문자 완전 제거
        normalized_name = remove_special_chars(search_name)

        # 브랜드가 있으면 브랜드+이름 검색, 없으면 이름만 검색
        if target_brand:
            # 브랜드 지정 검색 (더 정확)
            sql = """
                WITH TARGET_PERFUME AS (
                    SELECT p.PERFUME_ID, p.PERFUME_NAME, p.PERFUME_BRAND
                    FROM TB_PERFUME_BASIC_M p
                    LEFT JOIN TB_PERFUME_NAME_KR n ON p.perfume_id = n.perfume_id
                    WHERE p.PERFUME_BRAND ILIKE %s
                      AND (
                          REGEXP_REPLACE(p.PERFUME_NAME, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                          OR REGEXP_REPLACE(n.name_kr, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                          OR REGEXP_REPLACE(n.search_keywords, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                      )
                    ORDER BY LENGTH(p.PERFUME_NAME) ASC
                    LIMIT 1
                ),
                TARGET_ACCORDS AS (
                    SELECT ACCORD FROM TB_PERFUME_ACCORD_R
                    WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
                ),
                TARGET_NOTES AS (
                    SELECT NOTE FROM TB_PERFUME_NOTES_M
                    WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
                ),
                SIMILARITY_SCORE AS (
                    SELECT
                        p.perfume_id,
                        p.perfume_brand,
                        p.perfume_name,
                        p.img_link,
                        (
                            (SELECT COUNT(*) FROM TB_PERFUME_ACCORD_R a
                             WHERE a.perfume_id = p.perfume_id
                             AND a.accord IN (SELECT ACCORD FROM TARGET_ACCORDS)) * 3
                            +
                            (SELECT COUNT(*) FROM TB_PERFUME_NOTES_M n
                             WHERE n.perfume_id = p.perfume_id
                             AND n.note IN (SELECT NOTE FROM TARGET_NOTES)) * 1
                        ) as score
                    FROM TB_PERFUME_BASIC_M p
                    WHERE p.perfume_id != (SELECT PERFUME_ID FROM TARGET_PERFUME)
                )
                SELECT s.*,
                       (SELECT PERFUME_BRAND FROM TARGET_PERFUME) as target_brand,
                       (SELECT PERFUME_NAME FROM TARGET_PERFUME) as target_name
                FROM SIMILARITY_SCORE s
                WHERE score > 0
                ORDER BY score DESC
                LIMIT 3;
            """
            brand_pattern = f"%{target_brand}%"
            name_pattern = f"%{normalized_name}%"
            params_target = (brand_pattern, name_pattern, name_pattern, name_pattern)
        else:
            # 이름만으로 검색 (브랜드 불명확) - 한글 테이블도 조인
            sql = """
                WITH TARGET_PERFUME AS (
                    SELECT p.PERFUME_ID, p.PERFUME_NAME, p.PERFUME_BRAND
                    FROM TB_PERFUME_BASIC_M p
                    LEFT JOIN TB_PERFUME_NAME_KR n ON p.perfume_id = n.perfume_id
                    WHERE REGEXP_REPLACE(p.PERFUME_NAME, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                       OR REGEXP_REPLACE(n.name_kr, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                       OR REGEXP_REPLACE(n.search_keywords, '[^a-zA-Z0-9가-힣]', '', 'g') ILIKE %s
                    ORDER BY LENGTH(p.PERFUME_NAME) ASC
                    LIMIT 1
                ),
                TARGET_ACCORDS AS (
                    SELECT ACCORD FROM TB_PERFUME_ACCORD_R
                    WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
                ),
                TARGET_NOTES AS (
                    SELECT NOTE FROM TB_PERFUME_NOTES_M
                    WHERE PERFUME_ID = (SELECT PERFUME_ID FROM TARGET_PERFUME)
                ),
                SIMILARITY_SCORE AS (
                    SELECT
                        p.perfume_id,
                        p.perfume_brand,
                        p.perfume_name,
                        p.img_link,
                        (
                            (SELECT COUNT(*) FROM TB_PERFUME_ACCORD_R a
                             WHERE a.perfume_id = p.perfume_id
                             AND a.accord IN (SELECT ACCORD FROM TARGET_ACCORDS)) * 3
                            +
                            (SELECT COUNT(*) FROM TB_PERFUME_NOTES_M n
                             WHERE n.perfume_id = p.perfume_id
                             AND n.note IN (SELECT NOTE FROM TARGET_NOTES)) * 1
                        ) as score
                    FROM TB_PERFUME_BASIC_M p
                    WHERE p.perfume_id != (SELECT PERFUME_ID FROM TARGET_PERFUME)
                )
                SELECT s.*,
                       (SELECT PERFUME_BRAND FROM TARGET_PERFUME) as target_brand,
                       (SELECT PERFUME_NAME FROM TARGET_PERFUME) as target_name
                FROM SIMILARITY_SCORE s
                WHERE score > 0
                ORDER BY score DESC
                LIMIT 3;
            """
            name_pattern = f"%{normalized_name}%"
            params_target = (name_pattern, name_pattern, name_pattern)

        # SQL 완성 및 실행
        cur.execute(sql, params_target)
        results = cur.fetchall()

        # [Fallback] 결과가 3개 미만이면 계열/브랜드 기반 Fallback 검색
        if len(results) < 3:
            print(f"   🔄 [Fallback] Similar perfumes insufficient ({len(results)} found), trying fallback...", flush=True)
            
            # 타겟 향수의 계열과 브랜드 조회
            fallback_sql = """
                SELECT 
                    p.perfume_id,
                    p.perfume_brand,
                    p.perfume_name,
                    p.img_link,
                    COALESCE(
                        (SELECT STRING_AGG(accord, ', ') 
                         FROM TB_PERFUME_ACCORD_R 
                         WHERE perfume_id = p.perfume_id),
                        ''
                    ) as accords
                FROM TB_PERFUME_BASIC_M p
                WHERE p.perfume_id != (SELECT perfume_id FROM TARGET_PERFUME)
                  AND (
                      p.perfume_brand = (SELECT perfume_brand FROM TARGET_PERFUME)
                      OR EXISTS (
                          SELECT 1 FROM TB_PERFUME_ACCORD_R a1
                          JOIN TB_PERFUME_ACCORD_R a2 ON a1.accord = a2.accord
                          WHERE a1.perfume_id = p.perfume_id
                            AND a2.perfume_id = (SELECT perfume_id FROM TARGET_PERFUME)
                      )
                  )
                ORDER BY 
                    CASE WHEN p.perfume_brand = (SELECT perfume_brand FROM TARGET_PERFUME) 
                         THEN 0 ELSE 1 END,
                    p.perfume_id
                LIMIT 5;
            """
            
            try:
                cur.execute(fallback_sql)
                fallback_results = cur.fetchall()
                
                # 기존 결과와 병합 (중복 제거)
                existing_ids = {r['perfume_id'] for r in results}
                for r in fallback_results:
                    if r['perfume_id'] not in existing_ids:
                        results.append(r)
                        existing_ids.add(r['perfume_id'])
                        
                print(f"   ✅ [Fallback] Total {len(results)} perfumes after fallback", flush=True)
            except Exception as fallback_error:
                print(f"   ⚠️ [Fallback] Fallback query failed: {fallback_error}", flush=True)

        if not results:
            return []  # 빈 리스트 반환

        # 첫 번째 결과에서 타겟 향수 정보 추출
        first_result = results[0]
        target_brand_found = first_result.get('target_brand', '')
        target_name_found = first_result.get('target_name', '')
        target_display = f"{target_brand_found} - {target_name_found}"

        # similar_list에서 target_brand, target_name 제거
        similar_list = []
        for r in results:
            item = dict(r)
            item.pop('target_brand', None)
            item.pop('target_name', None)
            similar_list.append(item)

        return {
            "target_perfume": target_display,
            "similar_list": similar_list,
        }  # 객체 반환

    except Exception as e:
        raise Exception(f"유사 향수 검색 실패: {e}")
    finally:
        cur.close()
        release_db_connection(conn)


TOOLS = [
    advanced_perfume_search_tool,
    lookup_perfume_info_tool,
    lookup_perfume_by_id_tool,
    lookup_note_info_tool,
    lookup_accord_info_tool,
    lookup_similar_perfumes_tool,
]
