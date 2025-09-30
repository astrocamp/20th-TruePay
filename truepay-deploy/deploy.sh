#!/bin/bash
echo "Loading Docker image..."
docker load -i truepay-web-optimized.tar

echo "Stopping existing services..."
docker-compose down

echo "Starting infrastructure services..."
docker-compose up -d postgres rabbitmq

echo "Waiting for database to be ready..."
sleep 15

echo "Running database migrations..."
docker-compose run --rm web uv run python manage.py migrate

echo "Collecting static files..."
docker-compose run --rm web uv run python manage.py collectstatic --noinput

echo "Starting application services..."
docker-compose up -d web nginx celery-worker

echo "Starting monitoring services..."
docker-compose up -d celery-flower

echo "Checking status..."
docker-compose ps

echo "Services available at:"
echo "- Main site: http://$(curl -s ifconfig.me)"
echo "- RabbitMQ: http://$(curl -s ifconfig.me):15673"
echo "- Flower: http://$(curl -s ifconfig.me):5555"