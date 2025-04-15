import pytest
from unittest import mock
from modules.ollama import ollama_client


@mock.patch("modules.ollama.ollama_client._initialize_module")
@mock.patch("modules.ollama.ollama_client.os.path.exists", return_value=True)
@mock.patch("modules.ollama.ollama_client.pymupdf.open")
@mock.patch("modules.ollama.ollama_client.instructor.from_openai")
def test_get_paper_info_success(mock_from_openai, mock_open_pdf, mock_exists, mock_init):
    # Mocking PDF text extraction
    mock_doc = mock.MagicMock()
    mock_page = mock.MagicMock()
    mock_page.get_text.return_value = "Example title by John Doe\nComputer Science\nPublished: 2024-01-01\nKeywords: AI, ML"
    mock_doc.page_count = 1
    mock_doc.load_page.return_value = mock_page
    mock_open_pdf.return_value = mock_doc

    # Mocking API response
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.model_dump.return_value = {
        "title": "Example title",
        "authors": ["John Doe"],
        "field_of_study": "Computer Science",
        "journal": "Example Journal",
        "publication_date": "2024-01-01",
        "doi": "10.1234/example.doi",
        "keywords": ["AI", "ML"],
    }
    mock_client.chat.completions.create.return_value = mock_response
    mock_from_openai.return_value = mock_client

    file_path = "dummy_path.pdf"
    result = ollama_client.get_paper_info(file_path)

    assert result["title"] == "Example title"
    assert "John Doe" in result["authors"]
    assert result["publication_date"] == "2024-01-01"
    assert "AI" in result["keywords"]
