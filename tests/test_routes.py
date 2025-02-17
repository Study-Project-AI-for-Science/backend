# tests/test_routes.py

import io
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
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["message"] == "API is running"


def test_create_paper_success(client, mock_db):
    mock_db.paper_insert.return_value = "123e4567-e89b-12d3-a456-426614174000"

    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")

    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")

    assert response.status_code == 201
    assert "paper_id" in response.json


def test_create_paper_no_file(client):
    response = client.post("/papers", data={})
    assert response.status_code == 400
    assert "error" in response.json


def test_create_paper_empty_filename(client):
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test content"), "")
    
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.json

def test_create_paper_invalid_file_type(client):
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test content"), "test.txt")
    
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json["error"]

def test_create_paper_duplicate_error(client, mock_db):
    mock_db.paper_insert.side_effect = DuplicatePaperError("Paper already exists")
    
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")
    
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 409
    assert "error" in response.json

def test_create_paper_s3_error(client, mock_db):
    mock_db.paper_insert.side_effect = S3UploadError("Failed to upload to S3")
    
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")
    
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 503
    assert "error" in response.json

def test_create_paper_file_hash_error(client, mock_db):
    mock_db.paper_insert.side_effect = FileHashError("Invalid file hash")
    
    data = {"title": "Test Paper", "authors": "Test Author"}
    file = (io.BytesIO(b"test pdf content"), "test.pdf")
    
    response = client.post("/papers", data={**data, "file": file}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "error" in response.json


def test_list_papers_without_query(client, mock_db, sample_paper):
    mock_db.paper_list_all.return_value = {"papers": [sample_paper], "total": 1, "page": 1, "total_pages": 1}

    response = client.get("/papers")
    assert response.status_code == 200
    assert "papers" in response.json
    assert len(response.json["papers"]) == 1


def test_list_papers_with_query(client, mock_db, mock_ollama, sample_paper):
    mock_ollama.get_query_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_db.paper_get_similar_to_query.return_value = [sample_paper]

    response = client.get("/papers?query=test")
    assert response.status_code == 200
    assert "papers" in response.json
    assert len(response.json["papers"]) == 1


def test_list_papers_pagination(client, mock_db):
    mock_db.paper_list_all.return_value = {
        "papers": [],
        "total": 30,
        "page": 2,
        "total_pages": 3
    }
    
    response = client.get("/papers?page=2&page_size=10")
    assert response.status_code == 200
    assert response.json["page"] == 2
    assert response.json["total_pages"] == 3

def test_list_papers_embedding_error(client, mock_db, mock_ollama):
    mock_ollama.get_query_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_db.paper_get_similar_to_query.side_effect = EmbeddingNotFoundError("Embedding not found")
    
    response = client.get("/papers?query=test")
    assert response.status_code == 404
    assert "error" in response.json

def test_list_papers_invalid_page(client, mock_db):
    response = client.get("/papers?page=0&page_size=10")
    assert response.status_code == 200  # Default to page 1
    mock_db.paper_list_all.assert_called_with(page=1, page_size=10)

def test_list_papers_invalid_page_size(client, mock_db):
    response = client.get("/papers?page=1&page_size=0")
    assert response.status_code == 200  # Default to page_size 10
    mock_db.paper_list_all.assert_called_with(page=1, page_size=10)

def test_list_papers_empty_query(client, mock_db):
    """Test that empty query string falls back to regular listing"""
    mock_db.paper_list_all.return_value = {"papers": [], "total": 0, "page": 1, "total_pages": 1}
    
    response = client.get("/papers?query=")
    assert response.status_code == 200
    mock_db.paper_list_all.assert_called_once()

def test_get_paper_success(client, mock_db, sample_paper):
    mock_db.paper_find.return_value = sample_paper

    response = client.get(f"/papers/{sample_paper['paper_id']}")
    assert response.status_code == 200
    assert response.json["paper_id"] == sample_paper["paper_id"]


def test_get_paper_not_found(client, mock_db):
    mock_db.paper_find.side_effect = PaperNotFoundError("Paper not found")

    response = client.get("/papers/nonexistent")
    assert response.status_code == 404
    assert "error" in response.json

def test_get_paper_database_error(client, mock_db):
    mock_db.paper_find.side_effect = DatabaseError("Database connection failed")
    
    response = client.get("/papers/123")
    assert response.status_code == 500
    assert "error" in response.json


def test_update_paper_success(client, mock_db, sample_paper):
    update_data = {"title": "Updated Title", "authors": "Updated Author"}
    mock_db.paper_update.return_value = {**sample_paper, **update_data}

    response = client.put(f"/papers/{sample_paper['paper_id']}", json=update_data)
    assert response.status_code == 200
    assert response.json["title"] == update_data["title"]
    assert response.json["authors"] == update_data["authors"]

def test_update_paper_no_data(client, mock_db):
    response = client.put("/papers/123", json={})
    assert response.status_code == 400
    assert "No valid fields to update" in response.json["error"]

def test_update_paper_invalid_data(client, mock_db):
    mock_db.paper_update.side_effect = InvalidUpdateError("Invalid update data")
    
    response = client.put("/papers/123", json={"title": ""})
    assert response.status_code == 400
    assert "error" in response.json

def test_update_paper_not_found(client, mock_db):
    mock_db.paper_update.side_effect = PaperNotFoundError("Paper not found")
    
    response = client.put("/papers/123", json={"title": "New Title"})
    assert response.status_code == 404
    assert "error" in response.json

def test_update_paper_partial_update(client, mock_db, sample_paper):
    """Test that updating only title works without affecting authors"""
    update_data = {"title": "New Title Only"}
    expected_response = {**sample_paper, "title": "New Title Only"}
    mock_db.paper_update.return_value = expected_response
    
    response = client.put(f"/papers/{sample_paper['paper_id']}", json=update_data)
    assert response.status_code == 200
    assert response.json["title"] == "New Title Only"
    assert response.json["authors"] == sample_paper["authors"]

def test_delete_paper_success(client, mock_db, sample_paper):
    response = client.delete(f"/papers/{sample_paper['paper_id']}")
    assert response.status_code == 204
    mock_db.paper_delete.assert_called_once_with(sample_paper["paper_id"])


def test_delete_paper_not_found(client, mock_db):
    mock_db.paper_delete.side_effect = PaperNotFoundError("Paper not found")

    response = client.delete("/papers/nonexistent")
    assert response.status_code == 404
    assert "error" in response.json

def test_delete_paper_s3_error(client, mock_db):
    mock_db.paper_delete.side_effect = S3UploadError("Failed to delete from S3")
    
    response = client.delete("/papers/123")
    assert response.status_code == 503
    assert "error" in response.json

def test_delete_paper_database_error(client, mock_db):
    mock_db.paper_delete.side_effect = DatabaseError("Database connection failed")
    
    response = client.delete("/papers/123")
    assert response.status_code == 500
    assert "error" in response.json
