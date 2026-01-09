# tools.py
import re
import json
from openai import OpenAI
from psycopg2.extras import DictCursor
from database import get_db_connection

client = OpenAI()


# ==========================================
# 유틸리티
# ==========================================
def safe_json_parse(text: str, default=None):
    if not text or not text.strip():
        return default
    try:
        text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*", "", text).strip()
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else json.loads(text)
    except:
        return default


def get_embedding(text):
    return (
        client.embeddings.create(
            input=text.replace("\n", " "), model="text-embedding-3-small"
        )
        .data[0]
        .embedding
    )


# ==========================================
# 검색 도구 (Tools)
# ==========================================
def search_notes_smart(keyword: str) -> list[str]:
    """하이브리드 노트 검색 (Text + Vector)"""
    results = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Text Search
        clean_keyword = keyword.replace("향", "").strip()
        cur.execute(
            "SELECT note FROM tb_note_embedding_m WHERE note ILIKE %s LIMIT 3",
            (f"%{clean_keyword}%",),
        )
        results.extend([r[0] for r in cur.fetchall()])

        # 2. Vector Search (부족할 경우)
        if len(results) < 3:
            query_vector = get_embedding(keyword)
            exclude_cond = ""
            if results:
                formatted_excludes = (
                    "'" + "','".join([r.replace("'", "''") for r in results]) + "'"
                )
                exclude_cond = f"AND note NOT IN ({formatted_excludes})"

            sql = f"""
                SELECT note FROM tb_note_embedding_m WHERE 1=1 {exclude_cond}
                ORDER BY embedding <=> %s::vector LIMIT %s;
            """
            cur.execute(sql, (query_vector, 3 - len(results)))
            results.extend([r[0] for r in cur.fetchall()])

        conn.close()
        print(f"   ✅ 노트 검색 결과: '{keyword}' -> {list(set(results))}")
        return list(set(results))
    except Exception as e:
        print(f"⚠️ 노트 검색 오류: {e}")
        return []


def search_exact_entity_name(keyword: str, entity_type: str = "brand") -> str | None:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        table = "tb_perfume_basic_m"
        col = "perfume_brand" if entity_type == "brand" else "perfume_name"
        cur.execute(
            f"SELECT {col} FROM {table} WHERE {col} ILIKE %s LIMIT 1", (f"%{keyword}%",)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except:
        return keyword


def execute_search_with_fallback(filters: list[dict]) -> str:
    """
    [핵심 수정] 필터 조건에 맞는 향수를 검색하되,
    STRING_AGG를 사용하여 노트, 어코드, 계절 정보를 모두 가져옵니다.
    """
    if not filters:
        return "검색 조건을 추출하지 못했습니다."

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    while True:
        print(
            f"\n🔄 [DB] 검색 시도: {[f['column'] + '=' + str(f['value']) for f in filters]}"
        )

        where_clauses = []
        params = []

        # 1. WHERE 조건절 동적 생성
        for f in filters:
            col = f["column"]
            val = f["value"]

            if col == "brand":
                clause = "AND b.perfume_brand ILIKE %s"
            elif col == "perfume_name":
                clause = "AND b.perfume_name ILIKE %s"
            elif col == "note":
                if isinstance(val, list) and val:
                    # 노트 목록 중 '하나라도' 포함되면 검색 (OR 조건 느낌의 IN)
                    # 주의: JOIN 후 필터링하면 해당 노트만 남을 수 있으므로,
                    # 정확한 스펙을 위해서는 Subquery가 좋지만 성능상 여기서는 JOIN 필터 사용
                    clause = f"AND n.note IN ({','.join(['%s']*len(val))})"
                    where_clauses.append(clause)
                    params.extend(val)
                    continue
                else:
                    clause = "AND n.note = %s"
            elif col == "season":
                clause = "AND s.season = %s"
            elif col == "gender":
                clause = "AND a.audience = %s"
            elif col == "occasion":
                clause = "AND o.occasion = %s"
            elif col == "accord":
                clause = "AND ac.accord = %s"
            else:
                continue

            where_clauses.append(clause)
            params.append(val)

        # 2. [Aggregation Query] 모든 정보 긁어오기
        # STRING_AGG(DISTINCT col, ', ')로 중복 제거하며 합치기
        sql = f"""
            SELECT 
                b.perfume_id,
                b.perfume_name, 
                b.perfume_brand,
                STRING_AGG(DISTINCT ac.accord, ', ') as accords,
                STRING_AGG(DISTINCT s.season, ', ') as seasons,
                STRING_AGG(DISTINCT a.audience, ', ') as genders,
                STRING_AGG(DISTINCT o.occasion, ', ') as occasions,
                -- 검색된 노트 위주로 보일 수 있지만 정보 제공 차원
                STRING_AGG(DISTINCT n.note, ', ') as notes 
            FROM tb_perfume_basic_m b
            LEFT JOIN tb_perfume_notes_m n ON b.perfume_id = n.perfume_id
            LEFT JOIN tb_perfume_season_m s ON b.perfume_id = s.perfume_id
            LEFT JOIN tb_perfume_aud_m a ON b.perfume_id = a.perfume_id
            LEFT JOIN tb_perfume_oca_m o ON b.perfume_id = o.perfume_id
            LEFT JOIN tb_perfume_accord_m ac ON b.perfume_id = ac.perfume_id
            WHERE 1=1 {' '.join(where_clauses)}
            GROUP BY b.perfume_id, b.perfume_name, b.perfume_brand
            LIMIT 5;
        """

        try:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            if rows:
                conn.close()
                # 3. 결과 포맷팅 (풍부한 정보 제공)
                result_txt = "🔍 [DB 검색 결과 - 상세 정보]:\n\n"
                for i, r in enumerate(rows, 1):
                    result_txt += f"{i}. [{r['perfume_brand']}] {r['perfume_name']}\n"
                    result_txt += f"   - 특징(Accord): {r['accords']}\n"
                    result_txt += f"   - 분위기: {r['seasons']} / {r['genders']} / {r['occasions']}\n"
                    result_txt += f"   - 주요 노트: {r['notes']}\n\n"
                return result_txt

        except Exception as e:
            conn.rollback()
            print(f"   ⚠️ SQL 에러: {e}")

        if filters:
            removed = filters.pop()
            print(f"   ❌ 실패 -> 조건 완화: '{removed['column']}' 제거")
        else:
            break

    conn.close()
    return "검색 결과가 없습니다."
