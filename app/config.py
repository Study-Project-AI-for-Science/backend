import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///instance/flask_app.db")
