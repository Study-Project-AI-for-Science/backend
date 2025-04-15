import pytest
import datetime
from unittest.mock import patch, MagicMock
from modules.database.database import (
    paper_find,
    paper_insert,
    paper_update,
    paper_delete,
    paper_list_all,
    paper_get_similar_to_query,
    paper_references_insert_many,
    paper_references_list,
    PaperNotFoundError,
    DuplicatePaperError,
)

# Test data
TEST_PAPER_ID = "123e4567-e89b-12d3-a456-426614174000"
TEST_FILE_PATH = "test.pdf"
TEST_TITLE = "Test Paper"
TEST_AUTHORS = "Test Author"
TEST_FILE_URL = "http://localhost:9000/papers/123/test.pdf"
TEST_FILE_HASH = "abcdef1234567890"
TEST_ABSTRACT = "This is a test paper abstract"
TEST_PAPER_URL = "http://example.com/paper"
TEST_PUBLISHED = datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
TEST_UPDATED = datetime.datetime(2023, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
TEST_MARKDOWN_CONTENT = "# Test Paper\n\nThis is a test markdown content for the paper."


@pytest.fixture
def mock_psycopg():
    with patch("modules.database.database.psycopg") as mock:
        # Create mock cursor and connection
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Configure connect to return our mock connection
        mock.connect.return_value = mock_conn

        # Mock psycopg.Error
        mock.Error = Exception

        yield mock


@pytest.fixture
def mock_storage():
    with patch("modules.database.database.storage") as mock:
        yield mock


@pytest.fixture
def mock_ollama():
    with patch("modules.database.database.ollama_client") as mock:
        mock.get_paper_embeddings.return_value = {
            "embeddings": [[0.1, 0.2]],
            "model_name": "test-model",
            "model_version": "1.0",
        }
        yield mock


@pytest.fixture
def mock_file_hash():
    with patch("modules.database.database._paper_compute_file_hash") as mock:
        mock.return_value = TEST_FILE_HASH
        yield mock


@pytest.fixture
def sample_paper():
    return {
        "id": TEST_PAPER_ID,
        "title": TEST_TITLE,
        "authors": TEST_AUTHORS,
        "file_url": TEST_FILE_URL,
        "file_hash": TEST_FILE_HASH,
        "abstract": TEST_ABSTRACT,
        "online_url": TEST_PAPER_URL,
        "published_date": TEST_PUBLISHED,
        "updated_date": TEST_UPDATED,
        "content": TEST_MARKDOWN_CONTENT,
    }


def test_paper_find_success(mock_psycopg, sample_paper):
    """Test successful paper retrieval"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = sample_paper

    result = paper_find(TEST_PAPER_ID)
    assert result == sample_paper
    cursor.execute.assert_called_once()


def test_paper_find_not_found(mock_psycopg):
    """Test paper retrieval when paper doesn't exist"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = None

    with pytest.raises(PaperNotFoundError):
        paper_find(TEST_PAPER_ID)


def test_paper_insert_success(mock_psycopg, mock_storage, mock_ollama, mock_file_hash, sample_paper):
    """Test successful paper insertion with all fields including markdown content"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.side_effect = [None]  # Only need None for duplicate check
    mock_storage.upload_file.return_value = TEST_FILE_URL
    mock_ollama.get_paper_embeddings.return_value = {
        "embeddings": [[0.1, 0.2], [0.2, 0.3]],
        "model_name": "test-model",
        "model_version": "1.0",
    }

    # Mock the UUID7 function to return a predictable ID
    with patch("modules.database.database.uuid7", return_value=TEST_PAPER_ID):
        result = paper_insert(
            TEST_FILE_PATH,
            TEST_TITLE,
            TEST_AUTHORS,
            abstract=TEST_ABSTRACT,
            paper_url=TEST_PAPER_URL,
            published=TEST_PUBLISHED,
            updated=TEST_UPDATED,
            markdown_content=TEST_MARKDOWN_CONTENT,
        )

    # Verify the result is a UUID string
    assert isinstance(result, str)
    assert result == TEST_PAPER_ID  # Should match our mocked UUID

    mock_storage.upload_file.assert_called_once_with(TEST_FILE_PATH)
    mock_ollama.get_paper_embeddings.assert_called_once()

    # Verify correct SQL execution calls
    assert cursor.execute.call_count >= 2

    # Find the SQL insert statement in the execute calls
    # First call is the duplicate check, second call should be the insert
    insert_found = False
    for call in cursor.execute.call_args_list:
        sql = call[0][0]
        if "INSERT INTO papers" in sql and "content" in sql:
            insert_found = True
            break

    assert insert_found, "No INSERT INTO papers statement found in the SQL calls"


def test_paper_insert_minimal(mock_psycopg, mock_storage, mock_ollama, mock_file_hash):
    """Test paper insertion with only required fields"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.side_effect = [None]  # Only need None for duplicate check
    mock_storage.upload_file.return_value = TEST_FILE_URL
    mock_ollama.get_paper_embeddings.return_value = {
        "embeddings": [[0.1, 0.2]],
        "model_name": "test-model",
        "model_version": "1.0",
    }

    result = paper_insert(TEST_FILE_PATH, TEST_TITLE, TEST_AUTHORS)

    # Verify the result is a UUID string
    assert isinstance(result, str)
    assert len(result) == 36  # UUID string length
    assert result.count("-") == 4  # UUID format check

    mock_storage.upload_file.assert_called_once_with(TEST_FILE_PATH)
    mock_ollama.get_paper_embeddings.assert_called_once()
    assert cursor.execute.call_count >= 2


def test_paper_insert_duplicate(mock_psycopg, mock_file_hash, sample_paper):
    """Test paper insertion with duplicate file"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = sample_paper  # Return existing paper for duplicate check

    with pytest.raises(DuplicatePaperError):
        paper_insert(TEST_FILE_PATH, TEST_TITLE, TEST_AUTHORS)


def test_paper_update_success(mock_psycopg, sample_paper):
    """Test successful paper update"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    updated_paper = {**sample_paper, "title": "Updated Title"}
    cursor.fetchone.return_value = updated_paper

    result = paper_update(TEST_PAPER_ID, title="Updated Title")
    assert result == updated_paper
    cursor.execute.assert_called_once()


def test_paper_update_not_found(mock_psycopg):
    """Test paper update when paper doesn't exist"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = None

    with pytest.raises(PaperNotFoundError):
        paper_update(TEST_PAPER_ID, title="Updated Title")


def test_paper_delete_success(mock_psycopg, mock_storage, sample_paper):
    """Test successful paper deletion"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = sample_paper

    paper_delete(TEST_PAPER_ID)

    assert cursor.execute.call_count >= 3  # Should have 3 delete queries now (embeddings, references, paper)
    mock_storage.delete_file.assert_called_once_with(TEST_FILE_URL)


def test_paper_delete_not_found(mock_psycopg):
    """Test paper deletion when paper doesn't exist"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = None

    with pytest.raises(PaperNotFoundError):
        paper_delete(TEST_PAPER_ID)


def test_paper_list_all(mock_psycopg, sample_paper):
    """Test paper listing with pagination"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = {"total": 1}
    cursor.fetchall.return_value = [sample_paper]

    result = paper_list_all(page=1, page_size=10)
    assert result["papers"] == [sample_paper]
    assert result["total"] == 1
    assert result["page"] == 1
    assert result["total_pages"] == 1


def test_paper_get_similar_to_query(mock_psycopg, sample_paper):
    """Test similarity search"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    sample_result = {**sample_paper, "similarity": 0.95}
    cursor.fetchall.return_value = [sample_result]

    query_embedding = [0.1, 0.2, 0.3]
    results = paper_get_similar_to_query(query_embedding, limit=10)
    assert results == [sample_result]
    cursor.execute.assert_called_once()


def test_paper_references_insert_many(mock_psycopg):
    """Test inserting references for a paper"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = {"id": TEST_PAPER_ID}  # Paper exists
    cursor.rowcount = 2  # Two references inserted

    references = [
        {
            "id": "ref1",
            "type": "article",
            "title": "Test Reference 1",
            "author": "Author 1",
            "year": "2023",
            "raw_bibtex": "@article{ref1, title={Test Reference 1}, author={Author 1}, year={2023}}",
        },
        {
            "id": "ref2",
            "type": "inproceedings",
            "title": "Test Reference 2",
            "author": "Author 2",
            "year": "2022",
            "raw_bibtex": "@inproceedings{ref2, title={Test Reference 2}, author={Author 2}, year={2022}}",
        },
    ]

    result = paper_references_insert_many(TEST_PAPER_ID, references)

    assert result == 2
    assert cursor.executemany.called


def test_paper_references_insert_many_no_paper(mock_psycopg):
    """Test inserting references for a non-existent paper"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = None  # Paper does not exist

    references = [{"id": "ref1", "title": "Test Reference", "author": "Test Author"}]

    with pytest.raises(PaperNotFoundError):
        paper_references_insert_many(TEST_PAPER_ID, references)


def test_paper_references_list(mock_psycopg):
    """Test getting references for a paper"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.return_value = {"id": TEST_PAPER_ID}  # Paper exists

    test_references = [{"id": "ref1", "title": "Reference 1", "authors": "Author 1"}, {"id": "ref2", "title": "Reference 2", "authors": "Author 2"}]
    cursor.fetchall.return_value = test_references

    result = paper_references_list(TEST_PAPER_ID)

    assert result == test_references
    assert len(cursor.execute.call_args_list) == 2  # Two execute calls
