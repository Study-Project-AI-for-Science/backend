CREATE TABLE "paper_embeddings" (
	"id" text PRIMARY KEY NOT NULL,
	"paper_id" text NOT NULL,
	"embedding" vector(1024) NOT NULL,
	"model_name" text NOT NULL,
	"model_version" text NOT NULL,
	"embedding_hash" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "paper_embeddings_embeddingHash_unique" UNIQUE("embedding_hash")
);
--> statement-breakpoint
CREATE TABLE "paper_references" (
	"id" text PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"authors" text NOT NULL,
	"fields" jsonb NOT NULL,
	"paper_id" text NOT NULL,
	"reference_paper_id" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "papers" (
	"id" text PRIMARY KEY NOT NULL,
	"title" text NOT NULL,
	"authors" text NOT NULL,
	"file_url" text NOT NULL,
	"file_hash" text NOT NULL,
	"abstract" text,
	"online_url" text,
	"content" text,
	"published_date" timestamp with time zone,
	"updated_date" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "papers_fileHash_unique" UNIQUE("file_hash")
);
--> statement-breakpoint
ALTER TABLE "paper_embeddings" ADD CONSTRAINT "paper_embeddings_paper_id_papers_id_fk" FOREIGN KEY ("paper_id") REFERENCES "public"."papers"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "paper_references" ADD CONSTRAINT "paper_references_paper_id_papers_id_fk" FOREIGN KEY ("paper_id") REFERENCES "public"."papers"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "paper_references" ADD CONSTRAINT "paper_references_reference_paper_id_papers_id_fk" FOREIGN KEY ("reference_paper_id") REFERENCES "public"."papers"("id") ON DELETE no action ON UPDATE no action;