#!/bin/bash

echo "Setting up Compliance Agent..."

# Create necessary directories
mkdir -p certs
mkdir -p data

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please update with your configuration"
fi

# Generate self-signed certificates for development
if [ ! -f certs/server.crt ]; then
    echo "Generating self-signed certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout certs/server.key -out certs/server.crt \
        -subj "/C=DE/ST=Berlin/L=Berlin/O=Compliance/CN=localhost"
fi

# Create MinIO bucket
echo "Waiting for MinIO to start..."
sleep 10

docker-compose exec minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb myminio/compliance-audit
docker-compose exec minio mc policy set public myminio/compliance-audit

echo "Setup complete!"