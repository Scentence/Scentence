import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import os

CSV_PATH = "routputs/TB_PERFUME_GENDER_R.csv"
TABLE_NAME = "TB_PERFUME_GENDER_R"
BATCH_SIZE = 1000

DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5433"),
}


def load_data():
    if not os.path.exists(CSV_PATH):
        print(f"[SKIP] {CSV_PATH} 파일을 찾을 수 없음")
        return
    df = pd.read_csv(CSV_PATH)
    if df.empty:
        return
    records = df.to_dict(orient="records")
    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (PERFUME_ID, GENDER, LOAD_DT)
        VALUES (%(PERFUME_ID)s, %(GENDER)s, %(LOAD_DT)s)
        ON CONFLICT (PERFUME_ID)
        DO UPDATE SET GENDER = EXCLUDED.GENDER, LOAD_DT = EXCLUDED.LOAD_DT
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn:
            with conn.cursor() as cur:
                execute_batch(cur, insert_sql, records, page_size=BATCH_SIZE)
        print(f"[OK] {TABLE_NAME} 적재 완료 ({len(records)}건)")
    finally:
        conn.close()


if __name__ == "__main__":
    load_data()
