"""
This script is intended solely for inserting papers in a simple manner without a specifically crafted hash and without the correct authors. These details cannot be easily extracted from the PDF files. The purpose of this script is to test the general handling of files in the database and their connection with files in the S3 storage. It also does not store or create embeddings for the paper.
"""

import os
import sys
from uuid_extensions import uuid7str as uuid7
import hashlib
import boto3
import psycopg
from psycopg.rows import dict_row

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
MINIO_URL = "http://localhost:9000"
ACCESS_KEY = "ROOT_USER"
SECRET_KEY = "TOOR_PASSWORD"
BUCKET_NAME = "papers"

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def upload_to_minio(file_path):
    """Upload file to MinIO and return the file URL"""
    s3_client = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )
    
    file_id = str(uuid7())
    file_name = os.path.basename(file_path)
    object_name = f"{file_id}/{file_name}"
    
    s3_client.upload_file(file_path, BUCKET_NAME, object_name)
    return f"{MINIO_URL}/{BUCKET_NAME}/{object_name}"

def insert_paper(title, file_path):
    """Insert paper information into the database"""
    # Generate a unique ID for the paper
    paper_id = uuid7()
    
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)
    
    # Upload file to MinIO
    file_url = upload_to_minio(file_path)
    
    # Insert into database
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO papers (id, title, authors, file_url, file_hash)
                VALUES (%s, %s, %s, %s, %s)
            """, (paper_id, title, "Sample Author", file_url, file_hash))
        conn.commit()
    
    print(f"Inserted paper: {title}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python insert_paper.py <title> <pdf_path>")
        sys.exit(1)
    
    title = sys.argv[1]
    pdf_path = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist")
        sys.exit(1)
    
    try:
        insert_paper(title, pdf_path)
    except Exception as e:
        print(f"Error inserting paper: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()