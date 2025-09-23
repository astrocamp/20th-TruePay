#!/bin/bash
echo "Loading Docker image..."
docker load -i truepay-web-optimized.tar

echo "Starting services..."
docker-compose down
docker-compose up -d

echo "Checking status..."
docker-compose ps