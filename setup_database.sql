-- RWA Chatbot Phase 1 - Database Setup
-- Run this script to set up the PostgreSQL database with pgvector extension

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chatbot schema
CREATE SCHEMA IF NOT EXISTS chatbot;

-- Create objects table for storing Tableau metadata and embeddings
CREATE TABLE IF NOT EXISTS chatbot.objects (
  id BIGSERIAL PRIMARY KEY,
  site_id TEXT NOT NULL,
  object_type TEXT NOT NULL,          -- view | workbook | datasource
  object_id TEXT NOT NULL,            -- Tableau guid/id
  title TEXT NOT NULL,
  description TEXT,
  tags TEXT[],
  fields TEXT[],                      -- column/metric names (for views/datasources)
  project_name TEXT,
  owner TEXT,
  url TEXT,                           -- deep link
  text_blob TEXT NOT NULL,            -- concatenated text for BM25/FTS
  embedding vector(384),              -- size depends on chosen model (all-MiniLM-L6-v2)
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(site_id, object_type, object_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_objects_site_type ON chatbot.objects(site_id, object_type);
CREATE INDEX IF NOT EXISTS idx_objects_project ON chatbot.objects(project_name);
CREATE INDEX IF NOT EXISTS idx_objects_owner ON chatbot.objects(owner);
CREATE INDEX IF NOT EXISTS idx_objects_updated_at ON chatbot.objects(updated_at);

-- Create GIN index for text search (optional, for BM25-like scoring)
CREATE INDEX IF NOT EXISTS idx_objects_text_gin ON chatbot.objects USING gin(to_tsvector('english', text_blob));

-- Create vector similarity search index (HNSW for fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_objects_embedding_hnsw ON chatbot.objects 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Grant permissions (adjust as needed for your setup)
-- GRANT USAGE ON SCHEMA chatbot TO rwa_bot;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA chatbot TO rwa_bot;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA chatbot TO rwa_bot;
