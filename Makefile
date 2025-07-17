.PHONY: help build up down logs test clean setup

help:
	@echo "Available commands:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - Show logs from all services"
	@echo "  make test     - Run tests"
	@echo "  make clean    - Clean up containers and volumes"
	@echo "  make setup    - Initial setup"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	python3 scripts/test_ingestion.py
	pytest tests/ -v

clean:
	docker-compose down -v
	rm -rf data/
	rm -rf certs/

setup:
	chmod +x scripts/setup.sh
	./scripts/setup.sh

restart: down up

status:
	@echo "Service Status:"
	@curl -s http://localhost:8000/health | jq '.' || echo "Ingress: DOWN"
	@curl -s http://localhost:8001/health | jq '.' || echo "Parser: DOWN"
	@curl -s http://localhost:8002/health | jq '.' || echo "Validator: DOWN"
	@curl -s http://localhost:8003/health | jq '.' || echo "HashWriter: DOWN"
	@curl -s http://localhost:8004/health | jq '.' || echo "Reporter: DOWN"
	@echo ""
	@echo "Infrastructure:"
	@curl -s http://localhost:9200/_cluster/health | jq '.' || echo "Elasticsearch: DOWN"
	@curl -s http://localhost:9000/minio/health/live || echo "MinIO: DOWN"