# backend/database.py
import os
import traceback
import json
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI

# 오탈자 보정 라이브러리
try:
    from Levenshtein import distance
except ImportError:

    def distance(s1, s2):
        return 0 if s1 == s2 else 100


load_dotenv()

# ==========================================
# 0. 설정 및 초기화
# ==========================================
DB_CONFIG = {
    "dbname": "perfume_db",
    "user": "scentence",
    "password": "scentence",
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433"),
}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 브랜드 목록 캐싱
BRAND_CACHE = []


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_embedding(text: str) -> List[float]:
    try:
        if not text:
            return []
        return (
            client.embeddings.create(
                input=text.replace("\n", " "), model="text-embedding-3-small"
            )
            .data[0]
            .embedding
        )
    except Exception as e:
        print(f"⚠️ Embedding Error: {e}")
        return []


# ==========================================
# 1. 브랜드명 자동 보정 함수
# ==========================================
def get_all_brands() -> List[str]:
    """DB에 존재하는 모든 브랜드 목록을 가져옵니다 (캐싱 적용)"""
    global BRAND_CACHE
    if BRAND_CACHE:
        return BRAND_CACHE

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT perfume_brand FROM TB_PERFUME_BASIC_M")
        BRAND_CACHE = [r[0] for r in cur.fetchall() if r[0]]
        return BRAND_CACHE
    finally:
        cur.close()
        conn.close()


def match_brand_name(user_input: str) -> str:
    """
    사용자 입력(예: '샤넬')을 DB의 정확한 브랜드명(예: 'Chanel')으로 변환합니다.
    """
    if not user_input:
        return user_input

    all_brands = get_all_brands()
    for b in all_brands:
        if b.lower() == user_input.lower():
            return b

    try:
        brands_str = ", ".join(all_brands)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a specialized Brand Name Matcher. Find the exact brand name from the provided List. Return ONLY the string. If no match, return 'None'.",
                },
                {
                    "role": "user",
                    "content": f"List: [{brands_str}]\nUser Input: {user_input}",
                },
            ],
            temperature=0,
        )
        matched = response.choices[0].message.content.strip()
        if matched and matched != "None" and matched in all_brands:
            print(f"   ✨ Brand Correction: '{user_input}' -> '{matched}'")
            return matched
    except Exception:
        pass

    return user_input


# ==========================================
# 2. 메타데이터 로더 (신규 테이블 반영)
# ==========================================
def fetch_meta_data() -> Dict[str, str]:
    meta = {}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # [수정] _R 테이블에서 메타데이터 로드
        cur.execute("SELECT DISTINCT season FROM TB_PERFUME_SEASON_R")
        meta["seasons"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        cur.execute("SELECT DISTINCT occasion FROM TB_PERFUME_OCA_R")
        meta["occasions"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        cur.execute("SELECT DISTINCT accord FROM TB_PERFUME_ACCORD_R LIMIT 100")
        meta["accords"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        # [수정] 성별은 고정값이므로 하드코딩 혹은 R테이블 조회
        meta["genders"] = "Women, Men, Unisex"

        # Style은 현재 별도 R 테이블이 없으므로 Occasion이나 Accord를 참고하거나 비워둠
        # 일단 빈 문자열로 둡니다 (필요 시 수정)
        meta["styles"] = ""

        cur.execute(
            "SELECT perfume_brand, COUNT(*) as cnt FROM TB_PERFUME_BASIC_M GROUP BY perfume_brand ORDER BY cnt DESC LIMIT 50"
        )
        top_brands = [str(r[0]) for r in cur.fetchall() if r[0]]
        meta["brands"] = ", ".join(top_brands)

    except Exception:
        meta = {}
    finally:
        if conn:
            conn.close()
    return meta


# ==========================================
# 3. Tool 함수들 (노트 검색)
# ==========================================
def lookup_note_by_string(keyword: str) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    keyword_clean = keyword.strip().lower()
    found_notes = set()

    try:
        cur.execute(
            "SELECT note FROM TB_PERFUME_NOTES_M WHERE LOWER(note) = %s LIMIT 1",
            (keyword_clean,),
        )
        row = cur.fetchone()
        if row:
            return [row[0]]

        cur.execute("SELECT DISTINCT note FROM TB_PERFUME_NOTES_M")
        all_notes = [r[0] for r in cur.fetchall() if r[0]]

        for db_note in all_notes:
            if len(keyword_clean) < 3:
                if keyword_clean == db_note.lower():
                    found_notes.add(db_note)
                continue
            if distance(keyword_clean, db_note.lower()) <= 2:
                found_notes.add(db_note)

        return list(found_notes)
    except Exception as e:
        print(f"⚠️ Lookup String Note Error: {e}")
        return []
    finally:
        conn.close()


def lookup_note_by_vector(keyword: str) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query_vector = get_embedding(keyword)
        if not query_vector:
            return []
        sql = "SELECT note FROM TB_NOTE_EMBEDDING_M ORDER BY embedding <=> %s::vector LIMIT 10"
        cur.execute(sql, (query_vector,))
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Lookup Vector Note Error: {e}")
        return []
    finally:
        conn.close()


# ==========================================
# 4. 정밀 검색 엔진 (search_perfumes) - [핵심 수정]
# ==========================================
def search_perfumes(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int] = None,
) -> List[Dict[str, Any]]:

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # [1] SELECT 절 수정: 복잡한 연산 제거, _R 테이블 단순 조회
        # 노트 정보는 대소문자 이슈 방지를 위해 UPPER() 사용
        sql = """
            SELECT DISTINCT 
                m.perfume_id as id, 
                m.perfume_brand as brand, 
                m.perfume_name as name, 
                m.img_link as image_url,
                (
                    SELECT STRING_AGG(DISTINCT accord, ', ') 
                    FROM TB_PERFUME_ACCORD_R 
                    WHERE perfume_id = m.perfume_id
                ) as accords,
                (
                    SELECT gender
                    FROM TB_PERFUME_GENDER_R
                    WHERE perfume_id = m.perfume_id
                    LIMIT 1
                ) as gender,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND UPPER(n.type) = 'BASE') as base_notes
            FROM TB_PERFUME_BASIC_M m
        """
        params = []
        where_clauses = []

        # [0] 중복 방지 처리
        if exclude_ids and len(exclude_ids) > 0:
            placeholders = ", ".join(["%s"] * len(exclude_ids))
            where_clauses.append(f"m.perfume_id NOT IN ({placeholders})")
            params.extend(exclude_ids)

        # ---------------------------------------------------------
        # 1. HARD FILTERS (사용자 명시 조건)
        # ---------------------------------------------------------

        # [1-1] Gender Logic (TB_PERFUME_GENDER_R 사용)
        gender_req = hard_filters.get("gender", "").lower()
        if gender_req:
            target_gender = ""
            if gender_req in ["women", "female"]:
                target_gender = "Feminine"
            elif gender_req in ["men", "male"]:
                target_gender = "Masculine"
            elif gender_req in ["unisex"]:
                target_gender = "Unisex"

            if target_gender:
                where_clauses.append(
                    f"m.perfume_id IN (SELECT perfume_id FROM TB_PERFUME_GENDER_R WHERE gender = %s)"
                )
                params.append(target_gender)

        # [1-2] Brand Logic
        if hard_filters.get("brand"):
            corrected_brand = match_brand_name(hard_filters["brand"])
            where_clauses.append("m.perfume_brand ILIKE %s")
            params.append(corrected_brand)

        # [1-3] Other Hard Filters (Season, Occasion, Accord, Note)
        # Note는 기존 M 테이블 유지, 나머지는 R 테이블로 교체
        hard_meta_map = {
            "season": ("TB_PERFUME_SEASON_R", "season"),
            "occasion": ("TB_PERFUME_OCA_R", "occasion"),
            "accord": ("TB_PERFUME_ACCORD_R", "accord"),
            "note": ("TB_PERFUME_NOTES_M", "note"),
        }

        for key, (table, col) in hard_meta_map.items():
            val = hard_filters.get(key)
            if not val:
                continue

            # 단순 존재 여부 확인 (투표 계산 없음)
            where_clauses.append(
                f"m.perfume_id IN (SELECT perfume_id FROM {table} WHERE {col} ILIKE %s)"
            )
            params.append(val)

        # ---------------------------------------------------------
        # 2. STRATEGY FILTERS (AI 전략 제안 조건)
        # ---------------------------------------------------------
        # 매핑 테이블을 _R 테이블로 변경
        strategy_map = {
            "accord": ("TB_PERFUME_ACCORD_R", "accord"),
            "season": ("TB_PERFUME_SEASON_R", "season"),
            "occasion": ("TB_PERFUME_OCA_R", "occasion"),
            "note": ("TB_PERFUME_NOTES_M", "note"),
            # Style은 현재 별도 R 테이블이 없으므로 로직에서 제외하거나 필요한 경우 추가
        }

        for key, values in strategy_filters.items():
            if not values or key == "gender":
                continue

            mapping = strategy_map.get(key.lower())
            if not mapping:
                continue

            table_name, col_name = mapping

            # 범주 내 OR 조건 생성 (예: Accord가 Citrus OR Fresh 인 것)
            category_clauses = []
            for val in values:
                category_clauses.append(
                    f"m.perfume_id IN (SELECT perfume_id FROM {table_name} WHERE {col_name} ILIKE %s)"
                )
                params.append(val)

            if category_clauses:
                where_clauses.append("(" + " OR ".join(category_clauses) + ")")

        # 3. 최종 조립
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " LIMIT 5"

        # 디버깅용 로그 (필요시 주석 해제)
        # print(f"Executing SQL: {sql}")
        # print(f"Params: {params}")

        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        print(f"🚨 DB Search Error: {e}")
        traceback.print_exc()
        return []
    finally:
        cur.close()
        conn.close()
