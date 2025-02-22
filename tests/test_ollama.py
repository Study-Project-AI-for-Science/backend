import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from modules.ollama.ollama_client import (
    get_paper_embeddings,
    get_query_embeddings,
    get_paper_info,
    _extract_text_from_pdf,
    _send_embed_request_to_ollama,
    OLLAMA_EMBEDDING_MODEL,
)

# Set test environment variable to prevent module initialization
os.environ["PYTEST_RUNNING"] = "1"


@pytest.fixture(autouse=True)
def mock_module_globals():
    """Mock module-level globals for all tests"""
    with (
        patch("modules.ollama.ollama_client.TOKENIZER") as mock_tokenizer,
        patch("modules.ollama.ollama_client.OLLAMA_CLIENT") as mock_ollama_client,
    ):
        # Set up mock tokenizer
        mock_encoded = MagicMock()
        mock_encoded.__getitem__.return_value = np.array([1, 2, 3])
        mock_tokenizer.encode.return_value = mock_encoded

        # Set up mock Ollama client
        mock_ollama_client.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}

        yield mock_tokenizer, mock_ollama_client


@pytest.fixture
def test_pdf():
    """Create temporary test pdf file"""
    pdf_path = "test.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"test pdf content")
    yield pdf_path
    os.remove(pdf_path)


def test_send_embed_request_success(mock_module_globals):
    """Test successful embedding request"""
    _, mock_ollama_client = mock_module_globals
    result = _send_embed_request_to_ollama("test prompt", OLLAMA_EMBEDDING_MODEL)
    assert result == [0.1, 0.2, 0.3]
    mock_ollama_client.embeddings.assert_called_once()


def test_send_embed_request_failure(mock_module_globals):
    """Test handling of failed embedding request"""
    _, mock_ollama_client = mock_module_globals
    mock_ollama_client.embeddings.side_effect = Exception("Connection failed")
    result = _send_embed_request_to_ollama("test prompt", OLLAMA_EMBEDDING_MODEL)
    assert result is None


def test_extract_text_from_pdf(test_pdf):
    """Test PDF text extraction"""
    with patch("pymupdf.open") as mock_pymupdf:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "test pdf content"
        mock_doc.__enter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        extracted_text = _extract_text_from_pdf(test_pdf)
        assert extracted_text == "test pdf content"


def test_extract_text_from_pdf_file_not_found():
    """Test handling of non-existent PDF file"""
    with pytest.raises(FileNotFoundError):
        _extract_text_from_pdf("nonexistent.pdf")


def test_get_paper_embeddings_success(mock_module_globals, test_pdf):
    """Test successful paper embedding generation"""
    _, mock_ollama_client = mock_module_globals
    with patch("pymupdf.open") as mock_pymupdf:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "test content"
        mock_doc.__enter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        result = get_paper_embeddings(test_pdf)
        assert isinstance(result, dict)
        assert "embeddings" in result
        assert len(result["embeddings"]) > 0
        assert result["model_name"] == OLLAMA_EMBEDDING_MODEL


def test_get_paper_embeddings_empty_pdf(mock_module_globals, test_pdf):
    """Test handling of empty PDF content"""
    _, mock_ollama_client = mock_module_globals
    with patch("pymupdf.open") as mock_pymupdf:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.__enter__.return_value = [mock_page]
        mock_pymupdf.return_value = mock_doc

        result = get_paper_embeddings(test_pdf)
        assert result["embeddings"] == []


def test_get_query_embeddings_success(mock_module_globals):
    """Test successful query embedding generation"""
    _, mock_ollama_client = mock_module_globals
    result = get_query_embeddings("test query")
    assert result == [0.1, 0.2, 0.3]
    mock_ollama_client.embeddings.assert_called_once()


def test_get_query_embeddings_empty():
    """Test that empty query raises ValueError"""
    with pytest.raises(ValueError):
        get_query_embeddings("")


def test_get_query_embeddings_whitespace():
    """Test that whitespace-only query raises ValueError"""
    with pytest.raises(ValueError):
        get_query_embeddings("   \n   \t   ")


def test_get_paper_info_success():
    """Test successful paper info retrieval"""
    test_file = "test_paper.pdf"
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        result = get_paper_info(test_file)
        assert isinstance(result, dict)
        assert "title" in result
        assert "authors" in result


def test_get_paper_info_file_not_found():
    """Test handling of non-existent file"""
    with pytest.raises(FileNotFoundError):
        get_paper_info("nonexistent.pdf")
