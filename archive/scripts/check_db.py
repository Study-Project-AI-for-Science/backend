import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


def main():
    with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM papers")
            papers_count = cur.fetchone()["count"]
            print(f"Papers table count: {papers_count}")

            cur.execute("SELECT COUNT(*) as count FROM paper_embeddings")
            embeddings_count = cur.fetchone()["count"]
            print(f"Paper embeddings table count: {embeddings_count}")

            if embeddings_count > 0:
                print("\nExisting paper_embeddings records:")
                cur.execute("SELECT paper_id FROM paper_embeddings")
                for row in cur.fetchall():
                    print(f"Paper ID: {row['paper_id']}")


if __name__ == "__main__":
    main()
