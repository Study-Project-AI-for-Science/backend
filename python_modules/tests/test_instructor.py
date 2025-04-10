# import pytest
# from unittest.mock import patch, MagicMock

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from modules.ollama.ollama_client import get_paper_info


# @pytest.fixture
# def mock_pdf_text():
#     return "Sample paper title\nJohn Doe, Jane Smith\nAbstract...\nKeywords: AI, NLP"


# @pytest.fixture
# def mock_response_dict():
#     return {
#         "title": "Sample paper title",
#         "authors": ["John Doe", "Jane Smith"],
#         "field_of_study": "Computer Science",
#         "journal": "AI Journal",
#         "publication_date": "2023-01-01",
#         "doi": "10.1234/sample.doi",
#         "keywords": ["AI", "NLP"],
#     }


# @patch("modules.ollama.ollama_client.os.path.exists")
# @patch("modules.ollama.ollama_client.pdfreader")
# @patch("modules.ollama.ollama_client.instructor.from_openai")
# def test_get_paper_info_success(mock_instructor, mock_pdfreader, mock_exists, mock_pdf_text, mock_response_dict):
#     # Setup mocks
#     mock_exists.return_value = True

#     mock_reader = MagicMock()
#     mock_page = MagicMock()
#     mock_page.extract_text.return_value = mock_pdf_text
#     mock_reader.pages = [mock_page]
#     mock_pdfreader.return_value = mock_reader

#     mock_client = MagicMock()
#     mock_resp = MagicMock()
#     mock_resp.model_dump.return_value = mock_response_dict
#     mock_client.chat.completions.create.return_value = mock_resp
#     mock_instructor.return_value = mock_client

#     # Run
#     result = get_paper_info("some/path/to/file.pdf")

#     # Assert
#     assert isinstance(result, dict)
#     assert result["title"] == "Sample paper title"
#     assert result["authors"] == ["John Doe", "Jane Smith"]
#     assert "keywords" in result


# @patch("modules.ollama.ollama_client.os.path.exists")
# def test_get_paper_info_file_not_found(mock_exists):
#     mock_exists.return_value = False

#     with pytest.raises(FileNotFoundError):
#         get_paper_info("nonexistent.pdf")
