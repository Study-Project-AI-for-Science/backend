import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from modules.ollama.ollama_client import (
    get_paper_embeddings,
    get_query_embeddings,
    get_paper_info,
    _send_embed_request_to_ollama,
    OLLAMA_EMBEDDING_MODEL,
)
from modules.ollama.pdf_extractor import extract_text_from_pdf

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
    with patch("modules.ollama.pdf_extractor.partition_pdf") as mock_partition_pdf:
        # Create mock elements that will work properly with str() conversion
        element1 = MagicMock()
        element1.__str__.return_value = "test"
        element2 = MagicMock()
        element2.__str__.return_value = "pdf"
        element3 = MagicMock()
        element3.__str__.return_value = "content"

        mock_partition_pdf.return_value = [element1, element2, element3]

        extracted_text = extract_text_from_pdf(test_pdf)
        assert "test\npdf\ncontent" == extracted_text
        mock_partition_pdf.assert_called_once_with(filename=test_pdf)


def test_extract_text_from_pdf_file_not_found():
    """Test handling of non-existent PDF file"""
    with patch("modules.ollama.pdf_extractor.partition_pdf") as mock_partition_pdf:
        mock_partition_pdf.side_effect = FileNotFoundError("File not found")
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("nonexistent.pdf")


def test_get_paper_embeddings_success(mock_module_globals, test_pdf):
    """Test successful paper embedding generation"""
    _, mock_ollama_client = mock_module_globals

    with patch("modules.ollama.ollama_client.extract_pdf_content") as mock_extract_pdf_content:
        # Mock the extract_pdf_content function to return a list of content chunks
        mock_extract_pdf_content.return_value = [{"content": "test content"}]

        result = get_paper_embeddings(test_pdf)
        assert isinstance(result, dict)
        assert "embeddings" in result
        assert len(result["embeddings"]) > 0
        assert result["model_name"] == OLLAMA_EMBEDDING_MODEL

        mock_extract_pdf_content.assert_called_once_with(test_pdf)


def test_get_paper_embeddings_empty_pdf(mock_module_globals, test_pdf):
    """Test handling of empty PDF content"""
    _, mock_ollama_client = mock_module_globals

    with patch("modules.ollama.ollama_client.extract_pdf_content") as mock_extract_pdf_content:
        # Mock the extract_pdf_content function to return an empty list
        mock_extract_pdf_content.return_value = []

        result = get_paper_embeddings(test_pdf)
        assert result["embeddings"] == []

        mock_extract_pdf_content.assert_called_once_with(test_pdf)


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
    with (
        patch("os.path.exists") as mock_exists,
        patch("modules.ollama.ollama_client.pdfreader") as mock_pdfreader,
        patch("instructor.from_openai") as mock_instructor,
    ):
        # Mock exists to return True
        mock_exists.return_value = True

        # Mock pdfreader.PDFDocument to return a proper mock object
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Test Paper Title\nAuthor Name"
        mock_doc.pages = [mock_page]
        mock_pdfreader.PDFDocument.return_value = mock_doc

        # Mock instructor response
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.model_dump.return_value = {
            "title": "Test Paper Title",
            "authors": ["Author Name"],
            "field_of_study": "Computer Science",
            "journal": None,
            "publication_date": None,
            "doi": None,
            "keywords": [],
        }
        mock_client.chat.completions.create.return_value = mock_resp
        mock_instructor.return_value = mock_client

        result = get_paper_info(test_file)
        assert isinstance(result, dict)
        assert result["title"] == "Test Paper Title"
        assert "Author Name" in result["authors"]


def test_get_paper_info_file_not_found():
    """Test handling of non-existent file"""
    with pytest.raises(FileNotFoundError):
        get_paper_info("nonexistent.pdf")
