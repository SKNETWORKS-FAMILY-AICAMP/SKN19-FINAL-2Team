# tools.py
import re
import json
import traceback
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
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else json.loads(text)
    except:
        return default

def get_embedding(text):
    try:
        return (
            client.embeddings.create(
                input=text.replace("\n", " "), model="text-embedding-3-small"
            )
            .data[0]
            .embedding
        )
    except Exception:
        print("⚠️ Embedding Error")
        traceback.print_exc()
        return []

# ==========================================
# 검색 도구 (Tools)
# ==========================================
def search_notes_vector(keyword: str, top_k: int = 3) -> list[str]:
    """
    [Vector DB] 사용자의 추상적 표현을 구체적인 향료 노트로 변환
    """
    results = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. 텍스트 매칭 (보조)
        cur.execute("SELECT note FROM tb_note_embedding_m WHERE note ILIKE %s LIMIT %s", (f"%{keyword}%", top_k))
        results.extend([r[0] for r in cur.fetchall()])
        
        # 2. 벡터 유사도 검색 (핵심)
        if len(results) < top_k:
            query_vector = get_embedding(keyword)
            if query_vector:
                exclude_sql = ""
                if results:
                    formatted = "'" + "','".join([r.replace("'", "''") for r in results]) + "'"
                    exclude_sql = f"AND note NOT IN ({formatted})"
                
                sql = f"""
                    SELECT note 
                    FROM tb_note_embedding_m 
                    WHERE 1=1 {exclude_sql}
                    ORDER BY embedding <=> %s::vector 
                    LIMIT %s;
                """
                cur.execute(sql, (query_vector, top_k - len(results)))
                results.extend([r[0] for r in cur.fetchall()])
            
        conn.close()
        return list(set(results))
    except Exception:
        print(f"⚠️ Note Search Error: {keyword}")
        traceback.print_exc()
        return []

def search_exact_entity(keyword: str, type_: str = "brand") -> str | None:
    """
    브랜드나 향수 이름 정확도 보정 (Fuzzy Search)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        table = "tb_perfume_basic_m"
        col = "perfume_brand" if type_ == "brand" else "perfume_name"
        
        cur.execute(f"SELECT {col} FROM {table} WHERE {col} ILIKE %s LIMIT 1", (f"%{keyword}%",))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        print(f"⚠️ Entity Search Error: {keyword}")
        traceback.print_exc()
        return None

def execute_precise_search(filters: list[dict]) -> str | None:
    """
    필터 조건에 맞춰 향수를 검색하고, 모든 상세 정보를 반환합니다.
    로그를 사람이 읽기 좋게 출력합니다.
    """
    if not filters:
        return None
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        where_clauses = []
        params = []
        
        # 로그 개선: 깔끔하게 필터 내역 출력
        print(f"\n🔍 [검색 필터 적용]")
        valid_filters = False

        for f in filters:
            col = f.get("column", "").lower().strip()
            val = f.get("value")
            
            if not col or not val: continue

            # 로그용 한글 컬럼명 매핑
            col_map = {
                "brand": "브랜드", "perfume_name": "이름", "note": "노트", 
                "accord": "어코드(느낌)", "season": "계절", "gender": "성별", 
                "occasion": "상황", "name": "이름"
            }
            readable_col = col_map.get(col, col)
            print(f"   👉 [{readable_col}]: {val}")
            valid_filters = True

            # SQL 조립
            if col == "brand":
                where_clauses.append("AND b.perfume_brand ILIKE %s")
                params.append(val)
            elif col in ["perfume_name", "name"]:
                where_clauses.append("AND b.perfume_name ILIKE %s")
                params.append(val)
            elif col == "note":
                if isinstance(val, list) and val:
                    placeholders = ",".join(["%s"] * len(val))
                    where_clauses.append(f"AND n.note IN ({placeholders})")
                    params.extend(val)
                else:
                    where_clauses.append("AND n.note = %s")
                    params.append(val)
            elif col == "accord":
                where_clauses.append("AND ac.accord = %s")
                params.append(val)
            elif col == "season":
                where_clauses.append("AND s.season = %s")
                params.append(val)
            elif col == "gender":
                where_clauses.append("AND a.audience = %s")
                params.append(val)
            elif col == "occasion":
                where_clauses.append("AND o.occasion = %s")
                params.append(val)

        if not valid_filters or not where_clauses:
            print("   ⚠️ 유효한 필터가 없어 검색을 중단합니다.")
            return None

        # 정보 추가: 이미지, 조향사, 출시일 등 모든 정보 조회
        sql = f"""
            SELECT 
                b.perfume_id,
                b.perfume_name, 
                b.perfume_brand,
                b.img_link,          
                b.perfumer,          
                b.release_year,      
                b.concentration,     
                STRING_AGG(DISTINCT ac.accord, ', ') as accords,
                STRING_AGG(DISTINCT s.season, ', ') as seasons,
                STRING_AGG(DISTINCT n.note, ', ') as notes 
            FROM tb_perfume_basic_m b
            LEFT JOIN tb_perfume_notes_m n ON b.perfume_id = n.perfume_id
            LEFT JOIN tb_perfume_season_m s ON b.perfume_id = s.perfume_id
            LEFT JOIN tb_perfume_aud_m a ON b.perfume_id = a.perfume_id
            LEFT JOIN tb_perfume_accord_m ac ON b.perfume_id = ac.perfume_id
            LEFT JOIN tb_perfume_oca_m o ON b.perfume_id = o.perfume_id
            WHERE 1=1 {' '.join(where_clauses)}
            GROUP BY 
                b.perfume_id, b.perfume_name, b.perfume_brand, 
                b.img_link, b.perfumer, b.release_year, b.concentration
            ORDER BY RANDOM()
            LIMIT 5;
        """
        
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        
        if not rows:
            return None
            
        # 결과 포맷팅
        result_txt = ""
        for i, r in enumerate(rows, 1):
            result_txt += f"no.{i}\n"
            result_txt += f"브랜드: {r['perfume_brand']}\n"
            result_txt += f"이름: {r['perfume_name']}\n"
            result_txt += f"이미지: {r['img_link']}\n"  # Writer가 사용할 링크
            result_txt += f"조향사: {r['perfumer'] or '정보 없음'}\n"
            result_txt += f"출시: {r['release_year'] or '?'}\n"
            result_txt += f"노트: {r['notes'][:100]}...\n" 
            result_txt += f"특징: {r['accords']}\n"
            result_txt += f"계절: {r['seasons']}\n"
            result_txt += "-" * 20 + "\n"
            
        return result_txt
        
    except Exception:
        print("⚠️ SQL Execution Error")
        traceback.print_exc()
        return None
    finally:
        if conn: conn.close()