import pytest
from unittest.mock import patch, MagicMock
from modules.Retriever.arxiv.arxiv_retriever import (
    paper_get_metadata,
    paper_download_arxiv_id,
    paper_download_arxiv_metadata,
    extract_arxiv_ids,
    ArxivPaperNotFoundError,
    ArxivDownloadError,
)

# Test data
TEST_ARXIV_ID = "2401.00123"
TEST_AUTHORS = "Test Author"
TEST_TITLE = "Test Paper"
TEST_OUTPUT_DIR = "/tmp"
TEST_PDF_PATH = "/tmp/test.pdf"


@pytest.fixture
def mock_arxiv_client():
    with patch("modules.Retriever.arxiv.arxiv_retriever.client") as mock:
        yield mock


@pytest.fixture
def mock_arxiv():
    with patch("modules.Retriever.arxiv.arxiv_retriever.arxiv") as mock:
        # Set up mock paper result
        mock_paper = MagicMock()
        mock_paper.title = TEST_TITLE
        # Create proper author mock with name attribute
        author_mock = MagicMock()
        author_mock.name = TEST_AUTHORS
        mock_paper.authors = [author_mock]
        mock_paper.summary = "Test abstract"
        mock_paper.entry_id = f"http://arxiv.org/abs/{TEST_ARXIV_ID}"
        mock_paper.get_short_id.return_value = TEST_ARXIV_ID
        mock_paper.published = "2024-01-01"
        mock_paper.updated = "2024-01-01"
        mock_paper.download_pdf.return_value = TEST_PDF_PATH

        # Store the mock paper for tests to access
        mock._paper = mock_paper

        # Set up Search class mock
        mock.Search = MagicMock()
        mock.Search.return_value = "mock_search"

        # Set up sort enums
        mock.SortCriterion = MagicMock()
        mock.SortCriterion.Relevance = "relevance"
        mock.SortOrder = MagicMock()
        mock.SortOrder.Descending = "descending"

        # Configure query to return our mock paper
        mock.query.return_value = iter([mock_paper])
        yield mock


@pytest.fixture
def mock_pymupdf():
    with patch("modules.Retriever.arxiv.arxiv_retriever.pymupdf") as mock:
        # Create a mock document with proper page count
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.load_page.return_value.get_text.return_value = f"Test content {TEST_ARXIV_ID}"

        # Configure open to return our mock document
        mock.open.return_value = mock_doc
        yield mock


def test_extract_arxiv_ids():
    """Test extracting arXiv IDs from text"""
    text = f"Paper arXiv:{TEST_ARXIV_ID} and another 2402.12345"
    ids = extract_arxiv_ids(text)
    assert TEST_ARXIV_ID in ids
    assert "2402.12345" in ids
    assert len(ids) == 2


def test_paper_download_arxiv_id_success(mock_arxiv, mock_arxiv_client):
    """Test successful paper download using arXiv ID"""
    mock_arxiv_client.results.return_value = iter([mock_arxiv._paper])

    result = paper_download_arxiv_id(TEST_ARXIV_ID, TEST_OUTPUT_DIR)
    assert result == TEST_PDF_PATH

    mock_arxiv.Search.assert_called_once_with(id_list=[TEST_ARXIV_ID])
    mock_arxiv_client.results.assert_called_once_with("mock_search")


def test_paper_download_arxiv_id_not_found(mock_arxiv, mock_arxiv_client):
    """Test paper download with non-existent arXiv ID"""
    mock_arxiv_client.results.return_value = iter([])

    with pytest.raises(ArxivPaperNotFoundError):
        paper_download_arxiv_id(TEST_ARXIV_ID, TEST_OUTPUT_DIR)

    mock_arxiv.Search.assert_called_once_with(id_list=[TEST_ARXIV_ID])


def test_paper_download_arxiv_id_download_error(mock_arxiv, mock_arxiv_client):
    """Test paper download with download failure"""
    # Configure the mock to return our paper but fail on download
    paper = mock_arxiv._paper
    paper.download_pdf.side_effect = Exception("Download failed")
    # Ensure query returns our paper
    mock_arxiv_client.results.return_value = iter([paper])

    with pytest.raises(ArxivDownloadError):
        paper_download_arxiv_id(TEST_ARXIV_ID, TEST_OUTPUT_DIR)


def test_paper_download_arxiv_metadata_success(mock_arxiv, mock_arxiv_client):
    """Test successful paper download using metadata"""
    mock_arxiv_client.results.return_value = iter([mock_arxiv._paper])

    result = paper_download_arxiv_metadata(TEST_AUTHORS, TEST_TITLE, TEST_OUTPUT_DIR)
    assert result == TEST_PDF_PATH

    mock_arxiv.Search.assert_called_once()
    mock_arxiv_client.results.assert_called_once_with("mock_search")
    search_args = mock_arxiv.Search.call_args[1]
    assert "au:" in search_args["query"]
    assert "ti:" in search_args["query"]


def test_paper_download_arxiv_metadata_not_found(mock_arxiv, mock_arxiv_client):
    """Test paper download with non-matching metadata"""
    mock_arxiv_client.results.return_value = iter([])

    with pytest.raises(ArxivPaperNotFoundError):
        paper_download_arxiv_metadata(TEST_AUTHORS, TEST_TITLE, TEST_OUTPUT_DIR)


def test_paper_get_metadata_from_filename(mock_arxiv, mock_arxiv_client):
    """Test getting metadata from filename containing arXiv ID"""
    mock_arxiv_client.results.return_value = iter([mock_arxiv._paper])

    result = paper_get_metadata(f"paper_{TEST_ARXIV_ID}.pdf")
    assert result["title"] == TEST_TITLE
    assert result["authors"] == TEST_AUTHORS
    assert result["arxiv_id"] == TEST_ARXIV_ID


def test_paper_get_metadata_from_pdf_content(mock_arxiv, mock_arxiv_client, mock_pymupdf):
    """Test getting metadata from PDF content"""
    paper = mock_arxiv._paper

    # Setup mock to handle both search attempts:
    # 1. First try with filename (returns empty)
    # 2. Second try with arxiv ID (returns our paper)
    mock_arxiv_client.results.side_effect = [
        iter([]),  # Empty result for filename search
        iter([paper]),  # Success for arxiv ID search
    ]

    result = paper_get_metadata("test_paper.pdf")
    assert result["title"] == TEST_TITLE
    assert result["authors"] == TEST_AUTHORS
    assert result["arxiv_id"] == TEST_ARXIV_ID

    # Verify both searches were performed
    assert mock_arxiv.Search.call_count == 2
    mock_pymupdf.open.assert_called_once_with("test_paper.pdf")


def test_paper_get_metadata_not_found(mock_arxiv, mock_arxiv_client, mock_pymupdf):
    """Test metadata extraction when paper is not found"""
    mock_arxiv_client.results.return_value = iter([])
    mock_pymupdf.open().load_page().get_text.return_value = "Content with no arXiv ID"
    result = paper_get_metadata("unknown_paper.pdf")
    assert result == {}


def test_paper_get_metadata_pdf_error(mock_pymupdf):
    """Test metadata extraction with PDF reading error"""
    mock_pymupdf.open.side_effect = Exception("PDF error")
    result = paper_get_metadata("corrupted.pdf")
    assert result == {}
