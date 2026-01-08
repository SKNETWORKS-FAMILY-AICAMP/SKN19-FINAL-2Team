import psycopg2
import openai
import os
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI()

DB_CONFIG = {
    "dbname": "scentence_db",
    "user": "scentence",
    "password": "scentence",
    "host": "localhost",
    "port": "5433"
}

def get_embedding(text):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def search_perfumes(user_query, filters=None, top_k=3):
    """
    사용자 질문(user_query)과 필터(filters)를 받아 가장 유사한 향수를 찾습니다.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. 질문을 벡터로 변환 (Query Embedding)
    query_vector = get_embedding(user_query)
    
    # 2. 기본 SQL 쿼리 작성 (Cosine Distance operator: <=>)
    # 거리가 가까울수록(수치가 작을수록) 유사한 것입니다.
    sql = """
        SELECT m.name, m.brand, m.top_accords, m.main_season, m.gender, 
               (e.embedding <=> %s::vector) as distance
        FROM perfume_embeddings e
        JOIN perfume_metadata m ON e.perfume_id = m.id
        WHERE 1=1
    """
    
    params = [query_vector]

    # 3. 하이브리드 검색: 메타데이터 필터링 적용 (SQL WHERE 절)
    if filters:
        if "season" in filters:
            sql += " AND m.main_season = %s"
            params.append(filters["season"])
        if "gender" in filters:
            sql += " AND m.gender = %s"
            params.append(filters["gender"])
            
    # 4. 정렬 및 제한 (유사도 순)
    sql += " ORDER BY distance ASC LIMIT %s"
    params.append(top_k)

    # 5. 실행
    cur.execute(sql, tuple(params))
    results = cur.fetchall()
    
    conn.close()
    return results

if __name__ == "__main__":
    # === 테스트 시나리오 ===
    
    # 상황 1: 단순 의미 검색 (벡터만 사용)
    # "상쾌하고 시트러스한 향수 찾아줘"
    query1 = "I want a fresh and citrusy perfume that feels energetic."
    print(f"\n🔎 Query 1: {query1}")
    results = search_perfumes(query1, top_k=3)
    
    for r in results:
        print(f" - [{r[1]}] {r[0]} (Season: {r[3]}, Dist: {r[5]:.4f})")
        # 출력예: [Brand] Name (Season: Summer, Dist: 0.1234)

    print("-" * 50)

    # 상황 2: 하이브리드 검색 (벡터 + 필터링)
    # "겨울에 쓸 무거운 우디 향수 추천해줘" (Winter 필터 적용)
    query2 = "I am looking for a heavy woody scent with musk."
    my_filters = {"season": "Winter"} # 실제로는 LLM이 추출할 정보
    
    print(f"\n🔎 Query 2: {query2} (Filter: {my_filters})")
    results = search_perfumes(query2, filters=my_filters, top_k=3)
    
    for r in results:
        print(f" - [{r[1]}] {r[0]} (Season: {r[3]}, Dist: {r[5]:.4f})")