#!/bin/bash
set -e

# PostgreSQL 접속 정보
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

# ---------------------------------------------------------
# 1) CSV 생성 단계
# ---------------------------------------------------------

# (1-1) M 테이블용 원본 CSV 생성
for f in tables/*.py; do
  echo "[csv-m] $(basename "$f")"
  python3 "$f"
done

# (1-2) R 테이블용 정제 CSV 생성 (추가된 부분)
# 사용자님의 사진처럼 rtables 폴더 안에 생성 스크립트가 있다고 가정합니다.
if [ -d "rtables" ]; then
  for f in rtables/*.py; do
    echo "[csv-r] $(basename "$f")"
    python3 "$f"
  done
fi

# ---------------------------------------------------------
# 2) DB 적재 단계 (Master Tables)
# ---------------------------------------------------------

echo "[load] to_db_TB_PERFUME_BASIC_M.py (Priority)"
f="load/to_db_TB_PERFUME_BASIC_M.py"
sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3

for f in load/*.py; do
  filename=$(basename "$f")
  if [ "$filename" == "to_db_TB_PERFUME_BASIC_M.py" ]; then
    continue
  fi
  echo "[load-m] $filename"
  sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3
done

# ---------------------------------------------------------
# 3) DB 적재 단계 (Refined Tables)
# ---------------------------------------------------------

echo "[rload] Starting refined data loading (R Tables)"
for f in rload/*.py; do
  echo "[rload-r] $(basename "$f")"
  sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3
done

echo "[done] 모든 데이터(M 및 R 테이블) 적재 완료"