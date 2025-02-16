import pytest
from flask import Flask
from app.routes import bp  # Import your blueprint


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(bp)  # Register your blueprint
    return app


@pytest.fixture
def client(app):
    return app.test_client()
