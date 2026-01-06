# FastAPI + Next.js + PostgreSQL Docker Compose

## 🚀 빠른 시작 (로컬 Docker Desktop 사용)

### 한 번에 구동하기

```bash
# 프로젝트 클론 (또는 다운로드)
cd final

# 모든 서비스 자동 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```

**참고**: `docker-compose up -d` 실행 시 자동으로 이미지를 빌드합니다. 각자의 Docker Desktop에서 로컬로 빌드되어 실행됩니다.

### 접속 주소
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **PostgreSQL**: localhost:5433

---

## 🔧 주요 명령어

```bash
# 특정 서비스만 재시작
docker-compose restart backend

# 컨테이너 상태 확인
docker-compose ps

# 데이터베이스 접속
docker exec -it pgvector-db psql -U sentence -d sentence_db
```

