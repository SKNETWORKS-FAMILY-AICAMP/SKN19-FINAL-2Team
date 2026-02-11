from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from contextlib import asynccontextmanager
import os

from scentmap.db import init_db_schema, close_pool, close_nmap_pool  # [개선] NMap Pool 종료 추가
from scentmap.app.api.label import router as labels_router
from scentmap.app.api.session import router as session_router
from scentmap.app.api.ncard import router as ncard_router
from scentmap.app.api.nmap import router as nmap_router, limiter  # [개선] limiter import
from scentmap.app.services.label_service import load_labels
from slowapi import _rate_limit_exceeded_handler  # [개선] Rate Limit 핸들러
from slowapi.errors import RateLimitExceeded  # [개선] Rate Limit 에러

"""
Scentmap Main: FastAPI 애플리케이션 설정 및 라우터 등록
[개선] Rate Limiting 및 성능 최적화 추가
[개선] EC2 배포 최적화: 로그 레벨 환경 변수 지원
"""

# [개선] 로그 레벨 환경 변수로 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"🚀 Scentmap 시작 - 로그 레벨: {LOG_LEVEL}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Scentmap 서비스 시작 중...")
    init_db_schema()
    try:
        load_labels()
        logger.info("✅ 라벨 데이터 로드 완료")
    except Exception as e:
        logger.error(f"⚠️ 라벨 데이터 로드 실패: {e}")
    yield
    logger.info("🛑 Scentmap 서비스 종료 중...")
    close_pool()
    close_nmap_pool()  # [개선] NMap 전용 Pool 종료

app = FastAPI(title="Scentmap Service", lifespan=lifespan)

# [개선] Rate Limiter 설정
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 설정
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [개선] 응답 압축 (데이터 크기 감소)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 라우터 등록
app.include_router(nmap_router)
app.include_router(labels_router)
app.include_router(session_router)
app.include_router(ncard_router)

@app.get("/")
def root():
    return {"message": "Scentmap service is running!"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "scentmap"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("scentmap.main:app", host="0.0.0.0", port=8001, reload=True)
