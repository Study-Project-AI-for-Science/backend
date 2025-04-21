-- Custom SQL migration file, put your code below! --
-- Create the HNSW index concurrently using cosine similarity
COMMIT;--> statement-breakpoint
CREATE INDEX CONCURRENTLY paper_embeddings_embedding_hnsw_idx
ON paper_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);