import pytest
from unittest.mock import patch, MagicMock
from modules.database.database import (
    paper_find,
    paper_insert,
    paper_update,
    paper_delete,
    paper_list_all,
    paper_get_similar_to_query,
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
    """Test successful paper insertion"""
    cursor = mock_psycopg.connect().cursor().__enter__()
    cursor.fetchone.side_effect = [None]  # Only need None for duplicate check
    mock_storage.upload_file.return_value = TEST_FILE_URL
    mock_ollama.get_paper_embeddings.return_value = {
        "embeddings": [[0.1, 0.2], [0.2, 0.3]],
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

    assert cursor.execute.call_count >= 2
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
