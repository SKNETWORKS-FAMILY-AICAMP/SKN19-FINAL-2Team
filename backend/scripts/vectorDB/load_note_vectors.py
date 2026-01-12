import os
import json
import psycopg2
from psycopg2.extras import execute_batch

# ==========================================
# 1. 파일 경로 및 DB 설정
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# [수정] 확장된 데이터 파일 경로 사용
JSON_FILE_PATH = os.path.join(CURRENT_DIR, "raw", "notes_vector_db_ready_expanded.json")

# DB 접속 정보
DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432")
}

TABLE_NAME = "tb_note_embedding_m"

def load_vector_data():
    print(f"🚀 [Expanded] 노트 임베딩 데이터 적재 시작: {JSON_FILE_PATH}")
    
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

        # [★중요 추가] 0. pgvector 확장 및 테이블 생성 확인
        # 볼륨을 날렸으므로 테이블도 다시 만들어야 합니다.
        print("🛠️ 테이블 및 벡터 확장 확인 중...")
        
        # 벡터 익스텐션 활성화 (혹시 모르니)
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # 테이블 생성
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
        conn.commit()

        # 2. 기존 데이터 초기화 (TRUNCATE)
        print("🧹 기존 데이터 삭제 중 (TRUNCATE)...")
        cur.execute(f"TRUNCATE TABLE {TABLE_NAME};")
        conn.commit()

        # 3. 데이터 적재 (INSERT)
        insert_sql = f"""
            INSERT INTO {TABLE_NAME} (note, description, embedding)
            VALUES (%s, %s, %s);
        """

        records = []
        for item in data:
            note = item.get('note')
            description = item.get('description_en') 
            vector = item.get('embedding')

            if vector is None:
                vector = item.get('semantic_vector')

            if not vector:
                print(f"⚠️ 경고: {note}의 벡터 데이터가 없습니다.")
                continue

            if description is None:
                description = ""

            if isinstance(vector, str):
                try:
                    vector = json.loads(vector)
                except:
                    continue
                
            records.append((note, description, vector))

        if records:
            print(f"🚀 데이터 삽입 시작 ({len(records)}건)...")
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