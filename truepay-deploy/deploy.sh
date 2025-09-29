#!/bin/bash
echo "Loading Docker image..."
docker load -i truepay-web-optimized.tar

echo "Starting database and message queue..."
docker-compose up -d postgres rabbitmq

echo "Waiting for database to be ready..."
sleep 10

echo "Running database migrations..."
docker-compose run --rm web uv run python manage.py migrate

echo "Collecting static files..."
docker-compose run --rm web uv run python manage.py collectstatic --noinput

echo "Starting all services..."
docker-compose down
docker-compose up -d

echo "Checking status..."
docker-compose ps

echo "Services available at:"
echo "- Main site: http://$(curl -s ifconfig.me)"
echo "- RabbitMQ: http://$(curl -s ifconfig.me):15673"
echo "- Flower: http://$(curl -s ifconfig.me):5555"