#!/bin/bash
set -e

# PostgreSQL 접속 정보
# docker-compose의 환경 변수와 동일한 키 사용
DB_HOST=${POSTGRES_HOST:-db}
DB_PORT=${POSTGRES_PORT:-5432}
DB_USER=${POSTGRES_USER:-scentence}
DB_PASSWORD=${POSTGRES_PASSWORD:-scentence}
DB_NAME=${POSTGRES_DB:-perfume_db}

export PGPASSWORD="$DB_PASSWORD"

# DB가 기동 완료될 때까지 대기
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  sleep 2
done
echo "[ok] DB 연결 성공"

# 작업 디렉토리 이동
cd /app/scripts/perfume_db

# 1) CSV 생성: tables/*.py 실행
for f in tables/*.py; do
  echo "[csv] $(basename "$f")"
  python3 "$f"
done

# 2) DB 적재: load/*.py 실행
for f in load/*.py; do
  echo "[load] $(basename "$f")"
  sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3
done

echo "[done] perfume_db 데이터 적재 완료"
