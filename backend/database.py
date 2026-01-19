# database.py
import os
import traceback
import json
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI

# 오탈자 보정 라이브러리 (없으면 더미 함수 사용)
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

# [★Mapping Constants] LLM 용어 -> DB 용어 매핑
GENDER_MAP = {
    "women": "Feminine",
    "female": "Feminine",
    "men": "Masculine",
    "male": "Masculine",
}

# DB에 있는 성별 키워드
DB_GENDER_KEYWORDS = {"Feminine", "Masculine"}

# [★New] 브랜드 목록 캐싱 (반복 쿼리 방지)
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
# [★New] 브랜드명 자동 보정 함수
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
    사용자 입력(예: '샤넬', 'Chanle')을 DB의 정확한 브랜드명(예: 'Chanel')으로 변환합니다.
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
# 1. 메타데이터 로더
# ==========================================
def fetch_meta_data() -> Dict[str, str]:
    meta = {}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT season FROM TB_PERFUME_SEASON_M")
        meta["seasons"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        cur.execute("SELECT DISTINCT occasion FROM TB_PERFUME_OCA_M")
        meta["occasions"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        cur.execute("SELECT DISTINCT accord FROM TB_PERFUME_ACCORD_M LIMIT 100")
        meta["accords"] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        cur.execute("SELECT DISTINCT audience FROM TB_PERFUME_AUD_M")
        all_aud = {str(r[0]) for r in cur.fetchall() if r[0]}
        styles = all_aud - DB_GENDER_KEYWORDS
        meta["genders"] = "Women, Men, Unisex"
        meta["styles"] = ", ".join(list(styles))

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
# 2. Tool A-1: 문자 기반 노트 교정 (Hard Filter용)
# ==========================================
def lookup_note_by_string(keyword: str) -> List[str]:
    """
    사용자가 직접 입력한 키워드를 바탕으로 DB에서 정확한 노트 명칭을 찾습니다.
    완전 일치 확인 후, 오탈자(편집 거리 2 이하)를 교정합니다.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    keyword_clean = keyword.strip().lower()
    found_notes = set()

    try:
        # 1. 완전 일치 확인 (Exact Match)
        cur.execute(
            "SELECT note FROM TB_PERFUME_NOTES_M WHERE LOWER(note) = %s LIMIT 1",
            (keyword_clean,),
        )
        row = cur.fetchone()
        if row:
            return [row[0]]

        # 2. 오탈자 교정 (Fuzzy Match - Levenshtein Distance)
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


# ==========================================
# 2. Tool A-2: 벡터 기반 의미 검색 (Strategy Filter용)
# ==========================================
def lookup_note_by_vector(keyword: str) -> List[str]:
    """
    AI가 제안한 추상적 키워드를 바탕으로 벡터 DB에서 의미상 유사한 노드를 찾습니다.
    리서처가 최종 선택할 수 있도록 후보군을 10개까지 추출합니다.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query_vector = get_embedding(keyword)
        if not query_vector:
            return []

        # [★수정] 코사인 유사도 기반 상위 10개 노트 추출 (리서처 선택 풀 확보)
        sql = "SELECT note FROM TB_NOTE_EMBEDDING_M ORDER BY embedding <=> %s::vector LIMIT 10"
        cur.execute(sql, (query_vector,))
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Lookup Vector Note Error: {e}")
        return []
    finally:
        conn.close()


# ==========================================
# 3. Tool B: 정밀 검색 엔진 (search_perfumes)
# ==========================================
def search_perfumes(
    hard_filters: Dict[str, Any],
    strategy_filters: Dict[str, List[str]],
    exclude_ids: List[int] = None,
) -> List[Dict[str, Any]]:

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. SELECT 절: 10% 투표 비중 이상의 어코드만 추출 로직 반영
        sql = """
            SELECT DISTINCT 
                m.perfume_id as id, 
                m.perfume_brand as brand, 
                m.perfume_name as name, 
                m.img_link as image_url,
                (
                    SELECT STRING_AGG(DISTINCT a.accord, ', ') 
                    FROM TB_PERFUME_ACCORD_M a 
                    JOIN (
                        SELECT perfume_id, SUM(vote) as total_vote 
                        FROM TB_PERFUME_ACCORD_M 
                        GROUP BY perfume_id
                    ) totals ON a.perfume_id = totals.perfume_id
                    WHERE a.perfume_id = m.perfume_id 
                      AND (a.vote::float / NULLIF(totals.total_vote, 0)) >= 0.1
                ) as accords,
                (
                    SELECT audience 
                    FROM TB_PERFUME_AUD_M 
                    WHERE perfume_id = m.perfume_id AND audience IN ('Feminine', 'Masculine')
                    GROUP BY audience 
                    ORDER BY SUM(vote) DESC 
                    LIMIT 1
                ) as gender,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND n.type = 'TOP') as top_notes,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND n.type = 'MIDDLE') as middle_notes,
                (SELECT STRING_AGG(DISTINCT n.note, ', ') FROM TB_PERFUME_NOTES_M n WHERE n.perfume_id = m.perfume_id AND n.type = 'BASE') as base_notes
            FROM TB_PERFUME_BASIC_M m
        """
        params = []
        where_clauses = []

        # [0] 중복 방지 처리 (보안 및 에러 방지를 위해 %s 사용)
        if exclude_ids and len(exclude_ids) > 0:
            placeholders = ", ".join(["%s"] * len(exclude_ids))
            where_clauses.append(f"m.perfume_id NOT IN ({placeholders})")
            params.extend(exclude_ids)

        # ---------------------------------------------------------
        # 1. HARD FILTERS (사용자 명시 조건 - AND 결합)
        # ---------------------------------------------------------
        gender_req = hard_filters.get("gender", "").lower()
        if gender_req:
            if gender_req in ["women", "female"]:
                cond = "(SUM(CASE WHEN audience = 'Feminine' THEN vote ELSE 0 END)::float / NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)) > 0.66"
            elif gender_req in ["men", "male"]:
                cond = "(SUM(CASE WHEN audience = 'Masculine' THEN vote ELSE 0 END)::float / NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)) > 0.66"
            else:
                cond = "(SUM(CASE WHEN audience = 'Feminine' THEN vote ELSE 0 END)::float / NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)) BETWEEN 0.34 AND 0.66"
            where_clauses.append(
                f"m.perfume_id IN (SELECT perfume_id FROM TB_PERFUME_AUD_M WHERE audience IN ('Feminine', 'Masculine') GROUP BY perfume_id HAVING {cond})"
            )

        if hard_filters.get("brand"):
            corrected_brand = match_brand_name(hard_filters["brand"])
            where_clauses.append("m.perfume_brand ILIKE %s")
            params.append(corrected_brand)

        hard_meta_map = {
            "season": ("TB_PERFUME_SEASON_M", "season"),
            "occasion": ("TB_PERFUME_OCA_M", "occasion"),
            "accord": ("TB_PERFUME_ACCORD_M", "accord"),
            "note": ("TB_PERFUME_NOTES_M", "note"),
        }
        for key, (table, col) in hard_meta_map.items():
            val = hard_filters.get(key)
            if not val:
                continue
            if key == "note":
                where_clauses.append(
                    f"m.perfume_id IN (SELECT perfume_id FROM {table} WHERE {col} ILIKE %s)"
                )
                params.append(val)
            else:
                where_clauses.append(
                    f"""
                    m.perfume_id IN (
                        SELECT t.perfume_id FROM {table} t
                        JOIN (SELECT perfume_id, SUM(vote) as tv FROM {table} GROUP BY perfume_id) totals ON t.perfume_id = totals.perfume_id
                        WHERE t.{col} ILIKE %s AND (t.vote::float / NULLIF(totals.tv, 0)) >= 0.1
                    )
                """
                )
                params.append(val)

        # ---------------------------------------------------------
        # 2. STRATEGY FILTERS (AI 전략 제안 조건 - 범주 내 OR 결합)
        # ---------------------------------------------------------
        strategy_map = {
            "accord": ("TB_PERFUME_ACCORD_M", "accord", True),
            "season": ("TB_PERFUME_SEASON_M", "season", True),
            "occasion": ("TB_PERFUME_OCA_M", "occasion", True),
            "note": ("TB_PERFUME_NOTES_M", "note", False),
            "style": ("TB_PERFUME_AUD_M", "audience", True),
        }

        for key, values in strategy_filters.items():
            if not values or key == "gender":
                continue
            mapping = strategy_map.get(key.lower())
            if not mapping:
                continue
            table_name, col_name, has_vote = mapping

            # [★핵심 수정] 동일 범주(예: 여러 Accord) 내의 필터들을 OR로 묶기 위한 리스트
            category_clauses = []
            for val in values:
                if key.lower() == "style" and has_vote:
                    category_clauses.append(
                        f"""
                        m.perfume_id IN (
                            SELECT t.perfume_id FROM {table_name} t
                            JOIN (SELECT perfume_id, SUM(vote) as tv FROM {table_name} WHERE audience NOT IN ('Feminine', 'Masculine') GROUP BY perfume_id) totals ON t.perfume_id = totals.perfume_id
                            WHERE t.{col_name} ILIKE %s AND (t.vote::float / NULLIF(totals.tv, 0)) >= 0.1
                        )
                    """
                    )
                    params.append(val)
                elif has_vote:
                    category_clauses.append(
                        f"""
                        m.perfume_id IN (
                            SELECT t.perfume_id FROM {table_name} t
                            JOIN (SELECT perfume_id, SUM(vote) as tv FROM {table_name} GROUP BY perfume_id) totals ON t.perfume_id = totals.perfume_id
                            WHERE t.{col_name} ILIKE %s AND (t.vote::float / NULLIF(totals.tv, 0)) >= 0.1
                        )
                    """
                    )
                    params.append(val)
                else:
                    category_clauses.append(
                        f"m.perfume_id IN (SELECT perfume_id FROM {table_name} WHERE {col_name} ILIKE %s)"
                    )
                    params.append(val)

            # 범주 내에 조건이 있다면 (OR)로 감싸서 전체 WHERE 절에 추가
            if category_clauses:
                where_clauses.append("(" + " OR ".join(category_clauses) + ")")

        # 3. 최종 조립
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " LIMIT 5"
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        print(f"🚨 DB Search Error: {e}")
        traceback.print_exc()
        return []
    finally:
        cur.close()
        conn.close()
