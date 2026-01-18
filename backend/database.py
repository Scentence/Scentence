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
    def distance(s1, s2): return 0 if s1 == s2 else 100

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
    "male": "Masculine"
}

# DB에 있는 성별 키워드
DB_GENDER_KEYWORDS = {'Feminine', 'Masculine'}

# [★New] 브랜드 목록 캐싱 (반복 쿼리 방지)
BRAND_CACHE = []

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_embedding(text: str) -> List[float]:
    try:
        if not text: return []
        return client.embeddings.create(
            input=text.replace("\n", " "), 
            model="text-embedding-3-small"
        ).data[0].embedding
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
    1. 정확한 일치 확인
    2. LLM을 이용한 번역 및 퍼지 매칭
    """
    if not user_input: return user_input
    
    all_brands = get_all_brands()
    
    # 1. Exact / Case-insensitive Match
    for b in all_brands:
        if b.lower() == user_input.lower():
            return b
            
    # 2. Smart Match via LLM (Translation & Fuzzy)
    # 브랜드 개수가 많지 않으므로(보통 수백 개), LLM에게 리스트를 주고 찾게 하는 것이 가장 정확합니다.
    try:
        # 프롬프트 비용 절약을 위해 리스트가 너무 길면 상위 N개만 자르거나 할 수 있지만,
        # 향수 브랜드는 텍스트량이 적어 전체를 넣어도 괜찮습니다.
        brands_str = ", ".join(all_brands)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a specialized Brand Name Matcher. "
                                              "Find the exact brand name from the provided List that corresponds to the User Input. "
                                              "Handle Korean-English translation and minor typos. "
                                              "Return ONLY the exact string from the list. If no match found, return 'None'."},
                {"role": "user", "content": f"List: [{brands_str}]\nUser Input: {user_input}"}
            ],
            temperature=0
        )
        matched = response.choices[0].message.content.strip()
        
        if matched and matched != "None" and matched in all_brands:
            print(f"   ✨ Brand Correction: '{user_input}' -> '{matched}'")
            return matched
            
    except Exception as e:
        print(f"⚠️ Brand Match Error: {e}")
    
    # 매칭 실패 시 원본 반환 (ILIKE 검색이라도 시도하도록)
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

        # Season
        cur.execute("SELECT DISTINCT season FROM TB_PERFUME_SEASON_M")
        meta['seasons'] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        # Occasion
        cur.execute("SELECT DISTINCT occasion FROM TB_PERFUME_OCA_M")
        meta['occasions'] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        # Accord
        cur.execute("SELECT DISTINCT accord FROM TB_PERFUME_ACCORD_M LIMIT 100")
        meta['accords'] = ", ".join([str(r[0]) for r in cur.fetchall() if r[0]])

        # Audience
        cur.execute("SELECT DISTINCT audience FROM TB_PERFUME_AUD_M")
        all_aud = {str(r[0]) for r in cur.fetchall() if r[0]}
        styles = all_aud - DB_GENDER_KEYWORDS
        meta['genders'] = "Women, Men, Unisex"
        meta['styles'] = ", ".join(list(styles))
        
        # [★New] Brands (Top 50만 샘플로 제공하여 LLM에게 힌트)
        cur.execute("SELECT perfume_brand, COUNT(*) as cnt FROM TB_PERFUME_BASIC_M GROUP BY perfume_brand ORDER BY cnt DESC LIMIT 50")
        top_brands = [str(r[0]) for r in cur.fetchall() if r[0]]
        meta['brands'] = ", ".join(top_brands)

    except Exception:
        meta = {}
    finally:
        if conn: conn.close()
    return meta

# ==========================================
# 2. Tool A: 노트 변환기 (lookup_notes)
# ==========================================
def lookup_notes(keyword: str) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    keyword_clean = keyword.strip().lower()
    found_notes = set()

    try:
        # Step 1. Exact Match
        cur.execute("SELECT note FROM TB_PERFUME_NOTES_M WHERE LOWER(note) = %s LIMIT 1", (keyword_clean,))
        row = cur.fetchone()
        if row: return [row[0]]

        # Step 2. Fuzzy Match
        cur.execute("SELECT DISTINCT note FROM TB_PERFUME_NOTES_M")
        all_notes = [r[0] for r in cur.fetchall() if r[0]]
        for db_note in all_notes:
            if len(keyword_clean) < 3 and keyword_clean != db_note.lower(): continue
            if distance(keyword_clean, db_note.lower()) <= 2:
                found_notes.add(db_note)
        if found_notes: return list(found_notes)

        # Step 3. Vector Match
        query_vector = get_embedding(keyword)
        if query_vector:
            sql = "SELECT note FROM TB_NOTE_EMBEDDING_M ORDER BY embedding <=> %s::vector LIMIT 3"
            cur.execute(sql, (query_vector,))
            return [r[0] for r in cur.fetchall()]
        return []

    except Exception as e:
        print(f"⚠️ Lookup Notes Error: {e}")
        return []
    finally:
        conn.close()

# ==========================================
# 3. Tool B: 정밀 검색 엔진 (search_perfumes)
# ==========================================
def search_perfumes(
    hard_filters: Dict[str, str], 
    strategy_filters: Dict[str, List[str]], 
    exclude_ids: List[int] = None
) -> List[Dict[str, Any]]:
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # [1] Top/Middle/Base 노트 정보 가져오기 (기존 동일)
        sql = """
            SELECT DISTINCT 
                m.perfume_id as id, 
                m.perfume_brand as brand, 
                m.perfume_name as name, 
                m.img_link as image_url,
                (
                    SELECT STRING_AGG(DISTINCT n.note, ', ')
                    FROM TB_PERFUME_NOTES_M n 
                    WHERE n.perfume_id = m.perfume_id AND n.type = 'TOP'
                ) as top_notes,
                (
                    SELECT STRING_AGG(DISTINCT n.note, ', ')
                    FROM TB_PERFUME_NOTES_M n 
                    WHERE n.perfume_id = m.perfume_id AND n.type = 'MIDDLE'
                ) as middle_notes,
                (
                    SELECT STRING_AGG(DISTINCT n.note, ', ')
                    FROM TB_PERFUME_NOTES_M n 
                    WHERE n.perfume_id = m.perfume_id AND n.type = 'BASE'
                ) as base_notes
            FROM TB_PERFUME_BASIC_M m
        """
        params = []
        where_clauses = []

        # [★New] 이미 추천된 향수 제외하기 (Duplicate Prevention)
        if exclude_ids:
            # SQL Injection 방지를 위해 파라미터 바인딩 사용하거나, 정수형 리스트임을 확신하고 포매팅
            # 여기서는 exclude_ids가 정수 리스트라고 가정하고 안전하게 처리
            ids_str = ",".join(map(str, exclude_ids))
            where_clauses.append(f"m.perfume_id NOT IN ({ids_str})")

        # ... (이하 Gender, Brand, Strategy Filters 로직은 기존과 완전히 동일) ...
        # ... (아래 코드는 기존 코드 유지) ...

        # ---------------------------------------------------------
        # 1. Gender Logic
        # ---------------------------------------------------------
        target_genders = []
        if "gender" in hard_filters:
            target_genders.append(hard_filters["gender"].lower())
        if "gender" in strategy_filters:
            target_genders.extend([g.lower() for g in strategy_filters["gender"]])
        target_genders = list(set(target_genders))

        if target_genders:
            gender_conditions = []
            for g_req in target_genders:
                if g_req in ["women", "female"]:
                    gender_conditions.append("""
                        (
                            SUM(CASE WHEN audience = 'Feminine' THEN vote ELSE 0 END)::float / 
                            NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)
                        ) > 0.66
                    """)
                elif g_req in ["men", "male"]:
                    gender_conditions.append("""
                        (
                            SUM(CASE WHEN audience = 'Masculine' THEN vote ELSE 0 END)::float / 
                            NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)
                        ) > 0.66
                    """)
                elif g_req == "unisex":
                    gender_conditions.append("""
                        (
                            SUM(CASE WHEN audience = 'Feminine' THEN vote ELSE 0 END)::float / 
                            NULLIF(SUM(CASE WHEN audience IN ('Feminine', 'Masculine') THEN vote ELSE 0 END), 0)
                        ) BETWEEN 0.34 AND 0.66
                    """)
            if gender_conditions:
                or_clause = " OR ".join(gender_conditions)
                gender_sql = f"""
                    m.perfume_id IN (
                        SELECT perfume_id
                        FROM TB_PERFUME_AUD_M
                        WHERE audience IN ('Feminine', 'Masculine')
                        GROUP BY perfume_id
                        HAVING {or_clause}
                    )
                """
                where_clauses.append(gender_sql)

        # ---------------------------------------------------------
        # 2. Brand
        # ---------------------------------------------------------
        if "brand" in hard_filters and hard_filters["brand"]:
            corrected_brand = match_brand_name(hard_filters["brand"])
            where_clauses.append("m.perfume_brand ILIKE %s")
            params.append(corrected_brand)

        # ---------------------------------------------------------
        # 3. Generic Filters
        # ---------------------------------------------------------
        filter_map = {
            "accord":   ("TB_PERFUME_ACCORD_M", "accord",   True),
            "season":   ("TB_PERFUME_SEASON_M", "season",   True),
            "occasion": ("TB_PERFUME_OCA_M",    "occasion", True),
            "note":     ("TB_PERFUME_NOTES_M",  "note",     False),
            "style":    ("TB_PERFUME_AUD_M",    "audience", True) 
        }

        for key, values in strategy_filters.items():
            if not values or key == 'gender': continue
            key_lower = key.lower()
            if key_lower not in filter_map: continue

            table_name, col_name, has_vote = filter_map[key_lower]
            for val in values:
                if key_lower == "style" and has_vote:
                    subquery = f"""
                        m.perfume_id IN (
                            SELECT t.perfume_id
                            FROM {table_name} t
                            JOIN (
                                SELECT perfume_id, SUM(vote) as total_vote
                                FROM {table_name}
                                WHERE audience NOT IN ('Feminine', 'Masculine')
                                GROUP BY perfume_id
                            ) totals ON t.perfume_id = totals.perfume_id
                            WHERE 
                                t.{col_name} ILIKE %s
                                AND (t.vote::float / NULLIF(totals.total_vote, 0)) >= 0.1
                        )
                    """
                    where_clauses.append(subquery)
                    params.append(val)
                elif has_vote:
                    subquery = f"""
                        m.perfume_id IN (
                            SELECT t.perfume_id
                            FROM {table_name} t
                            JOIN (
                                SELECT perfume_id, SUM(vote) as total_vote
                                FROM {table_name}
                                GROUP BY perfume_id
                            ) totals ON t.perfume_id = totals.perfume_id
                            WHERE 
                                t.{col_name} ILIKE %s
                                AND (t.vote::float / NULLIF(totals.total_vote, 0)) >= 0.1
                        )
                    """
                    where_clauses.append(subquery)
                    params.append(val)
                else:
                    subquery = f"""
                        m.perfume_id IN (
                            SELECT t.perfume_id 
                            FROM {table_name} t 
                            WHERE t.{col_name} ILIKE %s
                        )
                    """
                    where_clauses.append(subquery)
                    params.append(val)

        # 4. Final Query Build
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        sql += " LIMIT 5"

        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        print(f"🚨 DB Search Error: {e}")
        return []
    finally:
        cur.close()
        conn.close()