ALTER TABLE "paper_embeddings" ALTER COLUMN "embedding_hash" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "paper_references" ALTER COLUMN "reference_paper_id" DROP NOT NULL;