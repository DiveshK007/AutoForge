.PHONY: help dev backend dashboard docker clean test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start both backend and dashboard in development mode
	@echo "⚒️  Starting AutoForge development environment..."
	@make backend &
	@make dashboard &
	@wait

backend: ## Start the backend API server
	@echo "🚀 Starting backend..."
	cd backend && pip install -r requirements.txt -q && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

dashboard: ## Start the dashboard dev server
	@echo "🚀 Starting dashboard..."
	cd dashboard && npm install && npm run dev

docker: ## Start everything with Docker Compose
	docker-compose up --build

docker-bg: ## Start everything with Docker Compose (detached)
	docker-compose up --build -d
	@echo "✅ AutoForge running:"
	@echo "   Backend:   http://localhost:8000"
	@echo "   Dashboard: http://localhost:3000"

docker-down: ## Stop Docker Compose services
	docker-compose down

test: ## Run backend tests
	cd backend && python -m pytest tests/ -v

clean: ## Remove generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dashboard/.next 2>/dev/null || true

lint: ## Run linting
	cd backend && python -m flake8 . --max-line-length 120 --exclude __pycache__
