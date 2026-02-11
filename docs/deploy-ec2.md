# AWS EC2 배포 환경변수 가이드

이 문서는 AWS EC2 환경에서 docker-compose를 사용하여 Scentence 애플리케이션을 배포할 때 필요한 환경변수를 설명합니다.

## 필수 환경변수

### 1. Next.js 내부 통신 URL

docker-compose 내부 서비스 간 통신을 위한 URL입니다. 기본값은 docker-compose 서비스명을 사용합니다.

- `BACKEND_INTERNAL_URL` (기본값: `http://backend:8000`)
  - Next.js 서버가 백엔드 FastAPI 서비스와 통신할 때 사용
  - EC2에서도 기본값 유지 권장

- `LAYERING_API_URL` (기본값: `http://layering:8002`)
  - Next.js 서버가 레이어링 서비스와 통신할 때 사용
  - EC2에서도 기본값 유지 권장

- `SCENTMAP_INTERNAL_URL` (기본값: `http://scentmap:8001`)
  - Next.js 서버가 향수 네트워크 맵 서비스와 통신할 때 사용
  - EC2에서도 기본값 유지 권장

### 2. CORS Origins

브라우저에서 접근할 수 있는 오리진(도메인)을 설정합니다. comma-separated 형태로 여러 개 지정 가능합니다.

- `BACKEND_CORS_ORIGINS`
  - 백엔드 FastAPI가 허용할 오리진 목록
  - 예: `http://localhost:3000,http://127.0.0.1:3000,http://<EC2-PUBLIC-IP>:3000,https://yourdomain.com`
  - EC2 Public IP 또는 도메인을 추가해야 브라우저에서 접근 가능

- `LAYERING_CORS_ORIGINS`
  - 레이어링 서비스가 허용할 오리진 목록
  - 형식은 BACKEND_CORS_ORIGINS와 동일

- `CORS_ORIGINS` (scentmap용)
  - 향수 네트워크 맵 서비스가 허용할 오리진 목록
  - 형식은 BACKEND_CORS_ORIGINS와 동일

**중요**: Next.js rewrites를 사용하므로 대부분의 요청은 프록시를 거칩니다. 하지만 일부 시나리오에서 Origin 헤더가 전달될 수 있으므로 CORS 설정을 유지합니다.

### 3. NextAuth (OAuth 로그인)

카카오 소셜 로그인을 사용하는 경우 필수입니다.

- `NEXTAUTH_URL`
  - NextAuth가 사용할 베이스 URL
  - 로컬: `http://localhost:3000`
  - EC2: `http://<EC2-PUBLIC-IP>:3000` 또는 `https://yourdomain.com`
  - 카카오 개발자 콘솔의 Redirect URI와 일치해야 함

- `KAKAO_CLIENT_ID`
  - 카카오 개발자 콘솔에서 발급받은 REST API 키

- `KAKAO_CLIENT_SECRET`
  - 카카오 개발자 콘솔에서 발급받은 Client Secret

### 4. 데이터베이스 (기존)

이미 설정되어 있는 변수들입니다. EC2에서도 동일하게 사용하거나 RDS 주소로 변경합니다.

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

## EC2 배포 예시

### .env 파일 예시

```bash
# === Next.js 내부 통신 (docker-compose 내부 DNS 사용) ===
BACKEND_INTERNAL_URL=http://backend:8000
LAYERING_API_URL=http://layering:8002
SCENTMAP_INTERNAL_URL=http://scentmap:8001

# === CORS Origins (EC2 Public IP 또는 도메인 추가) ===
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://YOUR_EC2_PUBLIC_IP:3000
LAYERING_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://YOUR_EC2_PUBLIC_IP:3000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://YOUR_EC2_PUBLIC_IP:3000

# === NextAuth (OAuth) ===
NEXTAUTH_URL=http://YOUR_EC2_PUBLIC_IP:3000
NEXTAUTH_SECRET=YOUR_RANDOM_SECRET_STRING
KAKAO_CLIENT_ID=YOUR_KAKAO_REST_API_KEY
KAKAO_CLIENT_SECRET=YOUR_KAKAO_CLIENT_SECRET

# === Database ===
DB_HOST=host.docker.internal
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=scentence_db

# === Admin ===
ADMIN_EMAILS=admin@example.com
NEXT_PUBLIC_ADMIN_EMAILS=admin@example.com
```

### 배포 명령

```bash
# EC2에서 실행
docker compose up -d --build
```

## 도메인 사용 시

도메인을 연결한 경우 (예: `https://scentence.com`):

1. CORS Origins에 도메인 추가:
   ```bash
   BACKEND_CORS_ORIGINS=http://localhost:3000,https://scentence.com
   LAYERING_CORS_ORIGINS=http://localhost:3000,https://scentence.com
   CORS_ORIGINS=http://localhost:3000,https://scentence.com
   ```

2. NEXTAUTH_URL 업데이트:
   ```bash
   NEXTAUTH_URL=https://scentence.com
   ```

3. 카카오 개발자 콘솔에서 Redirect URI 업데이트:
   - `https://scentence.com/api/auth/callback/kakao`

## 트러블슈팅

### CORS 에러 발생 시

브라우저 개발자 도구에서 CORS 에러가 발생하면:
1. `.env` 파일의 CORS_ORIGINS에 EC2 Public IP 또는 도메인이 포함되어 있는지 확인
2. `docker compose restart` 또는 `docker compose up -d --build`로 재시작
3. 브라우저 캐시 삭제 후 재시도

### 로그인 콜백 실패 시

1. NEXTAUTH_URL이 브라우저 주소와 일치하는지 확인
2. 카카오 개발자 콘솔의 Redirect URI가 `${NEXTAUTH_URL}/api/auth/callback/kakao` 형태인지 확인
3. KAKAO_CLIENT_ID와 KAKAO_CLIENT_SECRET이 정확한지 확인

### 프록시 연결 실패 (502/504) 시

1. 모든 서비스가 정상 실행 중인지 확인:
   ```bash
   docker compose ps
   ```

2. 헬스체크 엔드포인트 확인:
   ```bash
   curl http://localhost:3000/api/layering-health
   curl http://localhost:3000/api/scentmap-health
   curl http://localhost:3000/api/backend-openapi
   ```

3. docker-compose.yml의 환경변수가 `${VAR:-default}` 형태인지 확인
