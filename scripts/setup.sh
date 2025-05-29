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

# Wait for PostgreSQL service to be ready
echo "Waiting for PostgreSQL to be ready..."
until nc -z localhost 5432; do
  echo "PostgreSQL is not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "PostgreSQL is ready!"


SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "Running migrations..."
bun run db:migrate


echo "Setup completed successfully!"

echo "Starting backend..."
bun run dev --host