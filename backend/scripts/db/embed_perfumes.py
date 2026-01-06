import os
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

# 설정
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5433"))
DB_NAME = os.getenv("PGDATABASE", "scentence_db")
DB_USER = os.getenv("PGUSER", "scentence")
DB_PASSWORD = os.getenv("PGPASSWORD", "scentence2026!")

MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

def connect():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY 환경변수가 없습니다.")
        return

    client = OpenAI(api_key=api_key)
    conn = connect()
    cur = conn.cursor()

    while True:
        # 1. 임베딩이 없는 데이터 가져오기
        cur.execute(
            """
            SELECT perfume_id, description
            FROM perfume_items
            WHERE embedding IS NULL
            LIMIT %s
            """,
            (BATCH_SIZE,)
        )
        rows = cur.fetchall()
        
        if not rows:
            print("[DONE] 모든 데이터의 임베딩 변환이 완료되었습니다.")
            break

        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        # 2. OpenAI API 호출
        try:
            resp = client.embeddings.create(model=MODEL, input=texts)
            embeddings = [d.embedding for d in resp.data]
            
            # 3. DB 업데이트
            update_data = list(zip(embeddings, ids))
            execute_values(
                cur,
                """
                UPDATE perfume_items AS p
                SET embedding = v.embedding
                FROM (VALUES %s) AS v(embedding, perfume_id)
                WHERE p.perfume_id = v.perfume_id
                """,
                update_data,
                template="(%s, %s)"
            )
            conn.commit()
            print(f"[OK] {len(ids)}개 향수 임베딩 완료.")
            
        except Exception as e:
            print(f"[ERROR] API 호출 중 오류: {e}")
            break

    conn.close()

if __name__ == "__main__":
    main()