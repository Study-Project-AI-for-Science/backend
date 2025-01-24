import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')

def get_applied_migrations(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migration_history (
                id serial PRIMARY KEY,
                name text UNIQUE NOT NULL,
                applied_at timestamptz DEFAULT now()
            )
        """)
        cur.execute("SELECT name FROM migration_history")
        return {row['name'] for row in cur.fetchall()}

def apply_migration(conn, migration_path, name):
    with open(migration_path, 'r') as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("INSERT INTO migration_history (name) VALUES (%s)", (name,))
    conn.commit()

def run_migrations():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        applied = get_applied_migrations(conn)
        migrations = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql'))
        for migration in migrations:
            if migration not in applied:
                migration_path = os.path.join(MIGRATIONS_DIR, migration)
                print(f"Applying {migration}...")
                apply_migration(conn, migration_path, migration)
        print("Migrations complete.")

if __name__ == '__main__':
    run_migrations()