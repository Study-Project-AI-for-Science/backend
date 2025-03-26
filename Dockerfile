# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Set only essential environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    GUNICORN_WORKERS=4

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY app/ app/
COPY modules/ modules/
COPY scripts/ scripts/
COPY run.py .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["sh", "-c", "python scripts/run_migrations.py && python scripts/create_bucket.py && gunicorn -w ${GUNICORN_WORKERS} -b 0.0.0.0:5000 'app:create_app()'"]
