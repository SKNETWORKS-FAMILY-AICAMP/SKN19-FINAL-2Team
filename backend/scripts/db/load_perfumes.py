# -*- coding: utf-8 -*-
import os
import json
import psycopg2
import sys
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# DB 설정
DB_HOST = "127.0.0.1"
DB_PORT = int(os.getenv("PGPORT", "5433"))
DB_NAME = os.getenv("PGDATABASE", "scentence_db")
DB_USER = os.getenv("PGUSER", "scentence")
DB_PASSWORD = "1234" # 혹은 os.getenv 사용

def connect():
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    except Exception as e:
        print(f"❌ [DB 접속 에러] {e}")
        sys.exit(1)

def create_table_if_not_exists(cursor):
    # vector 확장 및 테이블 생성
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    create_query = """
    CREATE TABLE IF NOT EXISTS perfume_items (
        perfume_id    TEXT PRIMARY KEY,
        brand         TEXT,
        name          TEXT,
        description   TEXT NOT NULL,
        metadata      JSONB,
        embedding     vector(1536), -- 여기는 일단 NULL로 들어갑니다
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );
    """
    cursor.execute(create_query)

def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    file_path = os.path.join(project_root, "data", "perfume_data.jsonl")

    conn = connect()
    cursor = conn.cursor()
    create_table_if_not_exists(cursor)

    print(f"📂 파일 읽기 시작: {file_path}")
    data_to_insert = []
    
    # [핵심 수정] 인코딩 오류 해결 전략
    # 1순위: cp949 (한글 윈도우 기본), 2순위: utf-8
    encodings_to_try = ['cp949', 'utf-8', 'utf-8-sig']
    
    file_content = None
    with open(file_path, 'r', encoding="utf-8") as f:
            file_content = f.readlines()
    # for enc in encodings_to_try:
    #     try:
    #         print(f"   ↳ 인코딩 시도: {enc}...", end=" ")
    #         with open(file_path, 'r', encoding=enc) as f:
    #             file_content = f.readlines()
    #         print("✅ 성공!")
    #         break
    #     except UnicodeDecodeError:
    #         print("❌ 실패")
    #         continue
    
    # if not file_content:
    #     print("❌ [치명적 오류] 모든 인코딩 방식으로도 파일을 읽을 수 없습니다.")
    #     return

    # 데이터 파싱
    for line in file_content:
        if not line.strip(): continue
        try:
            row = json.loads(line)
            embed_text = row.get("embed", "")
            meta_data = row.get("metadata", {})
            perfume_id = str(meta_data.get("id"))
            
            if not perfume_id or perfume_id == "None": continue

            data_to_insert.append((
                perfume_id,
                meta_data.get("Brand"),
                meta_data.get("Name"),
                embed_text,
                json.dumps(meta_data, ensure_ascii=False)
            ))
        except json.JSONDecodeError:
            print(f"   [Warning] JSON 형식이 잘못된 라인이 있습니다.")
            continue

    if not data_to_insert:
        print("[WARNING] 저장할 데이터가 없습니다.")
        return

    print(f"🚀 DB에 {len(data_to_insert)}개 데이터 적재 중...")
    
    insert_query = """
    INSERT INTO perfume_items (perfume_id, brand, name, description, metadata)
    VALUES %s
    ON CONFLICT (perfume_id) DO UPDATE SET
        description = EXCLUDED.description,
        metadata = EXCLUDED.metadata;
    """
    
    try:
        execute_values(cursor, insert_query, data_to_insert)
        conn.commit()
        print(f"[DONE] 데이터 적재 완료! (이제 임베딩 스크립트를 실행하세요)")
    except Exception as e:
        print(f"❌ [DB 저장 실패] {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    load_data()