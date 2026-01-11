#!/bin/bash
set -e

echo "데이터베이스 초기화"

# PostgreSQL 사용자 및 비밀번호 설정
export PGPASSWORD=scentence
PSQL="psql -U scentence -d postgres"

# 1. 데이터베이스 생성
echo "데이터베이스 생성"
$PSQL -c "CREATE DATABASE scentence_db;" || echo "scentence_db 이미 존재"
$PSQL -c "CREATE DATABASE member_db;" || echo "member_db 이미 존재"
$PSQL -c "CREATE DATABASE perfume_db;" || echo "perfume_db 이미 존재"
$PSQL -c "CREATE DATABASE recom_db;" || echo "recom_db 이미 존재"

# 2. pgvector 및 오타 보정 확장 활성화 
echo "DB 확장 기능 활성화"
psql -U scentence -d perfume_db -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "vector 확장 이미 존재"
psql -U scentence -d perfume_db -c "CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;" || echo "fuzzystrmatch 확장 이미 존재"

# 3. MEMBER_DB 테이블 생성
echo "MEMBER_DB 테이블 생성"
psql -U scentence -d member_db -f /app/create/member_db/tb_member_basic_m.sql
psql -U scentence -d member_db -f /app/create/member_db/tb_member_profile_t.sql
psql -U scentence -d member_db -f /app/create/member_db/tb_member_status_t.sql
psql -U scentence -d member_db -f /app/create/member_db/tb_member_visit_t.sql

# 4. PERFUME_DB 테이블 생성
echo "PERFUME_DB 테이블 생성"
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_basic_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_accord_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_aud_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_notes_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_oca_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_review_m.sql
psql -U scentence -d perfume_db -f /app/create/perfume_db/tb_perfume_season_m.sql

# 5. RECOM_DB 테이블 생성
echo "RECOM_DB 테이블 생성"
psql -U scentence -d recom_db -f /app/create/recom_db/tb_member_my_perfume_t.sql
psql -U scentence -d recom_db -f /app/create/recom_db/tb_member_recom_result_t.sql

echo "데이터베이스 초기화 완료"
