.PHONY: help dev test lint seed clean build up down logs prod load-test k8s-deploy

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start development environment
	docker-compose up -d db redis minio
	cd stories_service && python manage.py migrate
	cd stories_service && python manage.py runserver

test: ## Run tests
	cd stories_service && python manage.py test

lint: ## Run linting
	cd stories_service && python -m flake8 .
	cd stories_service && python -m black --check .

seed: ## Seed database with sample data
	cd stories_service && python manage.py create_superuser
	cd stories_service && python manage.py loaddata fixtures/sample_data.json

clean: ## Clean up containers and volumes
	docker-compose down -v
	docker system prune -f

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs
	docker-compose logs -f

migrate: ## Run database migrations
	cd stories_service && python manage.py migrate

makemigrations: ## Create new migrations
	cd stories_service && python manage.py makemigrations

shell: ## Open Django shell
	cd stories_service && python manage.py shell

worker: ## Start the story expiration worker
	cd stories_service && python manage.py expire_stories

install: ## Install dependencies
	pip install -r requirements.txt

setup: ## Initial setup
	make install
	make build
	make up
	sleep 10
	make migrate
	make seed

# Production commands
prod: ## Start production environment with monitoring
	docker-compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

# Load testing
load-test: ## Run load tests with k6
	cd load-testing && ./run-load-test.sh

load-test-prod: ## Run load tests against production
	cd load-testing && ./run-load-test.sh https://your-production-url.com

# Kubernetes deployment
k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/postgres-deployment.yaml
	kubectl apply -f k8s/redis-deployment.yaml
	kubectl apply -f k8s/api-deployment.yaml
	kubectl apply -f k8s/ingress.yaml

k8s-delete: ## Delete Kubernetes deployment
	kubectl delete -f k8s/

k8s-logs: ## Show Kubernetes logs
	kubectl logs -f deployment/stories-api -n stories-api

# Monitoring
metrics: ## Show Prometheus metrics
	curl http://localhost:8000/metrics

grafana: ## Open Grafana dashboard
	open http://localhost:3000

# Health checks
health: ## Check API health
	curl http://localhost:8000/api/health/

# Database operations
db-shell: ## Connect to database
	docker-compose exec db psql -U ashish -d stories

redis-cli: ## Connect to Redis
	docker-compose exec redis redis-cli
