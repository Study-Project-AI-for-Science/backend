# tests/test_routes.py

import json


def test_home_route(client):
    """Test the home route."""
    response = client.get("/")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Hello there!"


def test_create_paper_success(client):
    """Test successful paper creation (though it's a placeholder)."""
    response = client.post(
        "/papers", data=json.dumps({}), content_type="application/json"
    )  # , data=json.dumps(test_data), content_type='application/json'
    assert response.status_code == 201
    assert response.data == b"{}\n"  # Expect an empty JSON object


def test_create_paper_no_data(client):
    """Test creating a paper without any data."""
    response = client.post("/papers")  # No data sent
    assert response.status_code == 201  # Should still work even if no data
    assert response.data == b"{}\n"


def test_create_paper_invalid_content_type(client):
    """Test with an invalid content type."""
    response = client.post("/papers", data="invalid data", content_type="text/plain")
    assert response.status_code == 201  # Still expect to work, content type should not matter, since the server side
    # code does not depend on the content-type
    data = json.loads(response.data)  # Should not fail
    assert data == {}  # expect the response to be the default {}


def test_list_papers_empty(client):
    """Test listing papers when there are none."""
    response = client.get("/papers")
    assert response.status_code == 200
    assert response.json == []  # Expect an empty list


def test_list_papers_with_query(client):
    """Test listing papers with a query parameter (even though it does nothing now)."""
    response = client.get("/papers?query=some_query")
    assert response.status_code == 200
    assert response.json == []


def test_get_paper_not_found(client):
    """Test getting a paper that doesn't exist."""
    response = client.get("/papers/nonexistent_id")
    assert response.status_code == 200  # Should return 200 OK, with an empty object
    assert response.json == {}
