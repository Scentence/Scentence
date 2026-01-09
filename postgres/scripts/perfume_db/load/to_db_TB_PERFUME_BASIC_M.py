import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

CSV_PATH = "outputs/TB_PERFUME_BASIC_M.csv"
TABLE_NAME = "TB_PERFUME_BASIC_M"
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

    df["RELEASE_YEAR"] = (
        pd.to_numeric(df["RELEASE_YEAR"], errors="coerce")  
        .astype("Int64")                                    
        .where(pd.notnull(df["RELEASE_YEAR"]), None) # NaN → None (DB에서는 NULL)
    )

    if df.empty:
        print(f"[SKIP] {CSV_PATH} 비었음")
        return

    records = df.to_dict(orient="records")

    insert_sql = f"""
        INSERT INTO {TABLE_NAME} (
            PERFUME_ID,
            PERFUME_NAME,
            PERFUME_BRAND,
            RELEASE_YEAR,
            CONCENTRATION,
            PERFUMER,
            IMG_LINK,
            LOAD_DT
        )
        VALUES (
            %(PERFUME_ID)s,
            %(PERFUME_NAME)s,
            %(PERFUME_BRAND)s,
            %(RELEASE_YEAR)s,
            %(CONCENTRATION)s,
            %(PERFUMER)s,
            %(IMG_LINK)s,
            %(LOAD_DT)s
        )
        ON CONFLICT (PERFUME_ID)
        DO UPDATE SET
            PERFUME_NAME   = EXCLUDED.PERFUME_NAME,
            PERFUME_BRAND  = EXCLUDED.PERFUME_BRAND,
            RELEASE_YEAR   = EXCLUDED.RELEASE_YEAR,
            CONCENTRATION  = EXCLUDED.CONCENTRATION,
            PERFUMER       = EXCLUDED.PERFUMER,
            IMG_LINK       = EXCLUDED.IMG_LINK,
            LOAD_DT        = EXCLUDED.LOAD_DT
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

# import pandas as pd
# df = pd.read_csv("outputs/TB_PERFUME_BASIC_M.csv")

# print(df["PERFUME_ID"].max())
# print(df["RELEASE_YEAR"].max())

# print(df["PERFUME_ID"].min())
# print(df["RELEASE_YEAR"].min())

# df["RELEASE_YEAR"] = (
#     pd.to_numeric(df["RELEASE_YEAR"], errors="coerce")
#     .astype("Int64")
#     .where(pd.notnull(df["RELEASE_YEAR"]), None)
# )
# print(df[df["RELEASE_YEAR"].isna()])