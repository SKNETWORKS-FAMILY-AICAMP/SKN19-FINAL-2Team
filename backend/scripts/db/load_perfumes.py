import json
import psycopg2
import ast

DB_CONFIG = {
    "dbname": "scentence_db",
    "user": "scentence",
    "password": "scentence",
    "host": "localhost",
    "port": "5433"
}

def create_metadata_table(cursor):
    """
    하이브리드 검색(필터링)을 위해 세부 컬럼을 추가하여 테이블을 생성합니다.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfume_metadata (
            id INTEGER PRIMARY KEY,
            external_id TEXT,
            name TEXT,
            brand TEXT,
            gender TEXT,        -- audience 1위 (예: Masculine, Feminine)
            main_season TEXT,   -- season 1위 (예: Winter)
            main_occasion TEXT, -- occasion 1위 (예: Daily)
            top_notes TEXT,
            middle_notes TEXT,
            base_notes TEXT,
            top_accords TEXT,
            image_url TEXT,     -- 이미지 URL도 저장 (프론트 표시용)
            full_data JSONB,    -- 원본 데이터 백업
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- 검색 속도를 위해 브랜드, 성별 등에 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_brand ON perfume_metadata(brand);
        CREATE INDEX IF NOT EXISTS idx_gender ON perfume_metadata(gender);
    """)

def parse_dict_str_get_top(dict_str, top_k=1):
    """
    문자열 형태의 딕셔너리에서 투표수 상위 k개를 추출합니다.
    k=1이면 문자열 반환, k>1이면 리스트 반환.
    """
    if not dict_str:
        return None if top_k == 1 else []
    
    try:
        data_dict = ast.literal_eval(dict_str)
        if not data_dict:
            return None if top_k == 1 else []

        # 투표수 기준 내림차순
        sorted_items = sorted(
            data_dict.items(), 
            key=lambda item: int(item[1]) if item[1] else 0, 
            reverse=True
        )
        
        top_items = [k for k, v in sorted_items[:top_k]]
        
        if top_k == 1:
            return top_items[0] if top_items else None
        return top_items
    except Exception as e:
        return None if top_k == 1 else []

def parse_perfume_id(p_id_str):
    try:
        return int(p_id_str.split('_')[1])
    except:
        return None

def load_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    create_metadata_table(cur)
    conn.commit()
    
    print("Start loading data...")
    count = 0
    
    with open("perfume_info.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                p_id = parse_perfume_id(data.get("perfume_id"))
                if not p_id: continue

                # 1. 데이터 파싱
                # Accords는 상위 3개 (임베딩 설명용)
                top_accords = parse_dict_str_get_top(data.get("accord"), top_k=3)
                
                # 나머지(성별, 계절, 상황)는 필터링용으로 상위 1개만 추출
                main_gender = parse_dict_str_get_top(data.get("audience"), top_k=1)
                main_season = parse_dict_str_get_top(data.get("season"), top_k=1)
                main_occasion = parse_dict_str_get_top(data.get("occasion"), top_k=1)

                # 2. DB 적재
                cur.execute("""
                    INSERT INTO perfume_metadata 
                    (id, external_id, name, brand, gender, main_season, main_occasion, 
                     top_notes, middle_notes, base_notes, top_accords, image_url, full_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        main_season = EXCLUDED.main_season,
                        image_url = EXCLUDED.image_url
                """, (
                    p_id,
                    data.get("perfume_id"),
                    data.get("perfume"),
                    data.get("brand"),
                    main_gender,
                    main_season,
                    main_occasion,
                    data.get("top_note"),
                    data.get("middle_note"),
                    data.get("base_note"),
                    ", ".join(top_accords),
                    data.get("img"),
                    json.dumps(data)
                ))
                count += 1
                
            except Exception as e:
                print(f"Error processing line: {e}")
                continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully loaded {count} perfumes.")

if __name__ == "__main__":
    load_data()