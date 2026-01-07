import json
import os
import ast
import re
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# 환경 설정
# ---------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "sentence_db")
DB_USER = os.getenv("POSTGRES_USER", "sentence")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sentence")

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# 스크립트 위치 기준 상대 경로로 데이터 파일 찾기
current_dir = os.path.dirname(os.path.abspath(__file__))
# 경로: backend/scripts/db/ -> backend/data/perfume/perfume_info.jsonl
DATA_FILE_PATH = os.path.join(current_dir, '../../data/perfume/perfume_info.jsonl')

# 임베딩 모델 (한국어 지원)
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
VECTOR_DIM = 384

# ---------------------------------------------------------
# 헬퍼 함수: 데이터 파싱 및 텍스트 생성
# ---------------------------------------------------------

def safe_eval_dict(dict_str: str) -> Dict[str, Any]:
    """
    "{'Key': 'Value'}" 형태의 문자열을 안전하게 파이썬 딕셔너리로 변환합니다.
    """
    if not dict_str:
        return {}
    try:
        return ast.literal_eval(dict_str)
    except (ValueError, SyntaxError):
        return {}

def get_sorted_keys(dict_data: Dict[str, Any], top_k: int = 3) -> List[str]:
    """
    투표수(Value) 기준으로 정렬하여 상위 Key 리스트를 반환합니다.
    예: {'Citrus': '110', 'Spicy': '20'} -> ['Citrus']
    """
    if not dict_data:
        return []
    
    # 문자열 숫자를 정수로 변환하여 정렬
    try:
        # (Key, Value) 튜플 리스트 생성 및 내림차순 정렬
        sorted_items = sorted(
            dict_data.items(), 
            key=lambda item: int(item[1]) if item[1] else 0, 
            reverse=True
        )
        # 상위 K개만 추출
        return [k for k, v in sorted_items[:top_k]]
    except Exception:
        return []

def clean_note_text(note_str: str) -> str:
    """
    노트 텍스트 정규화: 괄호 내용 및 불필요한 공백 제거
    예: "Sicilian Lemon (Oil)" -> "Sicilian Lemon"
    """
    if not note_str:
        return ""
    # 괄호와 괄호 안의 내용 제거
    return re.sub(r'\s*\(.*?\)', '', note_str).strip()

def generate_semantic_text(item: Dict[str, Any]) -> str:
    """
    LLM/검색 모델이 이해하기 쉽도록 구조화된 자연어 텍스트를 생성합니다.
    전략:
    1. 노트 순서(Top->Base)를 명시하여 향의 변화 서술
    2. Accord 투표수를 반영하여 '지배적인 향'과 '보조적인 향' 구분
    """
    name = item.get('perfume', '')
    brand = item.get('brand', '')
    
    # 1. Accord 처리 (투표수 기반 중요도 추출)
    accord_dict = safe_eval_dict(item.get('accord', '{}'))
    sorted_accords = get_sorted_keys(accord_dict, top_k=3)
    
    accord_desc = ""
    if sorted_accords:
        main_accord = sorted_accords[0]
        sub_accords = ", ".join(sorted_accords[1:])
        if sub_accords:
            accord_desc = f"가장 지배적인 향조는 {main_accord}이며, {sub_accords} 뉘앙스가 어우러져 있습니다."
        else:
            accord_desc = f"주요 향조는 {main_accord}입니다."

    # 2. 노트 처리 (향의 시간적 변화 반영)
    # 노트 정보가 없는 경우도 처리
    t_note = clean_note_text(item.get('top_note'))
    m_note = clean_note_text(item.get('middle_note'))
    b_note = clean_note_text(item.get('base_note'))
    
    note_desc = []
    if t_note:
        note_desc.append(f"첫 향(Top Note)으로 {t_note}가 느껴지고,")
    if m_note:
        note_desc.append(f"중간(Middle Note)에는 {m_note} 향이 풍부하게 나며,")
    if b_note:
        note_desc.append(f"마지막(Base Note)은 {b_note} 향으로 마무리됩니다.")
    
    full_note_desc = " ".join(note_desc) if note_desc else "상세 노트 정보가 없습니다."

    # 3. 상황/계절/성별 (Context)
    season_dict = safe_eval_dict(item.get('season', '{}'))
    top_seasons = ", ".join(get_sorted_keys(season_dict, top_k=2))
    
    audience_dict = safe_eval_dict(item.get('audience', '{}'))
    top_audiences = ", ".join(get_sorted_keys(audience_dict, top_k=2))

    context_desc = f"이 향수는 {top_seasons} 계절에 잘 어울리며, {top_audiences} 분위기를 선호하는 사람에게 적합합니다."

    # 최종 조합
    final_text = (
        f"브랜드 {brand}의 향수 {name}입니다. "
        f"{accord_desc} "
        f"{full_note_desc} "
        f"{context_desc}"
    )
    
    return final_text

# ---------------------------------------------------------
# DB 관련 함수
# ---------------------------------------------------------

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"DB Connection Error: {e}")
        # 로컬 테스트 폴백
        if DB_HOST == "db":
            print("Trying localhost:5433...")
            return psycopg2.connect(
                host="localhost", port="5433",
                dbname="sentence_db", user="sentence", password="sentence"
            )
        raise e

def init_db(cursor):
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # 새로운 데이터셋 구조에 맞춘 스키마
    query = f"""
    CREATE TABLE IF NOT EXISTS perfumes (
        id TEXT PRIMARY KEY,
        name TEXT,
        brand TEXT,
        top_note TEXT,
        middle_note TEXT,
        base_note TEXT,
        accords TEXT,     -- 원본 데이터 보존용 (JSON 문자열 등)
        description TEXT, -- 임베딩 생성에 사용된 텍스트 저장
        img_url TEXT,
        link TEXT,
        embedding vector({VECTOR_DIM})
    );
    """
    cursor.execute(query)

def main():
    conn = None
    try:
        # 1. 모델 로딩
        print(f"Loading Model: {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        
        # 2. DB 연결
        conn = get_db_connection()
        cur = conn.cursor()
        init_db(cur)

        # 3. 파일 읽기
        print(f"Reading {DATA_FILE_PATH}...")
        data_rows = []
        if os.path.exists(DATA_FILE_PATH):
            with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data_rows.append(json.loads(line))
        else:
            print("File not found.")
            return

        print(f"Processing {len(data_rows)} items...")

        # 4. 텍스트 생성 및 임베딩
        texts_to_embed = []
        rows_to_insert = []
        
        for item in data_rows:
            # RAG 검색용 의미론적 텍스트 생성
            semantic_text = generate_semantic_text(item)
            texts_to_embed.append(semantic_text)
            
            # DB 삽입용 데이터 준비
            rows_to_insert.append({
                "id": item.get('perfume_id'),
                "name": item.get('perfume'),
                "brand": item.get('brand'),
                "top": item.get('top_note'),
                "mid": item.get('middle_note'),
                "base": item.get('base_note'),
                "accord": item.get('accord'), # 원본 JSON 문자열
                "desc": semantic_text,        # 검색 결과 표시용
                "img": item.get('img'),
                "link": item.get('link')
            })

        print("Calculating embeddings...")
        embeddings = model.encode(texts_to_embed, show_progress_bar=True)

        # 5. DB 적재 (Execute Values)
        db_values = []
        for row, vector in zip(rows_to_insert, embeddings):
            db_values.append((
                row['id'], row['name'], row['brand'],
                row['top'], row['mid'], row['base'],
                row['accord'], row['desc'], row['img'], row['link'],
                vector.tolist()
            ))
            
        insert_query = """
            INSERT INTO perfumes 
            (id, name, brand, top_note, middle_note, base_note, accords, description, img_url, link, embedding)
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                brand = EXCLUDED.brand,
                top_note = EXCLUDED.top_note,
                middle_note = EXCLUDED.middle_note,
                base_note = EXCLUDED.base_note,
                accords = EXCLUDED.accords,
                description = EXCLUDED.description,
                img_url = EXCLUDED.img_url,
                link = EXCLUDED.link,
                embedding = EXCLUDED.embedding;
        """
        
        print("Inserting into DB...")
        execute_values(cur, insert_query, db_values)
        conn.commit()
        print("Done!")

    except Exception as e:
        print(f"Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    main()