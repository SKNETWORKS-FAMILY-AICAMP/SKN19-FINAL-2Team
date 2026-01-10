import re
import json
import traceback
from openai import OpenAI
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
# 2. 데이터 가공 헬퍼 함수 (핵심 업그레이드)
# ==========================================
def filter_by_votes(data_list: list, threshold_ratio=0.10) -> str:
    """
    JSON 리스트([{'name': 'A', 'vote': 100}, ...])를 받아
    총 투표수의 일정 비율(예: 10%) 이상인 항목만 남기고, 투표순으로 정렬하여 문자열로 반환
    """
    if not data_list:
        return "정보 없음"
    
    # 투표수가 없는 경우(None) 0으로 처리하며 데이터 정제
    clean_list = []
    for item in data_list:
        if not item: continue
        name = item.get('name')
        vote = item.get('vote')
        if not name: continue
        clean_list.append({'name': name, 'vote': int(vote) if vote else 0})

    if not clean_list:
        return "정보 없음"

    # 총 투표수 계산
    total_votes = sum(item['vote'] for item in clean_list)
    
    # 투표 데이터가 아예 없으면(전부 0) 그냥 상위 5개만 보여줌
    if total_votes == 0:
        return ", ".join([i['name'] for i in clean_list[:5]])

    # 비율 필터링 (threshold_ratio 이상만 생존)
    filtered = [
        item for item in clean_list 
        if (item['vote'] / total_votes) >= threshold_ratio
    ]
    
    # 투표 많은 순 정렬
    filtered.sort(key=lambda x: x['vote'], reverse=True)
    
    # 필터링 결과가 너무 엄격해서 다 사라졌으면, 1등이라도 리턴
    if not filtered and clean_list:
        clean_list.sort(key=lambda x: x['vote'], reverse=True)
        return clean_list[0]['name']

    return ", ".join([f"{item['name']}" for item in filtered])

def format_notes(note_list: list) -> str:
    """
    노트 리스트([{'name': 'Rose', 'type': 'Top'}, ...])를 받아
    Top / Middle / Base 로 나누어 문자열로 반환
    """
    if not note_list:
        return "정보 없음"
    
    top, mid, base, unknown = [], [], [], []
    
    for item in note_list:
        if not item: continue
        n_type = str(item.get('type', '')).lower()
        name = item.get('name', '')
        if not name: continue
        
        if 'top' in n_type: top.append(name)
        elif 'middle' in n_type or 'heart' in n_type: mid.append(name)
        elif 'base' in n_type or 'bottom' in n_type: base.append(name)
        else: unknown.append(name)
        
    result = []
    if top: result.append(f"   - Top: {', '.join(top)}")
    if mid: result.append(f"   - Middle: {', '.join(mid)}")
    if base: result.append(f"   - Base: {', '.join(base)}")
    # 타입 정보가 없는 경우 기타로 분류
    if unknown: result.append(f"   - Notes: {', '.join(unknown)}")
    
    return "\n".join(result) if result else "정보 없음"


# ==========================================
# 3. 검색 도구 (Tools)
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
        print(f"⚠️ Note Search Error: {keyword}", flush=True)
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
        print(f"⚠️ Entity Search Error: {keyword}", flush=True)
        traceback.print_exc()
        return None

def execute_precise_search(filters: list[dict]) -> str | None:
    """
    필터 조건에 맞춰 향수를 검색하고, 투표수 기반으로 정제된 상세 정보를 반환합니다.
    """
    if not filters:
        return None
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        where_clauses = []
        params = []
        
        print(f"\n🔍 [DB 검색 요청 필터]: {filters}", flush=True)
        
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
            print(f"   👉 [{readable_col}]: {val}", flush=True)
            valid_filters = True

            # SQL WHERE절 조립
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
            print("   ⚠️ 유효한 필터가 없어 검색을 중단합니다.", flush=True)
            return None

        # 👇 [핵심 변경] 데이터를 JSON으로 뭉쳐서 가져오는 SQL
        # 중복 방지를 위해 서브쿼리와 GROUP BY를 사용합니다.
        sql = f"""
            SELECT 
                b.perfume_id,
                b.perfume_name, 
                b.perfume_brand,
                b.img_link,
                b.perfumer,
                b.release_year,
                
                -- 노트 정보 (Type 포함)
                (
                    SELECT json_agg(json_build_object('name', sub_n.note, 'type', sub_n.type))
                    FROM tb_perfume_notes_m sub_n
                    WHERE sub_n.perfume_id = b.perfume_id
                ) as notes_json,

                -- 어코드 정보 (Vote 포함)
                (
                    SELECT json_agg(json_build_object('name', sub_ac.accord, 'vote', sub_ac.vote))
                    FROM tb_perfume_accord_m sub_ac
                    WHERE sub_ac.perfume_id = b.perfume_id
                ) as accords_json,

                -- 계절 정보 (Vote 포함)
                (
                    SELECT json_agg(json_build_object('name', sub_s.season, 'vote', sub_s.vote))
                    FROM tb_perfume_season_m sub_s
                    WHERE sub_s.perfume_id = b.perfume_id
                ) as season_json,
                
                -- 성별 정보 (Vote 포함)
                (
                    SELECT json_agg(json_build_object('name', sub_a.audience, 'vote', sub_a.vote))
                    FROM tb_perfume_aud_m sub_a
                    WHERE sub_a.perfume_id = b.perfume_id
                ) as gender_json,

                -- 상황(Occasion) 정보 (Vote 포함)
                (
                    SELECT json_agg(json_build_object('name', sub_o.occasion, 'vote', sub_o.vote))
                    FROM tb_perfume_oca_m sub_o
                    WHERE sub_o.perfume_id = b.perfume_id
                ) as occasion_json

            FROM tb_perfume_basic_m b
            -- 검색 필터링을 위한 조인 (데이터 조회용이 아님, WHERE절을 위해 필요)
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
        
        # 실행될 쿼리 확인용 로그 (필요시 주석 해제)
        # print(f"\n📝 [Executed SQL]:\n{sql}", flush=True)
        # print(f"📝 [Parameters]: {tuple(params)}\n", flush=True)
        
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        
        if not rows:
            return None
            
        result_txt = ""
        for i, r in enumerate(rows, 1):
            # Python에서 데이터 가공 (필터링 및 구조화)
            clean_accords = filter_by_votes(r['accords_json'], threshold_ratio=0.10) # 10% 미만 제거
            clean_seasons = filter_by_votes(r['season_json'], threshold_ratio=0.15)  # 계절은 조금 더 엄격하게
            clean_gender = filter_by_votes(r['gender_json'], threshold_ratio=0.10)
            clean_occasion = filter_by_votes(r['occasion_json'], threshold_ratio=0.10)
            formatted_notes = format_notes(r['notes_json'])

            # 최종 텍스트 조립
            result_txt += f"no.{i}\n"
            result_txt += f"브랜드: {r['perfume_brand']}\n"
            result_txt += f"이름: {r['perfume_name']}\n"
            result_txt += f"이미지: {r['img_link']}\n"
            result_txt += f"조향사: {r['perfumer'] or '정보 없음'}\n"
            result_txt += f"출시: {r['release_year'] or '?'}\n"
            result_txt += f"성별: {clean_gender}\n"
            result_txt += f"분위기(Accord): {clean_accords}\n"
            result_txt += f"상황(TPO): {clean_occasion}\n"
            result_txt += f"계절: {clean_seasons}\n"
            result_txt += f"노트 구성:\n{formatted_notes}\n"
            result_txt += "-" * 20 + "\n"
            
        return result_txt
        
    except Exception:
        print("⚠️ SQL Execution Error", flush=True)
        traceback.print_exc()
        return None
    finally:
        if conn: conn.close()