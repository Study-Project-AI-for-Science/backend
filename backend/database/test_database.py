import psycopg


with psycopg.connect("dbname=LLMsForScience user=root host=localhost password=root port=5432") as conn:
    
    with conn.cursor() as cur:
        
        cur.execute("""
                    SELECT * FROM pg_catalog.pg_tables""")
        
        fetched = cur.fetchall()
        
        print(fetched)