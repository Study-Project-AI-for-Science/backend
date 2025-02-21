import os
import pytest
import requests
from unittest.mock import patch, Mock

from modules.ollama.ollama import (
    _send_request_to_ollama,
    _extract_text_from_pdf,
    get_paper_embeddings,
    get_query_embeddings,
    get_paper_info,
    OLLAMA_MAX_RETRIES,
    OLLAMA_RETRY_DELAY,
)


# test _send_request_to_ollama
@pytest.fixture
def mock_ollama_response():
    """Simulates a valid Ollama API response returning a list of embeddings"""
    with patch("modules.ollama.ollama.requests.post") as mock_post:
        mock_response = Mock()
        # immitates the response from Ollama
        mock_response.json.return_value = {
            "embeddings": [0.1, 0.2, 0.3],
            "model_name": "name",
            "model_version": "version",
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        yield mock_response


def test_send_request_to_ollama_success(mock_ollama_response):
    """Test if _send_request_to_ollama successfully returns embeddings"""
    embeddings = _send_request_to_ollama("test prompt")
    assert embeddings == [0.1, 0.2, 0.3]


def test_send_request_to_ollama_error():
    """Test handling of API errors in _send_request_to_ollama."""
    with patch("modules.ollama.ollama.requests.post", side_effect=requests.exceptions.RequestException):
        embeddings = _send_request_to_ollama("test prompt")
        assert embeddings is None


# test _extract_text_from_pdf
@pytest.fixture
def test_pdf():
    """create temporary test pdf file"""
    pdf_path = "test.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"test pdf content")
    yield pdf_path
    os.remove(pdf_path)


def test_extract_text_from_pdf(test_pdf):
    """Ensures pdf text extraction works as intended"""
    with patch("modules.ollama.ollama.pymupdf.open") as mock_pymupdf:  # Updated to mock pymupdf.open
        mock_pymupdf.return_value.__enter__.return_value = [Mock(get_text=lambda: "test pdf content")]
        extracted_text = _extract_text_from_pdf(test_pdf)
        assert extracted_text == "test pdf content"


# Additional tests for _extract_text_from_pdf
def test_extract_text_from_pdf_file_not_found():
    """Test handling of non-existent PDF file"""
    with pytest.raises(FileNotFoundError):
        _extract_text_from_pdf("nonexistent.pdf")


def test_extract_text_from_pdf_parsing_error():
    """Test handling of PDF parsing errors"""
    with patch("modules.ollama.ollama.pymupdf.open", side_effect=Exception("PDF parsing error")):
        with pytest.raises(Exception) as exc_info:
            _extract_text_from_pdf("corrupted.pdf")
        assert "PDF parsing error" in str(exc_info.value)


# Additional tests for _send_request_to_ollama
def test_send_request_to_ollama_invalid_json():
    """Test handling of invalid JSON response"""
    with patch("modules.ollama.ollama.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"invalid": "response"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = _send_request_to_ollama("test prompt")
        assert result is None


def test_send_request_to_ollama_retry_mechanism():
    """Test that the retry mechanism works as expected"""
    with (
        patch("modules.ollama.ollama.requests.post") as mock_post,
        patch("modules.ollama.ollama.time.sleep") as mock_sleep,
    ):
        # First two calls fail, third succeeds
        mock_post.side_effect = [
            requests.exceptions.RequestException("Connection error"),
            requests.exceptions.RequestException("Connection error"),
            Mock(status_code=200, json=lambda: {"embeddings": [0.1, 0.2, 0.3]}),
        ]

        result = _send_request_to_ollama("test prompt")

        assert result == [0.1, 0.2, 0.3]
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(OLLAMA_RETRY_DELAY)


def test_send_request_to_ollama_timeout():
    """Test handling of timeout errors"""
    with patch("modules.ollama.ollama.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        result = _send_request_to_ollama("test prompt")
        assert result is None
        assert mock_post.call_count == OLLAMA_MAX_RETRIES


# test get_paper_embeddings
def test_get_paper_embeddings(mock_ollama_response, test_pdf):
    """checks if get_paper_embeddings() returns correct dict"""
    with patch("modules.ollama.ollama._extract_text_from_pdf", return_value="test pdf content"):
        result = get_paper_embeddings(test_pdf)
        assert result["embeddings"] == [0.1, 0.2, 0.3]
        assert isinstance(result["model_name"], str)
        assert isinstance(result["model_version"], str)


def test_get_paper_embeddings_empty_pdf():
    """Test handling of empty PDF content in get_paper_embeddings."""
    with patch("modules.ollama.ollama._extract_text_from_pdf", return_value=""):
        result = get_paper_embeddings("empty.pdf")
        assert result is None


# Additional edge cases for existing functions
def test_get_paper_embeddings_extraction_error():
    """Test handling of PDF extraction errors in get_paper_embeddings"""
    with patch("modules.ollama.ollama._extract_text_from_pdf", side_effect=Exception("Extraction error")):
        with pytest.raises(Exception) as exc_info:
            get_paper_embeddings("error.pdf")
        assert "Extraction error" in str(exc_info.value)


# test get_query_embeddings
def test_get_query_embeddings(mock_ollama_response):
    """Test successful embedding retrieval from a query string."""
    result = get_query_embeddings("What are you?")
    assert result == [0.1, 0.2, 0.3]


def test_get_query_embeddings_empty():
    """Test that an empty query string raises ValueError."""
    with pytest.raises(ValueError):
        get_query_embeddings("")


def test_get_query_embeddings_api_fail():
    """Test handling of API failure for query embeddings."""
    with patch("modules.ollama.ollama._send_request_to_ollama", return_value=None):
        result = get_query_embeddings("What are you?")
        assert result is None


def test_get_query_embeddings_with_whitespace():
    """Test that whitespace-only queries are handled correctly"""
    with pytest.raises(ValueError):
        get_query_embeddings("   \n   \t   ")


# Tests for get_paper_info
def test_get_paper_info_success():
    """Test successful paper info retrieval"""
    test_file = "test_paper.pdf"
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        result = get_paper_info(test_file)

        assert isinstance(result, dict)
        assert "title" in result
        assert "authors" in result
        assert isinstance(result["title"], str)
        assert isinstance(result["authors"], str)
        assert len(result["title"]) > 0
        assert len(result["authors"]) > 0


def test_get_paper_info_file_not_found():
    """Test handling of non-existent file in get_paper_info"""
    with pytest.raises(FileNotFoundError):
        get_paper_info("nonexistent.pdf")
