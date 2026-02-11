# 향수맵(scentmap) 서비스용 Dockerfile
# Build context: Scentence
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 PostgreSQL 클라이언트 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc && \
    rm -rf /var/lib/apt/lists/*

# 프로젝트 파일 복사 및 설치
COPY pyproject.toml /app/pyproject.toml
COPY scentmap /app/scentmap
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')" || exit 1

# 포트 노출
EXPOSE 8001

# 애플리케이션 실행
CMD ["uvicorn", "scentmap.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
