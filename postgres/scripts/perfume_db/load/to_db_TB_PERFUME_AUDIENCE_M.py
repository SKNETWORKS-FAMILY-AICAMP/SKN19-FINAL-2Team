import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

CSV_PATH = "outputs/TB_PERFUME_AUDIENCE_M.csv"
TABLE_NAME = "TB_PERFUME_AUD_M"
BATCH_SIZE = 1000

DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": "localhost",
    "port": "5433"
}


def load_data():

    df = pd.read_csv(CSV_PATH)

    if df.empty:
        print(f"[SKIP] {CSV_PATH} 비었음")
        return

    records = df.to_dict(orient="records")

    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            PERFUME_ID,
            AUDIENCE,
            VOTE,
            LOAD_DT
        )
        VALUES (
            %(PERFUME_ID)s,
            %(AUDIENCE)s,
            %(VOTE)s,
            %(LOAD_DT)s
        )
        ON CONFLICT (PERFUME_ID, AUDIENCE)
        DO UPDATE SET
            VOTE    = EXCLUDED.VOTE,
            LOAD_DT = EXCLUDED.LOAD_DT
    """

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn: 
            with conn.cursor() as cur:
                execute_batch(
                    cur,
                    insert_sql,
                    records,
                    page_size=BATCH_SIZE
                )

        print(f"[OK] {TABLE_NAME} 적재 완료 ({len(records)}건)")

    except Exception as e:
        print(f"[FAIL] 적재 실패: {e}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    load_data()