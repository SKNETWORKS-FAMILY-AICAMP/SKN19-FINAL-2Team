import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=False)


def _get_env_str(key: str, default: str) -> str:
    value = os.getenv(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    # Normalize to valid UTF-8 to prevent psycopg2 decoding errors
    return value.encode("utf-8", "surrogateescape").decode("utf-8", "ignore").strip()

# [수정] 모든 설정을 환경 변수에서 읽어오되, 기본값을 설정합니다.
USER_DB_PARAMS = {
    "dbname": "member_db",  # 회원 전용 DB 명시
    "user": _get_env_str("DB_USER", "scentence"),
    "password": _get_env_str("DB_PASSWORD", "scentence"),
    # 도커 내부에서 로컬 DB에 접속하기 위해 host.docker.internal 사용
    "host": _get_env_str("DB_HOST", "host.docker.internal"),
    "port": _get_env_str("DB_PORT", "5432"),
}


def get_user_db_connection():
    return psycopg2.connect(**USER_DB_PARAMS)
