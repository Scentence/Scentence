# MEMBER 계정관리 DB 생성
docker exec -it pgvector-db psql -U sentence -d postgres -c "CREATE DATABASE member_db;"

# MEMBER DB에 테이블 생성
docker exec -i pgvector-db psql -U sentence -d member_db < sql/tb_member_basic_m.sql

# docker-compose.yml 수정 후

# 기존 컨테이너와 볼륨 삭제 후 재생성
docker-compose down -v
// docker-compose up -d db
docker-compose up -d --build

# 기존 컨테이너 재시작 볼륨유지
docker-compose down
docker-compose up -d --build

# 모든 데이터베이스 목록 확인
docker exec -it pgvector-db psql -U sentence -d postgres -c "\l"

# sentence_db 확인
docker exec -it pgvector-db psql -U sentence -d sentence_db -c "\dt"

# member_db 확인
docker exec -it pgvector-db psql -U sentence -d member_db -c "\dt"


# 데이터 insert
docker exec -i pgvector-db psql -U sentence -d member_db < insert_sample_data.sql

-- 모든 데이터 조회
SELECT * FROM TB_MEMBER_BASIC_M;

-- 데이터 개수 확인
SELECT COUNT(*) FROM TB_MEMBER_BASIC_M;

-- 특정 조건으로 조회
SELECT * FROM TB_MEMBER_BASIC_M WHERE SNS_JOIN_YN = 'Y';





# 벡터 테이블 생성
-- 데이터베이스에 접속 후
CREATE EXTENSION IF NOT EXISTS vector;

-- 벡터 컬럼이 있는 테이블 생성
CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    content TEXT,                    -- 원본 텍스트
    embedding VECTOR(1536),          -- 벡터 차원 (예: OpenAI는 1536)
    metadata JSONB,                  -- 추가 메타데이터
    created_at TIMESTAMP DEFAULT NOW()
);