# -*- coding: utf-8 -*- 
import os
import json
import re
import psycopg2
from psycopg2.extras import DictCursor
from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. DB 설정
# ==========================================
DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433") 
}

client = OpenAI()

# ==========================================
# 2. 유틸리티 & 메타데이터
# ==========================================
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def safe_json_parse(text: str, default=None):
    if not text or not text.strip(): return default
    try:
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text).strip()
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else json.loads(text)
    except:
        return default

def get_embedding(text):
    return client.embeddings.create(input=text.replace("\n", " "), model="text-embedding-3-small").data[0].embedding

def load_metadata_from_db():
    print("🔄 [System] DB에서 메타데이터 로딩 중...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        tables = {
            "SEASONS": ("tb_perfume_season_m", "season"),
            "GENDERS": ("tb_perfume_aud_m", "audience"),
            "OCCASIONS": ("tb_perfume_oca_m", "occasion"),
            "ACCORDS": ("tb_perfume_accord_m", "accord")
        }
        meta = {}
        for key, (tbl, col) in tables.items():
            cur.execute(f"SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL")
            meta[key] = [r[0] for r in cur.fetchall()]
        conn.close()
        return meta
    except:
        return {"SEASONS": [], "GENDERS": [], "OCCASIONS": [], "ACCORDS": []}

METADATA = load_metadata_from_db()

# ==========================================
# 3. 도구 (Tools)
# ==========================================

def search_notes_smart(keyword: str) -> list[str]:
    """하이브리드 노트 검색 (Text + Vector)"""
    results = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Text Search
        clean_keyword = keyword.replace("향", "").strip()
        cur.execute("SELECT note FROM tb_note_embedding_m WHERE note ILIKE %s LIMIT 3", (f"%{clean_keyword}%",))
        results.extend([r[0] for r in cur.fetchall()])
        
        # 2. Vector Search (부족할 경우)
        if len(results) < 3:
            query_vector = get_embedding(keyword)
            exclude_cond = ""
            if results:
                formatted_excludes = "'" + "','".join([r.replace("'", "''") for r in results]) + "'"
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
        cur.execute(f"SELECT {col} FROM {table} WHERE {col} ILIKE %s LIMIT 1", (f"%{keyword}%",))
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
    if not filters: return "검색 조건을 추출하지 못했습니다."
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    while True:
        print(f"\n🔄 [DB] 검색 시도: {[f['column'] + '=' + str(f['value']) for f in filters]}")
        
        where_clauses = []
        params = []
        
        # 1. WHERE 조건절 동적 생성
        for f in filters:
            col = f['column']
            val = f['value']
            
            if col == 'brand': clause = "AND b.perfume_brand ILIKE %s"
            elif col == 'perfume_name': clause = "AND b.perfume_name ILIKE %s"
            elif col == 'note': 
                if isinstance(val, list) and val:
                    # 노트 목록 중 '하나라도' 포함되면 검색 (OR 조건 느낌의 IN)
                    # 주의: JOIN 후 필터링하면 해당 노트만 남을 수 있으므로, 
                    # 정확한 스펙을 위해서는 Subquery가 좋지만 성능상 여기서는 JOIN 필터 사용
                    clause = f"AND n.note IN ({','.join(['%s']*len(val))})"
                    where_clauses.append(clause)
                    params.extend(val)
                    continue
                else: clause = "AND n.note = %s"
            elif col == 'season': clause = "AND s.season = %s"
            elif col == 'gender': clause = "AND a.audience = %s"
            elif col == 'occasion': clause = "AND o.occasion = %s"
            elif col == 'accord': clause = "AND ac.accord = %s"
            else: continue
            
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

# ==========================================
# 4. State & Nodes
# ==========================================
class State(TypedDict):
    user_query: str
    route: Literal["interviewer", "researcher", "writer"]
    clarified_query: str | None
    research_result: str | None
    final_response: str

def supervisor(state: State) -> State:
    return {"route": "researcher"} # 편의상 고정 (테스트용)

def researcher(state: State) -> State:
    query = state.get("clarified_query") or state["user_query"]
    print(f"\n🕵️ [Researcher] 검색 설계 시작: '{query}'")
    
    prompt = f"""
    당신은 SQL 검색 조건을 설계하는 전문가입니다.
    사용자 질문: "{query}"
    DB 메타데이터: {json.dumps(METADATA, indent=2, ensure_ascii=False)}
    
    [규칙]
    1. 'filters'에 SQL 조건을 담되, **중요한 조건 순서대로** 배치하세요.
    2. **[필수] 노트(향) 키워드는 반드시 영어(English)로 번역해서 'note_keywords'에 담으세요.** (예: 레몬->Lemon, 흙->Earth, 장미->Rose)
    3. 브랜드/향수 이름은 'entity_keyword'에 담으세요.
    
    응답(JSON):
    {{
        "filters": [ {{ "column": "accord", "value": "Citrus" }} ],
        "note_search_needed": true,
        "note_keywords": ["Lemon"], 
        "entity_search_needed": false
    }}
    """
    try:
        msg = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}], 
            response_format={"type": "json_object"}
        )
        plan = safe_json_parse(msg.choices[0].message.content)
        
        final_filters = []
        if plan.get("entity_search_needed"):
            ex_name = search_exact_entity_name(plan["entity_keyword"], plan.get("entity_type", "brand"))
            if ex_name: final_filters.insert(0, {"column": "brand", "value": ex_name})
            
        if plan.get("note_search_needed"):
            notes = []
            for k in plan.get("note_keywords", []):
                notes.extend(search_notes_smart(k))
            if notes: final_filters.append({"column": "note", "value": list(set(notes))})
            
        for f in plan.get("filters", []):
            final_filters.append(f)
            
        result = execute_search_with_fallback(final_filters)
    except Exception as e:
        result = f"오류 발생: {e}"
        
    return {"research_result": result, "route": "writer"}

def writer(state: State) -> State:
    print("\n✍️ [Writer] 답변 생성 중...")
    prompt = f"""
    당신은 전문 조향사입니다. 아래 [DB 검색 결과]를 바탕으로 추천 답변을 작성하세요.
    
    [사용자 질문]: {state['user_query']}
    [DB 검색 결과]: 
    {state.get('research_result')}
    
    [지침]
    1. **DB에서 찾은 정보(노트, 어코드, 분위기 등)를 상세히 인용하여 설명하세요.**
    2. 단순히 나열하지 말고, "이 향수는 ~한 노트가 어우러져 ~한 느낌을 줍니다" 처럼 스토리텔링 하세요.
    3. 검색된 향수가 없다면 솔직히 말하고 대안을 제시하세요.
    """
    msg = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
    return {"final_response": msg.choices[0].message.content}

def build_graph():
    graph = StateGraph(State)
    graph.add_node("supervisor", supervisor)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)
    return graph.compile()