import re
import json
import traceback
from openai import OpenAI
import psycopg2
from psycopg2.extras import DictCursor
from database import get_db_connection

client = OpenAI()

# ==========================================
# 1. 유틸리티 함수
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
        print("⚠️ Embedding Error", flush=True)
        traceback.print_exc()
        return []

# ==========================================
# 2. 데이터 가공 헬퍼 함수
# ==========================================
def filter_by_votes(data_list, threshold_ratio=0.10):
    """
    투표 데이터에서 상위 N% 이상인 항목만 남기고, 문자열로 변환하여 반환
    """
    if not data_list or data_list == [None]:
        return "정보 없음"
    
    valid_items = [d for d in data_list if d and d.get('vote') is not None]
    if not valid_items:
        return "정보 없음"

    total_votes = sum(item['vote'] for item in valid_items)
    if total_votes == 0:
        return "정보 없음"

    filtered = []
    for item in valid_items:
        ratio = item['vote'] / total_votes
        if ratio >= threshold_ratio: 
            filtered.append(f"{item['name']}")
    
    return ", ".join(filtered) if filtered else "정보 없음"

def format_notes(notes_json):
    """
    노트 정보를 Top/Middle/Base로 분류하여 텍스트로 반환
    """
    if not notes_json or notes_json == [None]:
        return "정보 없음"
    
    structure = {"TOP": [], "MIDDLE": [], "BASE": [], "SINGLE": []}
    
    for n in notes_json:
        if not n or not n.get('name'): continue
        n_type = n.get('type', 'SINGLE')
        if n_type:
            n_type = n_type.upper()
        else:
            n_type = "SINGLE"
            
        if n_type not in structure:
            n_type = "SINGLE"
        structure[n_type].append(n['name'])
        
    result = []
    if structure["TOP"]: result.append(f"   [Top]: {', '.join(structure['TOP'])}")
    if structure["MIDDLE"]: result.append(f"   [Middle]: {', '.join(structure['MIDDLE'])}")
    if structure["BASE"]: result.append(f"   [Base]: {', '.join(structure['BASE'])}")
    if structure["SINGLE"] and not result: result.append(f"   [Notes]: {', '.join(structure['SINGLE'])}")
    
    return "\n".join(result)

# ==========================================
# 3. 검색 함수들
# ==========================================

def search_exact_entity(keyword: str, entity_type: str) -> str | None:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        table = "tb_perfume_basic_m"
        col = "perfume_brand" if entity_type == "brand" else "perfume_name"
        
        cur.execute(f"SELECT {col} FROM {table} WHERE {col} ILIKE %s LIMIT 1", (keyword,))
        row = cur.fetchone()
        conn.close()
        
        return row[0] if row else None
    except Exception:
        return None

def search_notes_vector(keyword: str, top_k: int = 3) -> list[str]:
    results = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Exact Match
        cur.execute("SELECT note FROM tb_note_embedding_m WHERE note ILIKE %s LIMIT %s", (f"%{keyword}%", top_k))
        results.extend([r[0] for r in cur.fetchall()])
        
        # 2. Levenshtein (Typo)
        if len(results) < top_k:
            exclude_sql = ""
            if results:
                formatted = "'" + "','".join([r.replace("'", "''") for r in results]) + "'"
                exclude_sql = f"AND note NOT IN ({formatted})"

            try:
                # DB에 fuzzystrmatch 확장기능이 없으면 에러 날 수 있음 -> 예외처리됨
                sql_typo = f"""
                    SELECT note 
                    FROM tb_note_embedding_m 
                    WHERE 1=1 {exclude_sql}
                      AND levenshtein(note, %s) <= 3 
                    ORDER BY levenshtein(note, %s) ASC 
                    LIMIT %s;
                """
                cur.execute(sql_typo, (keyword, keyword, top_k - len(results)))
                results.extend([r[0] for r in cur.fetchall()])
            except Exception:
                conn.rollback() 

        # 3. Vector Search
        if len(results) < top_k:
            query_vector = get_embedding(keyword)
            if query_vector:
                exclude_sql = ""
                if results:
                    formatted = "'" + "','".join([r.replace("'", "''") for r in results]) + "'"
                    exclude_sql = f"AND note NOT IN ({formatted})"
                
                sql_vector = f"""
                    SELECT note 
                    FROM tb_note_embedding_m 
                    WHERE 1=1 {exclude_sql}
                    ORDER BY embedding <=> %s::vector 
                    LIMIT %s;
                """
                cur.execute(sql_vector, (query_vector, top_k - len(results)))
                results.extend([r[0] for r in cur.fetchall()])
            
        conn.close()
        return list(set(results))

    except Exception:
        print(f"⚠️ Note Search Error: {keyword}", flush=True)
        traceback.print_exc()
        return []

# tools.py 내부 execute_precise_search 함수 전체 교체

def execute_precise_search(filters: list[dict]) -> str | None:
    if not filters:
        return None

    # --- 쿼리 실행 내부 함수 ---
    def _run_query(current_filters):
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=DictCursor)
            where_clauses, params = [], []
            
            for f in current_filters:
                col = f.get("column", "").lower().strip()
                val = f.get("value")
                if not col or not val: continue

                if col == "brand":
                    where_clauses.append("AND b.perfume_brand ILIKE %s")
                    params.append(val)
                elif col in ["perfume_name", "name"]:
                    where_clauses.append("AND b.perfume_name ILIKE %s")
                    params.append(f"%{val}%")
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

            # 테이블명: aud_m, oca_m 반영됨
            sql = f"""
                SELECT 
                    b.perfume_id, b.perfume_name, b.perfume_brand, b.img_link, b.perfumer, b.release_year,
                    (SELECT json_agg(json_build_object('name', sub_n.note, 'type', sub_n.type)) FROM tb_perfume_notes_m sub_n WHERE sub_n.perfume_id = b.perfume_id) as notes_json,
                    (SELECT json_agg(json_build_object('name', sub_ac.accord, 'vote', sub_ac.vote)) FROM tb_perfume_accord_m sub_ac WHERE sub_ac.perfume_id = b.perfume_id) as accords_json,
                    (SELECT json_agg(json_build_object('name', sub_s.season, 'vote', sub_s.vote)) FROM tb_perfume_season_m sub_s WHERE sub_s.perfume_id = b.perfume_id) as season_json,
                    (SELECT json_agg(json_build_object('name', sub_a.audience, 'vote', sub_a.vote)) FROM tb_perfume_aud_m sub_a WHERE sub_a.perfume_id = b.perfume_id) as gender_json,
                    (SELECT json_agg(json_build_object('name', sub_o.occasion, 'vote', sub_o.vote)) FROM tb_perfume_oca_m sub_o WHERE sub_o.perfume_id = b.perfume_id) as occasion_json
                FROM tb_perfume_basic_m b
                LEFT JOIN tb_perfume_notes_m n ON b.perfume_id = n.perfume_id
                LEFT JOIN tb_perfume_accord_m ac ON b.perfume_id = ac.perfume_id
                LEFT JOIN tb_perfume_season_m s ON b.perfume_id = s.perfume_id
                LEFT JOIN tb_perfume_aud_m a ON b.perfume_id = a.perfume_id
                LEFT JOIN tb_perfume_oca_m o ON b.perfume_id = o.perfume_id
                WHERE 1=1 {' '.join(where_clauses)}
                GROUP BY b.perfume_id
                ORDER BY RANDOM()
                LIMIT 5;
            """
            cur.execute(sql, tuple(params))
            return cur.fetchall()
        except:
            traceback.print_exc()
            return None
        finally:
            if conn: conn.close()

    # =========================================================================
    # [Step 1] Strict Search: 모든 조건(브랜드,노트,어코드,계절,상황) 포함
    # =========================================================================
    print(f"\n🔎 [Step 1] Strict: {filters}", flush=True)
    results = _run_query(filters)
    search_mode = "strict"

    # =========================================================================
    # [Step 2] Relaxed Context: 계절/상황 제거 (핵심인 노트/어코드는 유지)
    # =========================================================================
    if not results:
        # 1차 완화: Season, Occasion 제거 -> 향기는 유지
        context_columns = ['season', 'occasion']
        filters_step2 = [f for f in filters if f['column'] not in context_columns]
        
        if len(filters_step2) < len(filters):
            print(f"⚠️ [Step 2] Ignore Context: {filters_step2}", flush=True)
            results = _run_query(filters_step2)
            search_mode = "relaxed_context"

            # =========================================================================
            # [Step 3] Broad Scent: 구체적 노트 제거 -> 분위기(Accord) 유지 [★핵심]
            # 예: 'Soap' 노트가 없으면 -> 'Clean', 'Musk' 어코드인 향수를 찾음
            # =========================================================================
            if not results:
                # 2차 완화: Note 제거, Accord는 유지
                filters_step3 = [f for f in filters_step2 if f['column'] != 'note']
                
                # Accord 조건이 남아있을 때만 실행 (분위기는 맞춰줘야 하므로)
                has_accord = any(f['column'] == 'accord' for f in filters_step3)
                if len(filters_step3) < len(filters_step2) and has_accord:
                    print(f"⚠️ [Step 3] Broad Scent (Accord Only): {filters_step3}", flush=True)
                    results = _run_query(filters_step3)
                    search_mode = "broad_scent"

                # =========================================================================
                # [Step 4] Emergency: 어코드도 없으면 -> 브랜드 베스트셀러
                # =========================================================================
                if not results:
                    filters_step4 = [f for f in filters_step2 if f['column'] in ['brand', 'gender']]
                    if any(f['column'] == 'brand' for f in filters_step4):
                        print(f"🚨 [Step 4] Emergency (Brand Only): {filters_step4}", flush=True)
                        results = _run_query(filters_step4)
                        search_mode = "emergency"

    if not results:
        return None

    # 결과 메시지 조합
    result_txt = ""
    if search_mode == "relaxed_context":
        result_txt += "🚨 (계절/상황 조건이 맞지 않아, 향기(노트/분위기) 위주로 검색했습니다)\n\n"
    elif search_mode == "broad_scent":
        result_txt += "🚨 (정확한 노트가 없어, 비슷한 분위기(Accord)의 향수를 추천합니다)\n\n"
    elif search_mode == "emergency":
        result_txt += "🚨 (원하시는 향 정보를 찾을 수 없어, 해당 브랜드의 대표 향수를 보여드립니다)\n\n"

    for i, r in enumerate(results, 1):
        clean_accords = filter_by_votes(r['accords_json'], threshold_ratio=0.10)
        clean_seasons = filter_by_votes(r['season_json'], threshold_ratio=0.15)
        clean_gender = filter_by_votes(r['gender_json'], threshold_ratio=0.10)
        clean_occasion = filter_by_votes(r['occasion_json'], threshold_ratio=0.10)
        formatted_notes = format_notes(r['notes_json'])

        result_txt += f"no.{i}\n"
        result_txt += f"브랜드: {r['perfume_brand']}\n"
        result_txt += f"이름: {r['perfume_name']}\n"
        result_txt += f"이미지: {r['img_link']}\n"
        result_txt += f"성별: {clean_gender}\n"
        result_txt += f"분위기: {clean_accords}\n"
        result_txt += f"계절: {clean_seasons}\n"
        result_txt += f"상황: {clean_occasion}\n"
        result_txt += f"노트 구성:\n{formatted_notes}\n"
        result_txt += "-" * 25 + "\n"

    return result_txt