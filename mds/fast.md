### Scentence

**의존성 설치**
package.json에 추가했습니다.
"framer-motion": "^11.18.2",
"@react-three/drei": "^10.7.7",
"@react-three/fiber": "^9.5.0",
"@types/three": "^0.182.0",
"@react-three/postprocessing": "^10.7.7",

**26.02.02 의존성 설치**

### 1. `lucide-react`
- **용도**: 사이드바 메뉴(`sidebar.tsx`)의 직관적인 디자인을 위한 아이콘 라이브러리.
- **적용**: Home, Sparkles, Layers, Map, BookOpen 등 고해상도 SVG 아이콘 사용.
- **설치 명령어**: `npm install lucide-react`

### 2. `framer-motion`
- **용도**: 'Liquid Glass(리퀴드 글래스)' UI의 핵심인 3D 인터랙션과 애니메이션 구현.
- **적용**:
    - `useMotionValue`, `useSpring`, `useTransform`을 활용한 마우스 추적 3D 틸트 효과.
    - 부드러운 호버 트랜지션 및 광택(Shine) 애니메이션.


**실행에 문제있으시면**
docker compose down 혹은 docker compose down -v로
컨테이너를 삭제하고 docker compose up --build를 실행해주세요.

---

## 환경변수 설정 (Environment Variables)

프로젝트 루트에 `.env` 파일을 생성하고 아래 환경변수를 설정해야 합니다.

### 필수 환경변수

#### 데이터베이스 (Database)
```bash
DB_HOST=host.docker.internal  # 로컬 개발 시
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
```

#### AWS S3 및 CloudFront (프로필 이미지 업로드용)
```bash
# AWS 자격증명
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=ap-northeast-2  # 서울 리전 (필요에 따라 변경)

# S3 버킷
AWS_BUCKET_NAME=your_bucket_name

# CloudFront CDN 도메인 (프로토콜 포함, 슬래시 없이)
CLOUDFRONT_DOMAIN=https://your-cdn-domain.cloudfront.net
```

#### OpenAI / LangSmith (챗봇 기능용)
```bash
OPENAI_API_KEY=your_openai_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
```

#### 기타
```bash
# 관리자 이메일 (쉼표로 구분)
ADMIN_EMAILS=admin@example.com,admin2@example.com
NEXT_PUBLIC_ADMIN_EMAILS=admin@example.com,admin2@example.com

# 백엔드 URL 설정
BACKEND_INTERNAL_URL=http://backend:8000
# NEXT_PUBLIC_API_URL은 더 이상 필요하지 않습니다 (API rewrites 사용)
```

### 선택 환경변수 (Defaults 존재)

#### 프로필 이미지 설정
```bash
PROFILE_IMAGE_MAX_MB=5          # 최대 업로드 크기 (기본값: 5MB)
PROFILE_IMAGE_SIZE=256          # 이미지 크기 (기본값: 256x256)
PROFILE_IMAGE_FORMAT=webp       # 이미지 포맷 (기본값: webp)
S3_PREFIX_PROFILE_IMAGES=profile_images  # S3 prefix (기본값: profile_images)
```

#### AWS 임시 자격증명 (STS 사용 시)
```bash
AWS_SESSION_TOKEN=your_session_token  # 임시 자격증명 사용 시에만 필요
```

### 환경변수 파일 생성 방법

1. 프로젝트 루트에 `.env` 파일 생성:
   ```bash
   cp .env.example .env  # .env.example이 있는 경우
   # 또는
   touch .env
   ```

2. 위의 필수 환경변수를 `.env` 파일에 실제 값으로 채워 넣습니다.

3. **중요**: `.env` 파일은 절대 Git에 커밋하지 마세요. (`.gitignore`에 이미 포함됨)

### 프로필 이미지 S3 마이그레이션

기존 로컬 `/uploads` 디렉토리의 프로필 이미지를 S3로 마이그레이션하려면:

```bash
# 환경변수가 설정된 상태에서 실행
docker compose exec backend python scripts/migrate_profile_images_to_s3.py
```

마이그레이션 스크립트는:
- DB의 `/uploads/` 경로를 가진 프로필 이미지를 찾아서
- 256x256 WebP로 변환하고
- S3에 업로드한 후
- DB를 CDN URL로 업데이트합니다
- Idempotent: 재실행해도 안전합니다