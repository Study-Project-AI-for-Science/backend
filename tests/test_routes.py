# tests/test_routes.py

import io
from unittest.mock import patch
from app.routes import (
    PaperNotFoundError,
    FileHashError,
    DatabaseError,
    S3UploadError,
    DuplicatePaperError,
    EmbeddingNotFoundError,
    InvalidUpdateError,
)


def test_home_route(client):
    """Test that the home route returns a success status and expected message"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["message"] == "API is running"


def test_create_paper_success(client, mock_db, mock_arxiv_retriever):
    """Test successful paper creation with a valid file"""
    # Set up mocks
    mock_db.paper_insert.return_value = "123e4567-e89b-12d3-a456-426614174000"
    mock_arxiv_retriever.paper_get_metadata.return_value = {
        "arxiv_id": "2101.12345",
        "title": "Test Paper from ArXiv",
        "authors": "Test Author",
        "abstract": "Test abstract",
        "url": "https://arxiv.org/abs/2101.12345",
        "published_date": "2021-01-01",
        "updated_date": "2021-01-15",
    }

    # Create test data
    data = {"title": "Original Title", "authors": "Original Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")

    # Make request
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")

    # Assert response
    assert response.status_code == 201
    assert "paper_id" in response.json

    # Check that paper_insert was called with the right parameters including markdown_content
    # The default markdown_content should be None for this test
    calls = mock_db.paper_insert.call_args_list
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert len(args) >= 7  # At least file_path, title, authors, abstract, paper_url, published, updated


def test_create_paper_with_arxiv_and_markdown(client, mock_db, mock_arxiv_retriever):
    """Test paper creation with ArXiv ID that successfully converts LaTeX to Markdown"""
    # Set up mocks
    mock_db.paper_insert.return_value = "123e4567-e89b-12d3-a456-426614174000"
    mock_arxiv_retriever.paper_get_metadata.return_value = {
        "arxiv_id": "2101.12345",
        "title": "Test Paper from ArXiv",
        "authors": "Test Author",
        "abstract": "Test abstract",
        "url": "https://arxiv.org/abs/2101.12345",
        "published_date": "2021-01-01",
        "updated_date": "2021-01-15",
    }

    # Mock successful LaTeX download and conversion
    mock_arxiv_retriever.paper_download_arxiv_id.return_value = True

    # This patch mocks the latex_content_parser.parse_latex_to_markdown function
    with patch("app.routes.latex_content_parser.parse_latex_to_markdown", return_value="# Test Markdown Content") as mock_parse:
        # Create test data
        data = {"title": "Original Title", "authors": "Original Author"}
        file = (io.BytesIO(b"test pdf content"), "test.pdf")

        # Make request
        response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")

        # Assert response
        assert response.status_code == 201
        assert "paper_id" in response.json

        # Verify that parse_latex_to_markdown was called
        mock_parse.assert_called_once()

        # Check that paper_insert was called with the markdown content
        mock_db.paper_insert.assert_called_once()
        args, kwargs = mock_db.paper_insert.call_args
        assert len(args) >= 8  # At least file_path, title, authors, abstract, paper_url, published, updated, markdown_content
        assert args[7] == "# Test Markdown Content"  # The markdown content should be passed as the 8th argument


def test_create_paper_with_arxiv_markdown_conversion_failure(client, mock_db, mock_arxiv_retriever):
    """Test paper creation with ArXiv ID when LaTeX conversion fails but paper creation succeeds"""
    # Set up mocks
    mock_db.paper_insert.return_value = "123e4567-e89b-12d3-a456-426614174000"
    mock_arxiv_retriever.paper_get_metadata.return_value = {
        "arxiv_id": "2101.12345",
        "title": "Test Paper from ArXiv",
        "authors": "Test Author",
        "abstract": "Test abstract",
        "url": "https://arxiv.org/abs/2101.12345",
        "published_date": "2021-01-01",
        "updated_date": "2021-01-15",
    }

    # Mock successful LaTeX download but failed conversion
    mock_arxiv_retriever.paper_download_arxiv_id.return_value = True

    # This patch mocks the latex_content_parser.parse_latex_to_markdown function to raise an exception
    with patch("app.routes.latex_content_parser.parse_latex_to_markdown", side_effect=Exception("LaTeX parsing failed")) as mock_parse:
        # Create test data
        data = {"title": "Original Title", "authors": "Original Author"}
        file = (io.BytesIO(b"test pdf content"), "test.pdf")

        # Make request
        response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")

        # Assert response - should still succeed even with failed conversion
        assert response.status_code == 201
        assert "paper_id" in response.json

        # Verify that parse_latex_to_markdown was called
        mock_parse.assert_called_once()

        # Check that paper_insert was called with None for markdown_content
        mock_db.paper_insert.assert_called_once()
        args, kwargs = mock_db.paper_insert.call_args
        assert len(args) >= 8  # Make sure all parameters were passed
        assert args[7] is None  # The markdown content should be None due to conversion failure


def test_create_paper_no_file(client):
    """Test paper creation without a file"""
    response = client.post("/papers", data={})
    assert response.status_code == 400
    assert "error" in response.json


def test_create_paper_empty_filename(client):
    """Test paper creation with an empty filename"""
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test content"), "")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.json


def test_create_paper_invalid_file_type(client):
    """Test paper creation with an invalid file type"""
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test content"), "test.txt")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json["error"]


def test_create_paper_duplicate_error(client, mock_db):
    """Test paper creation with a duplicate paper"""
    mock_db.paper_insert.side_effect = DuplicatePaperError("Paper already exists")

    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 409
    assert "error" in response.json


def test_create_paper_s3_error(client, mock_db):
    """Test paper creation when S3 upload fails"""
    mock_db.paper_insert.side_effect = S3UploadError("Failed to upload to S3")

    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 503
    assert "error" in response.json


def test_create_paper_file_hash_error(client, mock_db):
    """Test paper creation when file hash computation fails"""
    mock_db.paper_insert.side_effect = FileHashError("Invalid file hash")

    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.json


def test_list_papers_without_query(client, mock_db, sample_paper):
    """Test listing papers without a search query"""
    mock_db.paper_list_all.return_value = {"papers": [sample_paper], "total": 1, "page": 1, "total_pages": 1}

    response = client.get("/papers")
    assert response.status_code == 200
    assert "papers" in response.json
    assert len(response.json["papers"]) == 1


def test_list_papers_with_query(client, mock_db, mock_ollama, sample_paper):
    """Test listing papers with a search query"""
    mock_ollama.get_query_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_db.paper_get_similar_to_query.return_value = [sample_paper]

    response = client.get("/papers?query=test")
    assert response.status_code == 200
    assert "papers" in response.json
    assert len(response.json["papers"]) == 1


def test_list_papers_pagination(client, mock_db):
    """Test paper listing with pagination"""
    mock_db.paper_list_all.return_value = {"papers": [], "total": 30, "page": 2, "total_pages": 3}

    response = client.get("/papers?page=2&page_size=10")
    assert response.status_code == 200
    assert response.json["page"] == 2
    assert response.json["total_pages"] == 3


def test_list_papers_embedding_error(client, mock_db, mock_ollama):
    """Test listing papers when embedding retrieval fails"""
    mock_ollama.get_query_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_db.paper_get_similar_to_query.side_effect = EmbeddingNotFoundError("Embedding not found")

    response = client.get("/papers?query=test")
    assert response.status_code == 404
    assert "error" in response.json


def test_list_papers_invalid_page(client, mock_db):
    """Test paper listing with an invalid page number"""
    mock_db.paper_list_all.return_value = {"papers": [], "total": 0, "page": 1, "total_pages": 1}
    response = client.get("/papers?page=0&page_size=10")
    assert response.status_code == 200  # Default to page 1
    mock_db.paper_list_all.assert_called_with(page=1, page_size=10)


def test_list_papers_invalid_page_size(client, mock_db):
    """Test paper listing with an invalid page size"""
    mock_db.paper_list_all.return_value = {"papers": [], "total": 0, "page": 1, "total_pages": 1}
    response = client.get("/papers?page=1&page_size=0")
    assert response.status_code == 200  # Default to page_size 1
    mock_db.paper_list_all.assert_called_with(page=1, page_size=1)


def test_list_papers_empty_query(client, mock_db):
    """Test that empty query string falls back to regular listing"""
    mock_db.paper_list_all.return_value = {"papers": [], "total": 0, "page": 1, "total_pages": 1}

    response = client.get("/papers?query=")
    assert response.status_code == 200
    mock_db.paper_list_all.assert_called_once()


def test_get_paper_success(client, mock_db, sample_paper):
    """Test getting a paper by ID"""
    # Ensure the content field is properly set in the sample paper
    mock_db.paper_find.return_value = sample_paper

    response = client.get(f"/papers/{sample_paper['id']}")
    assert response.status_code == 200
    assert response.json["id"] == sample_paper["id"]

    # Verify the content field is returned in the response
    assert "content" in response.json
    assert response.json["content"] == sample_paper["content"]


def test_get_paper_not_found(client, mock_db):
    """Test getting a non-existent paper"""
    mock_db.paper_find.side_effect = PaperNotFoundError("Paper not found")

    response = client.get("/papers/nonexistent")
    assert response.status_code == 404
    assert "error" in response.json


def test_get_paper_database_error(client, mock_db):
    """Test getting a paper when the database encounters an error"""
    mock_db.paper_find.side_effect = DatabaseError("Database connection failed")

    response = client.get("/papers/123")
    assert response.status_code == 500
    assert "error" in response.json


def test_update_paper_success(client, mock_db, sample_paper):
    """Test successful paper update"""
    update_data = {"title": "Updated Title", "authors": "Updated Author"}
    updated_paper = {**sample_paper, **update_data}
    mock_db.paper_update.return_value = updated_paper

    response = client.put(f"/papers/{sample_paper['id']}", json=update_data)
    assert response.status_code == 200
    assert response.json["title"] == update_data["title"]
    assert response.json["authors"] == update_data["authors"]

    # Verify the content field is preserved
    assert "content" in response.json
    assert response.json["content"] == sample_paper["content"]


def test_update_paper_no_data(client, mock_db):
    """Test updating a paper without providing any update data"""
    response = client.put("/papers/123", json={})
    assert response.status_code == 400
    assert "No valid fields to update" in response.json["error"]


def test_update_paper_invalid_data(client, mock_db):
    """Test updating a paper with invalid data"""
    mock_db.paper_update.side_effect = InvalidUpdateError("Invalid update data")

    response = client.put("/papers/123", json={"title": ""})
    assert response.status_code == 400
    assert "error" in response.json


def test_update_paper_not_found(client, mock_db):
    """Test updating a non-existent paper"""
    mock_db.paper_update.side_effect = PaperNotFoundError("Paper not found")

    response = client.put("/papers/123", json={"title": "New Title"})
    assert response.status_code == 404
    assert "error" in response.json


def test_update_paper_partial_update(client, mock_db, sample_paper):
    """Test that updating only title works without affecting authors or content"""
    update_data = {"title": "New Title Only"}
    updated_paper = {**sample_paper, "title": "New Title Only"}
    mock_db.paper_update.return_value = updated_paper

    response = client.put(f"/papers/{sample_paper['id']}", json=update_data)
    assert response.status_code == 200
    assert response.json["title"] == "New Title Only"
    assert response.json["authors"] == sample_paper["authors"]

    # Verify the content field is preserved
    assert "content" in response.json
    assert response.json["content"] == sample_paper["content"]


def test_delete_paper_success(client, mock_db, sample_paper):
    """Test successful paper deletion"""
    response = client.delete(f"/papers/{sample_paper['id']}")
    assert response.status_code == 204
    mock_db.paper_delete.assert_called_once_with(sample_paper["id"])


def test_delete_paper_not_found(client, mock_db):
    """Test deleting a non-existent paper"""
    mock_db.paper_delete.side_effect = PaperNotFoundError("Paper not found")

    response = client.delete("/papers/nonexistent")
    assert response.status_code == 404
    assert "error" in response.json


def test_delete_paper_s3_error(client, mock_db):
    """Test paper deletion when S3 deletion fails"""
    mock_db.paper_delete.side_effect = S3UploadError("Failed to delete from S3")

    response = client.delete("/papers/123")
    assert response.status_code == 503
    assert "error" in response.json


def test_delete_paper_database_error(client, mock_db):
    """Test paper deletion when the database encounters an error"""
    mock_db.paper_delete.side_effect = DatabaseError("Database connection failed")

    response = client.delete("/papers/123")
    assert response.status_code == 500
    assert "error" in response.json


def test_get_paper_references(client, mock_db, sample_paper):
    """Test getting references for a paper"""
    test_references = [{"id": "ref1", "title": "Reference 1", "authors": "Author 1"}, {"id": "ref2", "title": "Reference 2", "authors": "Author 2"}]
    mock_db.paper_references_list.return_value = test_references

    response = client.get(f"/papers/{sample_paper['id']}/references")
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]["title"] == "Reference 1"
    assert response.json[1]["title"] == "Reference 2"
