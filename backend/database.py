# database.py
import os
import psycopg2
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
    "port": os.getenv("DB_PORT", "5433"),
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_metadata_from_db():
    print("🔄 [System] DB에서 메타데이터 로딩 중...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        tables = {
            "SEASONS": ("tb_perfume_season_m", "season"),
            "GENDERS": ("tb_perfume_aud_m", "audience"),
            "OCCASIONS": ("tb_perfume_oca_m", "occasion"),
            "ACCORDS": ("tb_perfume_accord_m", "accord"),
        }
        meta = {}
        for key, (tbl, col) in tables.items():
            cur.execute(f"SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL")
            meta[key] = [r[0] for r in cur.fetchall()]
        conn.close()
        return meta
    except:
        return {"SEASONS": [], "GENDERS": [], "OCCASIONS": [], "ACCORDS": []}


# 모듈 로드 시 실행
METADATA = load_metadata_from_db()
