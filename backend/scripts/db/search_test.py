import os
import psycopg2
from openai import OpenAI

# DB 설정 (위와 동일)
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5433"))
DB_NAME = os.getenv("PGDATABASE", "scentence_db")
DB_USER = os.getenv("PGUSER", "scentence")
DB_PASSWORD = os.getenv("PGPASSWORD", "scentence2026!")

MODEL = "text-embedding-3-small"

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # 테스트할 질문
    query_text = "비 오는 날 뿌리기 좋은 차분한 숲 냄새 향수 추천해줘"
    print(f"질문: {query_text}\n" + "="*50)

    # 1. 질문을 벡터로 변환
    q_resp = client.embeddings.create(model=MODEL, input=query_text)
    q_emb = q_resp.data[0].embedding

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    
    # 2. 유사도 검색 쿼리 (HNSW 인덱스 활용)
    # <=> 연산자는 코사인 거리 (값이 작을수록 유사함)
    sql = """
    SELECT perfume_id, brand, name, description, metadata, 
           (embedding <=> %s::vector) as distance
    FROM perfume_items
    ORDER BY distance ASC
    LIMIT 5
    """

    with conn.cursor() as cur:
        cur.execute(sql, (q_emb,))
        rows = cur.fetchall()

        for i, row in enumerate(rows, 1):
            pid, brand, name, desc, meta, dist = row
            print(f"{i}. [{brand}] {name} (유사도 거리: {dist:.4f})")
            print(f"   - 설명 요약: {desc[:100]}...")
            print(f"   - 계절/상황: {meta.get('season')}, {meta.get('occasion')}")
            print("-" * 50)

    conn.close()

if __name__ == "__main__":
    main()