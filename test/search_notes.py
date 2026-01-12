import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드 (API Key)
load_dotenv()

# ==========================================
# 설정
# ==========================================
DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": "localhost",
    "port": "5433"
}

# 임베딩 모델 (적재할 때 사용한 것과 동일해야 함!)
EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI()

def get_embedding(text):
    """사용자 입력 텍스트를 1536차원 벡터로 변환"""
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=EMBEDDING_MODEL).data[0].embedding

def search_notes(query_text, top_k=5):
    print(f"\n🔎 검색어: '{query_text}'")
    print("🔄 임베딩 변환 중...")
    
    try:
        # 1. 질문을 벡터로 변환
        query_vector = get_embedding(query_text)
        
        # 2. DB 접속 및 검색
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 3. 벡터 유사도 검색 쿼리 (Cosine Distance)
        # <=> 연산자는 '코사인 거리'를 의미합니다. (0에 가까울수록 유사함)
        # 1 - (거리) = 유사도 (1에 가까울수록 유사함)
        sql = """
            SELECT note, description, 1 - (embedding <=> %s::vector) as similarity
            FROM tb_note_embedding_m
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        
        cur.execute(sql, (query_vector, query_vector, top_k))
        results = cur.fetchall()
        
        print(f"\n📊 검색 결과 (Top {top_k})")
        print("="*60)
        
        if not results:
            print("결과가 없습니다.")
        
        for i, row in enumerate(results, 1):
            note = row[0]
            desc = row[1]
            score = row[2]
            
            # 설명이 너무 길면 자르기
            short_desc = (desc[:80] + "...") if desc and len(desc) > 80 else desc
            
            print(f"[{i}] {note} (유사도: {score:.4f})")
            print(f"    설명: {short_desc}")
            print("-" * 60)
            
        conn.close()

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    while True:
        user_input = input("\n향이나 느낌을 입력하세요 (종료: exit): ")
        if user_input.lower() in ["exit", "quit", "종료"]:
            break
        
        if user_input.strip():
            search_notes(user_input)