# tests/test_routes.py

import io
from app.routes import PaperNotFoundError


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


def test_update_paper_success(client, mock_db, sample_paper):
    update_data = {"title": "Updated Title", "authors": "Updated Author"}
    mock_db.paper_update.return_value = {**sample_paper, **update_data}

    response = client.put(f"/papers/{sample_paper['paper_id']}", json=update_data)
    assert response.status_code == 200
    assert response.json["title"] == update_data["title"]
    assert response.json["authors"] == update_data["authors"]


def test_delete_paper_success(client, mock_db, sample_paper):
    response = client.delete(f"/papers/{sample_paper['paper_id']}")
    assert response.status_code == 204
    mock_db.paper_delete.assert_called_once_with(sample_paper["paper_id"])


def test_delete_paper_not_found(client, mock_db):
    mock_db.paper_delete.side_effect = PaperNotFoundError("Paper not found")

    response = client.delete("/papers/nonexistent")
    assert response.status_code == 404
    assert "error" in response.json
