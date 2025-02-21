import pytest
from flask import Flask
from unittest.mock import patch
from app.routes import bp


@pytest.fixture
def mock_db():
    with patch("app.routes.db") as mock_db:
        yield mock_db


@pytest.fixture
def mock_ollama():
    with patch("app.routes.ollama_client") as mock_ollama:
        mock_ollama.get_query_embeddings.return_value = [0.1, 0.2, 0.3]
        yield mock_ollama


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_paper():
    return {
        "paper_id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "Test Paper",
        "authors": "Test Author",
        "similarity": 0.95,
    }
