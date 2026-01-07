import psycopg2
import openai
import os
from tqdm import tqdm
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
    """
    OpenAI text-embedding-3-small 모델을 사용하여 1536차원 벡터 생성
    """
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def generate_rich_description(row):
    """
    DB의 정형 데이터를 LLM이 이해하기 쉬운 '자연어 문장'으로 변환합니다.
    검색 시 '여름 향수', '데일리 향수' 같은 키워드와 매칭되도록 
    계절, 상황, 성별 정보를 문장에 자연스럽게 녹여냅니다.
    """
    # load_perfumes.py에서 저장한 컬럼 순서에 맞춰 인덱싱
    # 0:id, 1:ext_id, 2:name, 3:brand, 4:gender, 5:season, 6:occasion, 7:top, 8:mid, 9:base, 10:accords, 11:img, 12:full_data
    
    p_id = row[0]
    name = row[2]
    brand = row[3]
    gender = row[4]    # Feminine, Masculine
    season = row[5]    # Winter, Summer
    occasion = row[6]  # Daily, Night Out
    top_note = row[7]
    mid_note = row[8]
    base_note = row[9]
    accords = row[10]  # Citrus, Fresh (상위 3개까지만)
    
    # 1. 기본 식별 정보
    desc = f"'{name}' is a perfume created by the brand '{brand}'."
    
    # 2. 어코드
    if accords:
        desc += f" It represents {accords} accords."
    
    # 3. 상황/맥락

    context_parts = []
    if gender:
        context_parts.append(f"suitable for {gender}")
    if season:
        context_parts.append(f"perfect for {season}")
    if occasion:
        context_parts.append(f"recommended for {occasion} use")
        
    if context_parts:
        # 예시: "It is suitable for Feminine, perfect for Spring, and recommended for Daily use."
        desc += " It is " + ", and ".join(context_parts) + "."

    # 4. 상세 노트 정보
    notes_desc = []
    if top_note: notes_desc.append(f"top notes of {top_note}")
    if mid_note: notes_desc.append(f"middle notes of {mid_note}")
    if base_note: notes_desc.append(f"base notes of {base_note}")
    
    if notes_desc:
        desc += " The scent profile features " + ", ".join(notes_desc) + "."

    return desc

def embed_and_store():
    print("🔌 Connecting to Database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 이미 임베딩된 데이터는 건너뜀
    print("🔍 Checking for new perfumes to embed...")
    cur.execute("""
        SELECT m.* FROM perfume_metadata m
        LEFT JOIN perfume_embeddings e ON m.id = e.perfume_id
        WHERE e.perfume_id IS NULL
    """)
    rows = cur.fetchall()
    
    total_count = len(rows)
    print(f"🚀 Found {total_count} perfumes to process.")
    
    if total_count == 0:
        print("All perfumes are already embedded.")
        return

    for row in tqdm(rows, desc="Embedding"):
        p_id = row[0]
        
        description = generate_rich_description(row)
        
        try:
            vector = get_embedding(description)
            
            cur.execute("""
                INSERT INTO perfume_embeddings (perfume_id, description, embedding)
                VALUES (%s, %s, %s)
            """, (p_id, description, vector))
            
        except Exception as e:
            print(f"\n⚠️ Error processing ID {p_id}: {e}")
            continue
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅ Successfully embedded and stored {total_count} perfumes.")

if __name__ == "__main__":
    embed_and_store()