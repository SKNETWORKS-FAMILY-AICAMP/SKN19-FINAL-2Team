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

# 1) CSV 생성: tables/*.py 실행
for f in tables/*.py; do
  echo "[csv] $(basename "$f")"
  python3 "$f"
done

# 2) DB 적재: load/*.py 실행

# [중요 변경] 부모 테이블(BASIC)을 먼저 명시적으로 실행
echo "[load] to_db_TB_PERFUME_BASIC_M.py (Priority)"
f="load/to_db_TB_PERFUME_BASIC_M.py"
sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3

# 나머지 테이블 실행 (BASIC은 제외하고 실행)
for f in load/*.py; do
  filename=$(basename "$f")
  
  # 위에서 이미 실행한 BASIC 파일은 건너뜀
  if [ "$filename" == "to_db_TB_PERFUME_BASIC_M.py" ]; then
    continue
  fi

  echo "[load] $filename"
  sed \
    -e "s/\"host\": \"localhost\"/\"host\": \"${DB_HOST}\"/" \
    -e "s/\"port\": \"5433\"/\"port\": \"${DB_PORT}\"/" \
    "$f" | python3
done

echo "[done] perfume_db 데이터 적재 완료"