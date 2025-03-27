"""
database.py

This module provides a unified interface for handling database operations for papers and
their embeddings. It handles interactions with PostgreSQL for storing paper metadata and embeddings.
"""

import os
import hashlib
import psycopg
from psycopg.rows import dict_row
import logging
from dotenv import load_dotenv
from uuid_extensions import uuid7str as uuid7

from modules.ollama import ollama_client
from modules.storage import storage

import tempfile
import shutil

load_dotenv()

# Configure logging for debugging and error tracking.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


class PaperNotFoundError(Exception):
    """Exception raised when a paper is not found in the database."""

    pass


class FileHashError(Exception):
    """Exception raised when computing a file's hash fails."""

    pass


class DatabaseError(Exception):
    """Base exception for database-related errors."""

    pass


class EmbeddingNotFoundError(Exception):
    """Exception raised when embeddings are not found for a paper."""

    pass


class InvalidUpdateError(Exception):
    """Exception raised when attempting to update a paper with invalid fields."""

    pass


class DuplicatePaperError(Exception):
    """Exception raised when attempting to insert a paper that already exists."""

    pass


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
        FileHashError: If there is any error during file reading or hash computation.

    Example:
        file_hash = _paper_compute_file_hash("/path/to/file.pdf")
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
    except (IOError, OSError) as e:
        logger.error(f"Error computing file hash for {file_path}: {e}")
        raise FileHashError(f"Failed to compute hash for {file_path}: {str(e)}") from e

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
    query = "SELECT * FROM papers WHERE id = %s;"

    try:
        # Connect to the database using psycopg and set row factory for dict output.
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (paper_id,))
                paper = cur.fetchone()

        if paper is None:
            logger.error(f"Paper with ID {paper_id} not found.")
            raise PaperNotFoundError(f"Paper with ID {paper_id} not found.")

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

    storage.download_file(file_url, destination_path)


def paper_get_embeddings(paper_id: str) -> dict:
    """
    Retrieves a paper's embeddings and associated metadata from the "paper_embeddings" table.

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
            raise EmbeddingNotFoundError(f"No embeddings found for paper ID {paper_id}")
        return result
    except psycopg.Error as e:
        logger.error(f"Error retrieving embeddings for paper {paper_id}: {e}")
        raise DatabaseError(f"Database error while retrieving embeddings: {str(e)}") from e


def paper_insert(
    file_path: str,
    title: str,
    authors: str,
    abstract: str = None,
    paper_url: str = None,
    published: str = None,
    updated: str = None,
    markdown_content: str = None,
):
    """
    Inserts a new paper and its embedding(s) into the database.

    Description:
        Computes the file hash, uploads the paper to S3, generates one or more embeddings,
        and inserts the paper's metadata into the "papers" table and each embedding into the
        "paper_embeddings" table.

    Parameters:
        file_path (str): The local path to the PDF file.
        title (str): The title of the paper.
        authors (str): The authors of the paper.
        abstract (str, optional): The abstract of the paper.
        paper_url (str, optional): The URL where the paper is available online.
        published (str, optional): The publication date of the paper.
        updated (str, optional): The last update date of the paper.
        markdown_content (str, optional): The full text content of the paper in markdown format.

    Returns:
        The paper_id (str) of the newly inserted paper.

    Raises:
        DuplicatePaperError: If a paper with the same hash already exists.
        FileHashError: If computing the file hash fails.
        S3UploadError: If uploading the file to S3 fails.
        DatabaseError: If a database error occurs during insertion.

    Example:
        paper_id = paper_insert("/path/to/file.pdf", "Title", "Author A, Author B")
    """
    try:
        # Compute file hash
        file_hash = _paper_compute_file_hash(file_path)

        # Check if a paper with this hash already exists
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, authors FROM papers WHERE file_hash = %s", (file_hash,))
                existing_paper = cur.fetchone()

                if existing_paper:
                    logger.info(f"Paper with hash {file_hash} already exists (ID: {existing_paper['id']})")
                    raise DuplicatePaperError(
                        f"This paper appears to be already in the database with ID: {existing_paper['id']}, "
                        f"title: '{existing_paper['title']}', authors: '{existing_paper['authors']}'"
                    )

        # Upload file to S3
        file_url = storage.upload_file(file_path)

        # If title or authors is empty, fill missing info using paper_get_info
        if not title or not authors:
            info = ollama_client.get_paper_info(file_path)
            if not title:
                title = info.get("title", title)
            if not authors:
                authors = info.get("authors", authors)
            if not abstract:
                abstract = info.get("abstract", abstract)

        # Generate embeddings using the file directly
        embedding_info = ollama_client.get_paper_embeddings(file_path)
        embeddings = embedding_info.get("embeddings", [])
        model_name = embedding_info.get("model_name", "")
        model_version = embedding_info.get("model_version", "")

        if not embeddings:
            # Fallback to a dummy embedding if the generation fails
            embeddings = [[0.0] * 1024]

        # Handle empty date strings by converting them to None
        if published == "":
            published = None
        if updated == "":
            updated = None

        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Generate a new UUID7 for the paper
                paper_id = uuid7()

                paper_insert_query = """
                    INSERT INTO papers (id, title, authors, file_url, file_hash,
                                        abstract, online_url, published_date, updated_date, content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(
                    paper_insert_query,
                    (paper_id, title, authors, file_url, file_hash, abstract, paper_url, published, updated, markdown_content),
                )

                # Insert one record per embedding
                embed_insert_query = """
                    INSERT INTO paper_embeddings (paper_id, embedding, model_name, model_version)
                    VALUES (%s, %s, %s, %s);
                """
                for emb in embeddings:
                    cur.execute(embed_insert_query, (paper_id, emb, model_name, model_version))
            conn.commit()

        logger.info(f"Successfully inserted paper with ID {paper_id}")
        return paper_id

    except (DuplicatePaperError, FileHashError, storage.S3UploadError) as e:
        logger.error(f"Failed to insert paper: {e}")
        raise
    except psycopg.Error as e:
        logger.error(f"Failed to insert paper: {e}")
        raise DatabaseError(f"Database error while inserting paper: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error while inserting paper: {e}")
        raise DatabaseError(f"Failed to insert paper: {str(e)}") from e


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
                               (pe.embedding <=> %s::vector) AS similarity
                        FROM paper_embeddings pe
                        JOIN papers p ON p.id = pe.paper_id
                        WHERE (pe.embedding <=> %s::vector) <= %s
                        ORDER BY (pe.embedding <=> %s::vector)
                        LIMIT %s;
                    """
                    cur.execute(query, (query_embedding, query_embedding, similarity_dropout, query_embedding, limit))
                else:
                    query = """
                        SELECT p.*,
                               pe.embedding,
                               pe.model_name,
                               pe.model_version,
                               pe.created_at,
                               (pe.embedding <=> %s::vector) AS similarity
                        FROM paper_embeddings pe
                        JOIN papers p ON p.id = pe.paper_id
                        ORDER BY (pe.embedding <=> %s::vector)
                        LIMIT %s;
                    """
                    cur.execute(query, (query_embedding, query_embedding, limit))
                results = cur.fetchall()
        if not results:
            logger.info("No similar papers found for the provided query embedding.")
        return results
    except psycopg.Error as e:
        logger.error(f"Error executing similarity search for query embedding: {e}")
        raise DatabaseError(f"Database error while performing similarity search: {str(e)}") from e


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
        InvalidUpdateError: If an invalid field is provided or no valid fields are provided.
        PaperNotFoundError: If the paper is not found.
        DatabaseError: If a database error occurs.

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
            raise InvalidUpdateError(f"Invalid field for update: {field}")
        set_clauses.append(f"{field} = %s")
        params.append(value)

    if not set_clauses:
        raise InvalidUpdateError("No valid fields provided to update.")

    # Construct the SQL query.
    set_clause = ", ".join(set_clauses)
    query = f"UPDATE papers SET {set_clause} WHERE id = %s RETURNING *;"
    params.append(paper_id)

    try:
        # Connect to the database and perform the update in a transaction.
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                updated_record = cur.fetchone()
                if updated_record is None:
                    raise PaperNotFoundError(f"Paper with ID {paper_id} not found.")
            conn.commit()
        logger.info(f"Successfully updated paper with ID {paper_id}")
        return updated_record
    except PaperNotFoundError as e:
        logger.error(f"Failed to update paper with ID {paper_id}: {e}")
        raise
    except psycopg.Error as e:
        logger.error(f"Failed to update paper with ID {paper_id}: {e}")
        raise DatabaseError(f"Database error while updating paper: {str(e)}") from e


def paper_delete(paper_id: str):
    """
    Deletes a paper along with its embedding, references, and S3 file.

    Description:
        Removes the paper record from the "papers" table, the associated embedding from
        the "paper_embeddings" table, the associated references from the "paper_references" table,
        and deletes the corresponding file from S3.

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
        # First, retrieve the paper's file_url to use for S3 deletion
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT file_url FROM papers WHERE id = %s;", (paper_id,))
                paper = cur.fetchone()
                if paper is None:
                    raise PaperNotFoundError(f"Paper with ID {paper_id} not found.")
                file_url = paper.get("file_url")

                # Delete the associated embeddings
                cur.execute("DELETE FROM paper_embeddings WHERE paper_id = %s;", (paper_id,))
                # Delete the associated references
                cur.execute("DELETE FROM paper_references WHERE paper_id = %s;", (paper_id,))
                # Delete the paper record
                cur.execute("DELETE FROM papers WHERE id = %s;", (paper_id,))
            conn.commit()
        logger.info(f"Successfully deleted paper with ID {paper_id} from the database.")

        # Delete the file from S3
        if file_url:
            try:
                storage.delete_file(file_url)
            except (ValueError, storage.S3UploadError) as e:
                logger.error(f"Error deleting file from S3 for paper {paper_id}: {e}")
                raise
    except PaperNotFoundError as e:
        logger.error(f"Failed to delete paper with ID {paper_id}: {e}")
        raise
    except psycopg.Error as e:
        logger.error(f"Failed to delete paper with ID {paper_id}: {e}")
        raise DatabaseError(f"Database error while deleting paper: {str(e)}") from e


def paper_list_all(page: int = 1, page_size: int = 10) -> dict:
    """
    Retrieves a paginated list of all papers from the database.

    Description:
        Returns a list of papers with basic metadata, ordered by creation date,
        with pagination support.

    Parameters:
        page (int): The page number to retrieve (1-based). Defaults to 1.
        page_size (int): The number of papers per page. Defaults to 10.

    Returns:
        dict: A dictionary containing:
            - papers: List of paper records
            - total: Total number of papers
            - page: Current page number
            - total_pages: Total number of pages

    Example:
        result = paper_list_all(page=2, page_size=20)
    """
    try:
        offset = (page - 1) * page_size

        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute("SELECT COUNT(*) as total FROM papers;")
                total = cur.fetchone()["total"]

                # Get paginated results with additional metadata fields
                query = """
                    SELECT id, title, authors, file_url, abstract, online_url,
                           published_date, updated_date, created_at
                    FROM papers
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s;
                """
                cur.execute(query, (page_size, offset))
                papers = cur.fetchall()

                total_pages = (total + page_size - 1) // page_size  # Ceiling division

                return {"papers": papers, "total": total, "page": page, "total_pages": total_pages}
    except psycopg.Error as e:
        logger.error(f"Error retrieving paper list: {e}")
        raise DatabaseError(f"Database error while retrieving paper list: {str(e)}") from e


# References


def paper_references_insert_many(paper_id: str, references: list):
    """
    Inserts multiple reference entries for a paper into the database.

    Description:
        Takes a list of references and associates them with the specified paper by
        inserting records into the "paper_references" table. When a reference contains
        an ArXiv ID, the referenced paper is downloaded, processed, and stored in the
        database, with its paper_id added to the reference metadata.

    Parameters:
        paper_id (str): The unique identifier of the paper that contains the references.
        references (list): A list of dictionaries, each containing reference metadata in BibTeX format:
                           - id (str): The citation key of the reference
                           - type (str): The type of reference (e.g., 'article', 'inproceedings')
                           - title (str): The title of the referenced paper
                           - author (str): The authors of the referenced paper
                           - raw_bibtex (str): The raw BibTeX entry
                           - Additional fields (e.g., booktitle, journal, year, etc.)

    Returns:
        int: The number of references successfully inserted.

    Raises:
        PaperNotFoundError: If the paper with the given ID does not exist.
        DatabaseError: If there is an error executing the database operations.
        ValueError: If the references list is empty or not properly formatted.

    Example:
        references = [
            {
                "id": "turbo",
                "type": "inproceedings",
                "title": "Adversarial diffusion distillation",
                "author": "Sauer, Axel and Lorenz, Dominik and Blattmann, Andreas and Rombach, Robin",
                "booktitle": "European Conference on Computer Vision",
                "pages": "87--103",
                "year": "2024",
                "organization": "Springer",
                "raw_bibtex": "@inproceedings{turbo, title={Adversarial diffusion distillation},\n  author={Sauer, Axel and Lorenz, Dominik and Blattmann, Andreas and Rombach, Robin},\n  booktitle={European Conference on Computer Vision},\n  pages={87--103},\n  year={2024},\n  organization={Springer}\n}}"
            }
        ]
        inserted_count = paper_references_insert_many("1234abcd", references)
    """  # noqa: E501
    if not references:
        logger.warning(f"No references provided for paper ID {paper_id}")
        return 0

    # Validate the structure of references
    for i, ref in enumerate(references):
        # Check if ref is a dictionary
        if not isinstance(ref, dict):
            error_msg = f"Reference at index {i} is not a dictionary"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check for required fields
        if "title" not in ref:
            ref["title"] = "Unknown Title"
            logger.warning(f"Reference at index {i} is missing title, using default")

        if "author" not in ref:
            ref["author"] = "Unknown Authors"
            logger.warning(f"Reference at index {i} is missing author, using default")

    # Create a temporary directory for downloading referenced papers
    temp_dir = tempfile.mkdtemp()
    logger.info(f"Created temporary directory for reference processing: {temp_dir}")

    try:
        # Process references that have ArXiv IDs
        for ref in references:
            try:
                # Process reference with ArXiv ID and get paper_id if successful
                ref_paper_id = _process_reference_with_arxiv_id(ref, temp_dir)

                # If a paper was successfully inserted, add its ID to the reference
                if ref_paper_id:
                    ref["paper_id"] = ref_paper_id
                    logger.info(f"Added paper_id {ref_paper_id} to reference {ref.get('title', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error processing reference with ArXiv ID: {str(e)}")
                # Continue with other references even if this one failed

        # Check if the paper exists
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM papers WHERE id = %s", (paper_id,))
                if cur.fetchone() is None:
                    raise PaperNotFoundError(f"Paper with ID {paper_id} not found.")

                # Prepare values for batch insertion
                values = []
                for ref in references:
                    # Prepare batch insert
                    ref_paper_id = ref.get("paper_id", None)
                    insert_query = """
                        INSERT INTO paper_references (id, title, authors, fields, paper_id, reference_paper_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """

                    # Generate a new UUID for each reference instead of using citation key
                    # This fixes the "invalid input syntax for type uuid" error
                    ref_id = uuid7()

                    # Copy all fields except certain ones to the fields dictionary
                    fields = {k: v for k, v in ref.items() if k not in ["id", "title", "author"]}

                    # Store the original citation key in the fields if it exists
                    if "id" in ref:
                        fields["citation_key"] = ref["id"]

                    values.append(
                        (
                            ref_id,
                            ref["title"],
                            ref["author"],  # Use "author" field instead of "authors"
                            psycopg.types.json.Json(fields),  # Convert to JSON
                            paper_id,
                            ref_paper_id,
                        )
                    )

                # Execute batch insert
                cur.executemany(insert_query, values)
                inserted_count = cur.rowcount

            conn.commit()

        logger.info(f"Successfully inserted {inserted_count} references for paper ID {paper_id}")
        return inserted_count

    except PaperNotFoundError as e:
        logger.error(f"Error inserting references for paper {paper_id}: {e}")
        raise
    except psycopg.Error as e:
        logger.error(f"Database error while inserting references for paper {paper_id}: {e}")
        raise DatabaseError(f"Database error while inserting references: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error while inserting references for paper {paper_id}: {e}")
        raise DatabaseError(f"Failed to insert references: {str(e)}") from e
    finally:
        # Clean up temporary directory
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")


def paper_references_list(paper_id: str) -> list:
    """
    Retrieves all references for a specific paper from the database.

    Description:
        Queries the "paper_references" table to find all papers that are referenced
        by the paper with the given `paper_id`.

    Parameters:
        paper_id (str): The unique identifier of the paper.

    Returns:
        list: A list of dictionaries containing reference paper metadata.

    Raises:
        PaperNotFoundError: If the paper with the given ID does not exist.
        DatabaseError: If a database error occurs during query execution.

    Example:
        references = paper_references_list("1234abcd")
    """
    try:
        # First check if the paper exists
        with psycopg.connect(POSTGRES_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM papers WHERE id = %s", (paper_id,))
                if cur.fetchone() is None:
                    raise PaperNotFoundError(f"Paper with ID {paper_id} not found.")

                # Query to get all references for the paper
                query = """
                    SELECT pr.*
                    FROM paper_references pr
                    WHERE pr.paper_id = %s
                """
                cur.execute(query, (paper_id,))
                references = cur.fetchall()

                return references

    except PaperNotFoundError as e:
        logger.error(f"Error retrieving references for paper {paper_id}: {e}")
        raise
    except psycopg.Error as e:
        logger.error(f"Database error while retrieving references for paper {paper_id}: {e}")
        raise DatabaseError(f"Database error while retrieving references: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error while retrieving references for paper {paper_id}: {e}")
        raise DatabaseError(f"Failed to retrieve references: {str(e)}") from e


def _process_reference_with_arxiv_id(reference: dict, temp_dir: str) -> str:
    """
    Process a reference that contains an ArXiv ID by downloading and adding it to the system.

    Description:
        Extracts ArXiv IDs from the reference metadata, downloads the paper if an ID is found,
        and inserts it into the database using the standard paper_insert process.

    Parameters:
        reference (dict): A dictionary containing reference metadata in BibTeX format.
        temp_dir (str): A temporary directory where the referenced paper will be downloaded.

    Returns:
        str: The paper_id of the newly inserted paper if successful, None otherwise.

    Example:
        paper_id = _process_reference_with_arxiv_id(reference, "/tmp/ref_papers")
    """
    from modules.retriever.arxiv import arxiv_retriever

    # Search through all keys and values in the reference dictionary for ArXiv IDs
    arxiv_ids = []
    for key, value in reference.items():
        if isinstance(value, str):
            arxiv_ids.extend(arxiv_retriever.extract_arxiv_ids(value))
        if isinstance(key, str):
            arxiv_ids.extend(arxiv_retriever.extract_arxiv_ids(key))

    if not arxiv_ids:
        return None

    # Use the first found ArXiv ID
    arxiv_id = arxiv_ids[0]
    logger.info(f"Found ArXiv ID {arxiv_id} in reference {reference.get('title', 'Unknown')}")

    try:
        # Download the paper with the ArXiv ID
        paper_path = arxiv_retriever.paper_download_arxiv_id(arxiv_id, temp_dir)

        # Get metadata from the downloaded paper
        paper_metadata = arxiv_retriever.paper_get_metadata(paper_path)

        # Insert the paper into the database
        paper_id = paper_insert(
            file_path=paper_path,
            title=paper_metadata.get("title", reference.get("title", "Unknown Title")),
            authors=paper_metadata.get("authors", reference.get("author", "Unknown Authors")),
            abstract=paper_metadata.get("abstract", ""),
            paper_url=paper_metadata.get("url", ""),
            published=paper_metadata.get("published_date", ""),
            updated=paper_metadata.get("updated_date", ""),
        )

        logger.info(f"Successfully processed reference with ArXiv ID {arxiv_id}, inserted as paper {paper_id}")
        return paper_id
    except Exception as e:
        logger.error(f"Error processing reference with ArXiv ID {arxiv_id}: {str(e)}")
        return None
