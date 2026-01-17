# database.py
import os
import psycopg2
from dotenv import load_dotenv
import json

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


def get_recent_messages(limit=10) -> list:
    """
    [메모리 로드] 최근 대화 10개를 가져와서 LangChain Message 포맷으로 변환
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 테이블 이름(tb_chat_logs)은 실제 DB에 맞게 수정 필요
        # 없다면: CREATE TABLE tb_chat_logs (id SERIAL PRIMARY KEY, role VARCHAR(20), content TEXT, created_at TIMESTAMP DEFAULT NOW());
        sql = """
            SELECT role, content 
            FROM tb_chat_logs 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        conn.close()

        # 최신순(DESC)으로 가져왔으니 -> 시간순(ASC)으로 뒤집어야 대화 흐름이 맞음
        history = [{"role": r[0], "content": r[1]} for r in rows][::-1]
        return history
    except Exception as e:
        print(f"⚠️ 히스토리 로딩 실패 (테이블이 없거나 DB 에러): {e}")
        return []


def save_chat_log(role: str, content: str):
    """
    [메모리 저장] 대화 내용을 DB에 저장
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = "INSERT INTO tb_chat_logs (role, content, created_at) VALUES (%s, %s, NOW())"
        cur.execute(sql, (role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ 채팅 저장 실패: {e}")
