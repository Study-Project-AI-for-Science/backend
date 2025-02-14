from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

def create_app():
    # Initialize the Flask app with instance-relative config
    app = Flask(__name__, instance_relative_config=True)

    # Load default configuration from app/config.py
    app.config.from_object('app.config.Config')

    # Load instance-specific configuration from instance/config.py
    app.config.from_pyfile('config.py', silent=True)

    # Register blueprints or routes here
    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)

    return app
