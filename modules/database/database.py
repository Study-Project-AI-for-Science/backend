"""
database.py

This module provides a unified interface for handling database operations for papers and
their embeddings,
as well as interactions with S3 storage. The functions below are placeholders with
detailed documentation
on what they should do, including considerations for error handling, consistency,
and extensibility.
"""

import os
import hashlib
import boto3
import psycopg
from psycopg.rows import dict_row
import logging
from uuid_extensions import uuid7str as uuid7
import time
import botocore.exceptions
from dotenv import load_dotenv

from modules.ollama import ollama as ollama

load_dotenv()

# Configure logging for debugging and error tracking.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Database configuration: Adjust these as needed.
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# MinIO configuration
MINIO_URL = os.getenv("MINIO_URL", "http://localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "TOOR_PASSWORD")
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "papers")

# Initialize the MinIO client using boto3.
# Note: MinIO supports the S3 API; we set the endpoint_url accordingly.
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
)


def _paper_upload_to_s3(file_path: str) -> str:
    """
    Uploads a PDF file to S3 with error handling and retry mechanism.

    Description:
        Uploads the file located at `file_path` to the S3 storage and returns its URL.

    Parameters:
        file_path (str): The local filesystem path of the PDF file to upload.

    Returns:
        str: The URL of the uploaded file on S3.

    Raises:
        Exception: If the upload fails after the maximum number of retries.

    Example:
        url = _paper_upload_to_s3("/path/to/file.pdf")
    """
    file_id = str(uuid7())
    file_name = os.path.basename(file_path)
    object_name = f"{file_id}/{file_name}"
    max_retries = 3
    delay = 2  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            s3_client.upload_file(file_path, BUCKET_NAME, object_name)
            url = f"{MINIO_URL}/{BUCKET_NAME}/{object_name}"
            logger.info(f"Successfully uploaded file to S3: {url}")
            return url
        except botocore.exceptions.ClientError as e:
            logger.error(f"S3 ClientError on attempt {attempt} for file {file_path}: {e}")
        except botocore.exceptions.EndpointConnectionError as e:
            logger.error(f"S3 EndpointConnectionError on attempt {attempt} for file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt} for file {file_path}: {e}")
        if attempt < max_retries:
            logger.info(f"Retrying upload in {delay} seconds...")
            time.sleep(delay)
    raise Exception(f"Failed to upload {file_path} to S3 after {max_retries} attempts.")


def _paper_download_from_s3(file_url: str, destination_path: str) -> None:
    """
    Downloads a file from S3 and saves it to a local destination.

    Description:
        Given a file URL from S3, this function extracts the S3 object key and downloads
        the file to the provided destination path.

    Parameters:
        file_url (str): The complete URL of the file stored on S3.
        destination_path (str): The local filesystem path where the file should be saved.

    Returns:
        None

    Raises:
        ValueError: If the `file_url` is not valid.
        Exception: If there is an error during the file download.

    Example:
        _paper_download_from_s3("http://localhost:9000/papers/abc/filename.pdf", "/local/path/file.pdf")
    """
    prefix = f"{MINIO_URL}/{BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        logger.error(f"Invalid file URL: {file_url}")
        raise ValueError(f"Invalid file URL: {file_url}")
    object_name = file_url[len(prefix) :]

    try:
        s3_client.download_file(BUCKET_NAME, object_name, destination_path)
        logger.info(f"Successfully downloaded file from S3 to {destination_path}")
    except Exception as e:
        logger.error(f"Error downloading file from S3: {e}")
        raise e


def _paper_compute_file_hash(file_path: str) -> str:
    """
    Computes the SHA-256 hash of a file's contents.

    Description:
        Opens the file at `file_path` in binary mode and computes its SHA-256 hash using streamed read.

    Parameters:
        file_path (str): The path to the file whose hash is to be computed.

    Returns:
        str: A hexadecimal string representing the SHA-256 hash of the file.

    Raises:
        Exception: If there is any error during file reading or hash computation.

    Example:
        file_hash = _paper_compute_file_hash("/path/to/file.pdf")
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
    except Exception as e:
        logger.error(f"Error computing file hash for {file_path}: {e}")
        raise e

    return hash_sha256.hexdigest()


def paper_find(paper_id: str) -> dict:
    """
    Retrieves a paper's metadata from the database.

    Description:
        Searches the "papers" table for a record with the given `paper_id` and returns its metadata.

    Parameters:
        paper_id (str): The unique identifier of the paper.

    Returns:
        dict: A dictionary containing the paper's metadata.

    Raises:
        Exception: If the paper is not found or a database error occurs.

    Example:
        paper = paper_find("1234abcd")
    """
    query = "SELECT * FROM papers WHERE paper_id = %s;"

    try:
        # Connect to the database using psycopg and set row factory for dict output.
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (paper_id,))
                paper = cur.fetchone()

        if paper is None:
            logger.error(f"Paper with ID {paper_id} not found.")
            raise Exception(f"Paper with ID {paper_id} not found.")

        return paper

    except Exception as e:
        logger.error(f"Error retrieving paper {paper_id}: {e}")
        raise e


def paper_get_file(paper_id: str, destination_path: str) -> None:
    """
    Retrieves a paper file from S3 using its metadata.

    Description:
        Uses `paper_find` to retrieve the paper metadata by `paper_id`, extracts the `file_url`,
        and downloads the file from S3 to the `destination_path`.

    Parameters:
        paper_id (str): The unique identifier of the paper.
        destination_path (str): The local path where the file should be saved.

    Returns:
        None

    Raises:
        Exception: If the paper is not found or the file_url is missing.

    Example:
        paper_get_file("1234abcd", "/local/path/file.pdf")
    """
    paper = paper_find(paper_id)
    file_url = paper.get("file_url")
    if not file_url:
        logger.error(f"File URL not found for paper ID {paper_id}")
        raise Exception(f"File URL not found for paper ID {paper_id}")

    _paper_download_from_s3(file_url, destination_path)


def paper_get_embeddings(paper_id: str) -> dict:
    """
    Retrieves a paper's embeddings and associated
    metadata from the "paper_embeddings" table.

    Steps:
      - Query the "paper_embeddings" table using the paper_id.
      - Return the embeddings along with model_name, model_version, and created_at.

    Considerations:
      - Handle cases where no embedding is found for the provided paper_id.
      - Ensure consistency with the "papers" table via foreign key relationships.
    """
    query = """
        SELECT embedding, model_name, model_version, created_at
        FROM paper_embeddings
        WHERE paper_id = %s;
    """
    try:
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (paper_id,))
                result = cur.fetchone()
        if result is None:
            logger.error(f"No embeddings found for paper ID {paper_id}")
            raise Exception(f"No embeddings found for paper ID {paper_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving embeddings for paper {paper_id}: {e}")
        raise e


def paper_insert(file_path: str, title: str, authors: str):
    """
    Inserts a new paper and its embedding(s) into the database.

    Description:
        Computes the file hash, uploads the paper to S3, generates one or more embeddings,
        and inserts the paper's metadata into the "papers" table and each embedding into the
        "paper_embeddings" table. The embedding generation function returns multiple embeddings,
        all associated with the same paper id. It also returns the model_name and model_version used.

    Parameters:
        file_path (str): The local path to the PDF file.
        title (str): The title of the paper.
        authors (str): The authors of the paper.

    Returns:
        The paper_id (str) of the newly inserted paper.

    Raises:
        Exception: If any step fails (hash computation, S3 upload, embedding generation, or database insertion).

    Example:
        paper_id = paper_insert("/path/to/file.pdf", "Title", "Author A, Author B")
    """
    try:
        # Compute file hash.
        file_hash = _paper_compute_file_hash(file_path)

        # Upload file to S3.
        file_url = _paper_upload_to_s3(file_path)

        # If title or authors is empty, fill missing info using paper_get_info.
        if not title or not authors:
            # Assume paper_get_info returns a dict with keys: title and authors.
            info = ollama.get_paper_info(file_path)
            if not title:
                title = info.get("title", title)
            if not authors:
                authors = info.get("authors", authors)

        # Generate embeddings using the file directly.
        # Expecting get_paper_embeddings to return a dict with keys:
        # "embeddings": list of embeddings, "model_name": str, "model_version": str.
        embedding_info = ollama.get_paper_embeddings(file_path)
        embeddings = embedding_info.get("embeddings", [])
        model_name = embedding_info.get("model_name", "")
        model_version = embedding_info.get("model_version", "")

        if not embeddings:
            # Fallback to a dummy embedding if the generation fails.
            embeddings = [[0.0] * 1024]

        # Insert records into the database in a transaction.
        with psycopg.connect(POSTGRES_URL) as conn:
            with conn.cursor() as cur:
                # Insert into papers table.
                paper_insert_query = """
                    INSERT INTO papers (title, authors, file_url, file_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING paper_id;
                """
                cur.execute(paper_insert_query, (title, authors, file_url, file_hash))
                paper_id = cur.fetchone()[0]

                # Insert one record per embedding.
                embed_insert_query = """
                    INSERT INTO paper_embeddings (paper_id, embedding, model_name, model_version)
                    VALUES (%s, %s, %s, %s);
                """
                for emb in embeddings:
                    cur.execute(embed_insert_query, (paper_id, emb, model_name, model_version))
            conn.commit()

        logger.info(f"Successfully inserted paper with ID {paper_id}")
        return paper_id

    except Exception as e:
        logger.error(f"Failed to insert paper: {e}")
        raise e


def paper_get_similar_to_query(query_embedding: list, limit: int = 10, similarity_dropout: float = 0.0) -> list:
    """
    Searches for papers with embeddings similar to the given query_embedding.

    Steps:
      - Use the vector similarity search capabilities of PostgreSQL (via pgvector)
        to find similar embeddings.
      - Optionally filter out results with a similarity (distance) greater than similarity_dropout.
      - Join the results with the "papers" table to get full metadata.
      - Return a list of papers, each with its similarity score.

    Parameters:
        query_embedding (list): The embedding vector to compare.
        limit (int): The maximum number of results to return.
        similarity_dropout (float): A threshold for the similarity score. Only papers with
                                    a similarity (i.e. distance) <= this value will be returned.
                                    Set to 0.0 to disable filtering.

    Returns:
        list: A list of dictionaries containing paper metadata and similarity scores.

    Raises:
        Exception: If there is an error executing the database query.
    """
    try:
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if similarity_dropout > 0:
                    query = """
                        SELECT p.*, 
                               pe.embedding, 
                               pe.model_name, 
                               pe.model_version, 
                               pe.created_at, 
                               (pe.embedding <=> %s) AS similarity
                        FROM paper_embeddings pe
                        JOIN papers p ON p.paper_id = pe.paper_id
                        WHERE (pe.embedding <=> %s) <= %s
                        ORDER BY (pe.embedding <=> %s)
                        LIMIT %s;
                    """
                    # Pass the query_embedding four times and similarity_dropout value.
                    cur.execute(query, (query_embedding, query_embedding, similarity_dropout, query_embedding, limit))
                else:
                    query = """
                        SELECT p.*, 
                               pe.embedding, 
                               pe.model_name, 
                               pe.model_version, 
                               pe.created_at, 
                               (pe.embedding <=> %s) AS similarity
                        FROM paper_embeddings pe
                        JOIN papers p ON p.paper_id = pe.paper_id
                        ORDER BY (pe.embedding <=> %s)
                        LIMIT %s;
                    """
                    cur.execute(query, (query_embedding, query_embedding, limit))
                results = cur.fetchall()
        if not results:
            logger.info("No similar papers found for the provided query embedding.")
        return results
    except Exception as e:
        logger.error(f"Error executing similarity search for query embedding: {e}")
        raise e


def paper_update(paper_id: str, **kwargs):
    """
    Updates fields of a paper record in the database.

    Description:
        Validates and updates the specified fields for the paper with `paper_id` in the "papers" table.

    Parameters:
        paper_id (str): The unique identifier of the paper to update.
        kwargs: Keyword arguments corresponding to the fields to update.
                Allowed keys: 'title', 'authors', 'file_url', 'file_hash'.

    Returns:
        dict: The updated paper record.

    Raises:
        ValueError: If an invalid field is provided or no valid fields are provided.
        Exception: If the paper is not found or a database error occurs.

    Example:
        updated_record = paper_update("1234abcd", title="New Title", authors="New Authors")
    """
    # Define allowed fields that can be updated.
    allowed_fields = {"title", "authors", "file_url", "file_hash"}
    set_clauses = []
    params = []

    # Validate input fields.
    for field, value in kwargs.items():
        if field not in allowed_fields:
            raise ValueError(f"Invalid field for update: {field}")
        set_clauses.append(f"{field} = %s")
        params.append(value)

    if not set_clauses:
        raise ValueError("No valid fields provided to update.")

    # Construct the SQL query.
    set_clause = ", ".join(set_clauses)
    query = f"UPDATE papers SET {set_clause} WHERE paper_id = %s RETURNING *;"
    params.append(paper_id)

    try:
        # Connect to the database and perform the update in a transaction.
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                updated_record = cur.fetchone()
                if updated_record is None:
                    raise Exception(f"Paper with ID {paper_id} not found.")
            conn.commit()
        logger.info(f"Successfully updated paper with ID {paper_id}")
        return updated_record
    except Exception as e:
        logger.error(f"Failed to update paper with ID {paper_id}: {e}")
        raise e


def paper_delete(paper_id: str):
    """
    Deletes a paper along with its embedding and optionally its S3 file.

    Description:
        Removes the paper record from the "papers" table and the associated embedding from
        the "paper_embeddings" table. Optionally, deletes the corresponding file from S3.

    Parameters:
        paper_id (str): The unique identifier of the paper to delete.

    Returns:
        None

    Raises:
        Exception: If the paper is not found or if a database or S3 deletion error occurs.

    Example:
        paper_delete("1234abcd")
    """
    try:
        # First, retrieve the paper's file_url to use for the optional S3 deletion.
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT file_url FROM papers WHERE paper_id = %s;", (paper_id,))
                paper = cur.fetchone()
                if paper is None:
                    raise Exception(f"Paper with ID {paper_id} not found.")
                file_url = paper.get("file_url")

                # Delete the associated embeddings.
                cur.execute("DELETE FROM paper_embeddings WHERE paper_id = %s;", (paper_id,))
                # Delete the paper record.
                cur.execute("DELETE FROM papers WHERE paper_id = %s;", (paper_id,))
            conn.commit()
        logger.info(f"Successfully deleted paper with ID {paper_id} from the database.")

        # Optionally, delete the file from S3.
        if file_url:
            prefix = f"{MINIO_URL}/{BUCKET_NAME}/"
            if file_url.startswith(prefix):
                object_name = file_url[len(prefix) :]
                try:
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
                    logger.info(f"Successfully deleted file from S3: {file_url}")
                except Exception as s3_e:
                    logger.error(f"Error deleting file from S3 for paper {paper_id}: {s3_e}")
            else:
                logger.error(f"Invalid file URL, unable to delete from S3: {file_url}")
    except Exception as e:
        logger.error(f"Failed to delete paper with ID {paper_id}: {e}")
        raise e
