#!/bin/bash

# Exit on any error
set -e

# Start Docker Compose services
echo "Starting Docker Compose services..."
docker compose up -d

# Wait for MinIO service to be ready
echo "Waiting for MinIO to be ready..."
until curl -s http://localhost:9000 > /dev/null; do
  echo "MinIO is not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "MinIO is ready!"

# Run the Python setup script to create the bucket
echo "Running Python script to set up the 'papers' bucket..."
python create_bucket.py

echo "Setup completed successfully!"