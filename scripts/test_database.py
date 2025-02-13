"""
This script is only to test if the database is up and running.
"""

import psycopg

with psycopg.connect(
    "dbname=postgres user=postgres host=localhost password=postgres port=5432"
) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM pg_catalog.pg_tables")
        fetched = cur.fetchall()
        print(fetched)
