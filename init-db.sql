-- init-db.sql
-- member_db 생성
CREATE DATABASE member_db;

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;


-- 벡터 테이블 생성
CREATE TABLE IF NOT EXISTS perfume_embeddings (
    id BIGSERIAL PRIMARY KEY,
    perfume_id INTEGER,
    description TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX ON perfume_embeddings USING hnsw (embedding vector_cosine_ops);