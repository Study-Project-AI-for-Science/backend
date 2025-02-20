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

)

# test _send_request_to_ollama
@pytest.fixture
def mock_ollama_response():
    """Simulates a valid Ollama API response returning a list of embeddings"""
    with patch("modules.ollama.ollama.requests.post") as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"embeddings": [0.1,0.2,0.3], "model_name": "name", "model_version": "version"} # immitates the response from Ollama
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
    with patch("modules.ollama.ollama.fitz.open") as mock_fitz: # mocks fitz.open() to prevent actual file reading
        mock_fitz.return_value.__enter__.return_value = [Mock(get_text=lambda: "test pdf content")]
        extracted_text = _extract_text_from_pdf(test_pdf)
        assert extracted_text == "test pdf content"

# test get_paper_embeddings
def test_get_paper_embeddings(mock_ollama_response, test_pdf):
    """checks if get_paper_embeddings() returns correct dict """
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
