.PHONY: dev dev-backend dev-frontend install test build docker clean

# ═══════════════════════════════════════
# Development
# ═══════════════════════════════════════

dev: dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# ═══════════════════════════════════════
# Install
# ═══════════════════════════════════════

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# ═══════════════════════════════════════
# Test
# ═══════════════════════════════════════

test:
	cd backend && python -m pytest tests/ -v

test-coverage:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html

# ═══════════════════════════════════════
# Build
# ═══════════════════════════════════════

build:
	cd frontend && npm run build

# ═══════════════════════════════════════
# Docker
# ═══════════════════════════════════════

docker:
	docker-compose up --build

docker-down:
	docker-compose down

# ═══════════════════════════════════════
# Clean
# ═══════════════════════════════════════

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/sandbox backend/output backend/ds_copilot.db
	rm -rf frontend/dist frontend/node_modules/.vite
