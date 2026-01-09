import os
import json
import psycopg2
from psycopg2.extras import execute_batch

# ==========================================
# 1. 파일 경로 및 DB 설정
# ==========================================
# 현재 파일(load_note_vectors.py)의 위치 기준
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# JSON 파일 경로: /backend/script/vectorDB/raw/notes_vector_db_ready.json
JSON_FILE_PATH = os.path.join(CURRENT_DIR, "raw", "notes_vector_db_ready.json")

# DB 접속 설정 (로컬 실행 시 localhost:5433, 도커 내부 실행 시 db:5432)
DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433") 
}

TABLE_NAME = "tb_note_embedding_m"

def load_vector_data():
    print("🚀 노트 임베딩 데이터 적재 시작")
    
    # 1. JSON 파일 읽기
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ 파일을 찾을 수 없습니다: {JSON_FILE_PATH}")
        return

    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"📂 JSON 로드 완료: {len(data)}개 데이터")
    except Exception as e:
        print(f"❌ JSON 읽기 실패: {e}")
        return

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. 테이블 생성 (vector 컬럼 포함!)
        # note 컬럼에 UNIQUE 제약조건을 걸어 중복 적재를 방지합니다.
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                note TEXT NOT NULL UNIQUE,
                description TEXT,
                embedding vector(1536),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cur.execute(create_table_sql)
        print("✅ 테이블 생성/확인 완료 (embedding vector(1536) 포함)")

        # 3. 데이터 적재 (Batch Insert)
        insert_sql = f"""
            INSERT INTO {TABLE_NAME} (note, description, embedding)
            VALUES (%s, %s, %s)
            ON CONFLICT (note) 
            DO UPDATE SET
                description = EXCLUDED.description,
                embedding = EXCLUDED.embedding;
        """

        # JSON 데이터를 튜플 리스트로 변환
        records = []
        for item in data:
            # item['semantic_vector']가 리스트인지 확인
            vector = item.get('semantic_vector')
            if not vector or len(vector) != 1536:
                print(f"⚠️ 경고: {item.get('note')}의 벡터 차원이 1536이 아닙니다. 건너뜁니다.")
                continue
                
            records.append((
                item.get('note'),
                item.get('description'),
                vector  # 리스트 그대로 넘기면 pgvector가 알아서 처리함
            ))

        if records:
            execute_batch(cur, insert_sql, records)
            conn.commit()
            print(f"🎉 데이터 적재 완료: 총 {len(records)}건")
        else:
            print("⚠️ 적재할 유효한 데이터가 없습니다.")

        # 4. 확인 (Count)
        cur.execute(f"SELECT count(*) FROM {TABLE_NAME};")
        cnt = cur.fetchone()[0]
        print(f"📊 현재 DB 저장된 개수: {cnt}개")

    except Exception as e:
        print(f"❌ DB 작업 중 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    load_vector_data()