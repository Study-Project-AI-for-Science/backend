-- Create UUID v7 generation function if it doesn't exist
create or replace function uuid_generate_v7()
returns uuid
as $$
begin
  -- use random v4 uuid as starting point (which has the same variant we need)
  -- then overlay timestamp
  -- then set version 7 by flipping the 2 and 1 bit in the version 4 string
  return encode(
    set_bit(
      set_bit(
        overlay(uuid_send(gen_random_uuid())
                placing substring(int8send(floor(extract(epoch from clock_timestamp()) * 1000)::bigint) from 3)
                from 1 for 6
        ),
        52, 1
      ),
      53, 1
    ),
    'hex')::uuid;
end
$$
language plpgsql
volatile;

-- Drop the primary key constraint from paper_id
ALTER TABLE paper_embeddings DROP CONSTRAINT paper_embeddings_pkey;

-- Add a new id column as the primary key with UUID v7
ALTER TABLE paper_embeddings ADD COLUMN id uuid PRIMARY KEY DEFAULT uuid_generate_v7();

-- Add foreign key constraint for paper_id
ALTER TABLE paper_embeddings ADD CONSTRAINT paper_embeddings_paper_id_fkey 
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;

-- Add a column for the embedding hash
ALTER TABLE paper_embeddings ADD COLUMN embedding_hash TEXT 
    GENERATED ALWAYS AS (encode(sha256(embedding::text::bytea), 'hex')) STORED;

-- Add unique constraint using the hash instead of the full embedding
ALTER TABLE paper_embeddings ADD CONSTRAINT paper_embeddings_unique_combination 
    UNIQUE (paper_id, model_name, model_version, embedding_hash);