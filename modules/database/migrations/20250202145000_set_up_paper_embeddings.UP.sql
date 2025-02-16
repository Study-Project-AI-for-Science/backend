-- Enable the pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the paper_embeddings table
CREATE TABLE paper_embeddings (
    paper_id uuid PRIMARY KEY,  -- Assumes papers.id is uuidv7 (UUID)
    embedding vector(1024) NOT NULL,  -- Using float4 for the embedding data type
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

