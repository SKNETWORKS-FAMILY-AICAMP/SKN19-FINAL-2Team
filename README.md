# FastAPI + Next.js + PostgreSQL Docker Compose

## 🚀 빠른 시작 (로컬 Docker Desktop 사용)

```bash

## 🚀 1. 초기 권한 및 환경 설정 (필수)

# 1-1. 스크립트 실행 권한 부여 (에러 방지용)
# [중요] init-db.sh와 init-data.sh를 실행하기 전에 실행 권한을 부여해야 합니다.
# [중요] 에디터 하단 바에서 CRLF를 LF로 변경하고 저장했는지 꼭 확인하세요!
chmod +x init-db.sh init-data.sh

## 🚀 2. 프로젝트 통합 실행

# 기존 데이터 삭제 및 깨끗하게 시작
docker compose down -v
docker compose up --build -d # (-d: 백그라운드 실행)

## 🚀 3. 데이터 적재 확인
docker compose logs -f perfume-etl-worker

## 🚀 4. 프로젝트 클론 (또는 다운로드)
cd Sentence

# .env 파일 설정

위치: Scentence/.env (최상위 루트)

OPENAI_API_KEY: GPT 모델 호출을 위한 키
POSTGRES_...: 데이터베이스 접속 정보

# 모든 서비스 자동 빌드 및 실행
docker compose up -d

# 로그 확인
docker compose logs -f

# 서비스 중지
docker compose down

# 볼륨까지 삭제 (데이터 초기화)
docker compose down -v
```

**참고**: `docker compose up -d` 실행 시 자동으로 이미지를 빌드합니다. 각자의 Docker Desktop에서 로컬로 빌드되어 실행됩니다.

### 접속 주소
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **PostgreSQL**: localhost:5433

---

## 🔧 주요 명령어

```bash
# 특정 서비스만 재시작
docker compose restart backend

# 컨테이너 상태 확인
docker compose ps

# 데이터베이스 접속
docker exec -it pgvector-db psql -U sentence -d sentence_db
```

# Scentence
