# ============================================================
# Tax Return AI — Makefile
# All Docker operations go through here.
# Never run npm, pip, or python directly on the host.
# ============================================================

# ── Config ──────────────────────────────────────────────────
COMPOSE      = docker compose
COMPOSE_DEV  = docker compose -f docker-compose.yml -f docker-compose.dev.yml
BACKEND      = $(COMPOSE) exec backend
BACKEND_DEV  = $(COMPOSE_DEV) exec backend
FRONTEND     = $(COMPOSE) exec frontend
FRONTEND_DEV = $(COMPOSE_DEV) exec frontend

.DEFAULT_GOAL := help

# ── Help ────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  Tax Return AI — Available Commands"
	@echo "  ─────────────────────────────────────────────────"
	@echo ""
	@echo "  DEVELOPMENT"
	@echo "  make dev            Start all services (dev mode, hot reload)"
	@echo "  make dev-build      Build + start dev services"
	@echo "  make dev-down       Stop dev services"
	@echo "  make dev-logs       Tail all dev logs"
	@echo "  make dev-logs-be    Tail backend logs only"
	@echo "  make dev-logs-fe    Tail frontend logs only"
	@echo ""
	@echo "  PRODUCTION"
	@echo "  make up             Start all services (production)"
	@echo "  make build          Build production images"
	@echo "  make down           Stop production services"
	@echo "  make restart        Restart all production services"
	@echo "  make logs           Tail all production logs"
	@echo ""
	@echo "  DATABASE"
	@echo "  make migrate        Run Alembic migrations (production)"
	@echo "  make migrate-dev    Run Alembic migrations (dev)"
	@echo "  make migration      Create new migration (use: make migration MSG='add table')"
	@echo "  make db-shell       Open SQLite shell (dev)"
	@echo ""
	@echo "  TESTING"
	@echo "  make test           Run all backend tests"
	@echo "  make test-watch     Run tests in watch mode"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make test-fe        Run frontend tests"
	@echo ""
	@echo "  BACKEND SHELL"
	@echo "  make shell-be       Open bash in backend container (dev)"
	@echo "  make shell-fe       Open bash in frontend container (dev)"
	@echo "  make python         Open Python shell in backend (dev)"
	@echo ""
	@echo "  DEPENDENCIES"
	@echo "  make freeze         Freeze pip deps to backend/requirements.lock"
	@echo ""
	@echo "  SETUP"
	@echo "  make seed           Seed development database with test data"
	@echo "  make setup-dirs     Create required host directories (run once on Pi)"
	@echo "  make env            Copy .env.example to .env (first time setup)"
	@echo ""
	@echo "  MAINTENANCE"
	@echo "  make health         Check service health"
	@echo "  make ps             Show running containers"
	@echo "  make clean          Remove stopped containers and dangling images"
	@echo "  make clean-all      Remove everything including volumes (DANGER)"
	@echo "  make backup         Backup data volume to ./backups/"
	@echo "  make restore        Restore from backup (use: make restore FILE=backup.tar.gz)"
	@echo ""


# ── Development ─────────────────────────────────────────────
.PHONY: dev
dev:
	$(COMPOSE_DEV) up

.PHONY: dev-build
dev-build:
	$(COMPOSE_DEV) up --build

.PHONY: dev-down
dev-down:
	$(COMPOSE_DEV) down

.PHONY: dev-logs
dev-logs:
	$(COMPOSE_DEV) logs -f

.PHONY: dev-logs-be
dev-logs-be:
	$(COMPOSE_DEV) logs -f backend

.PHONY: dev-logs-fe
dev-logs-fe:
	$(COMPOSE_DEV) logs -f frontend


# ── Production ──────────────────────────────────────────────
.PHONY: up
up:
	$(COMPOSE) up -d

.PHONY: build
build:
	$(COMPOSE) build

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: restart
restart:
	$(COMPOSE) restart

.PHONY: logs
logs:
	$(COMPOSE) logs -f


# ── Database ────────────────────────────────────────────────
.PHONY: migrate
migrate:
	$(BACKEND) alembic upgrade head

.PHONY: migrate-dev
migrate-dev:
	$(BACKEND_DEV) alembic upgrade head

.PHONY: migration
migration:
	@if [ -z "$(MSG)" ]; then echo "Usage: make migration MSG='describe change'"; exit 1; fi
	$(BACKEND_DEV) alembic revision --autogenerate -m "$(MSG)"

.PHONY: db-shell
db-shell:
	$(BACKEND_DEV) sqlite3 /data/db/tax_return_dev.db


# ── Testing ─────────────────────────────────────────────────
.PHONY: test
test:
	@$(BACKEND_DEV) pytest tests/ -v; ret=$$?; if [ $$ret -eq 5 ]; then exit 0; else exit $$ret; fi

.PHONY: test-watch
test-watch:
	$(BACKEND_DEV) pytest tests/ -v --watch

.PHONY: test-cov
test-cov:
	$(BACKEND_DEV) pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

.PHONY: test-fe
test-fe:
	$(FRONTEND_DEV) npm test

# Run a specific test file: make test-file FILE=tests/test_evidence.py
.PHONY: test-file
test-file:
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-file FILE=tests/test_evidence.py"; exit 1; fi
	$(BACKEND_DEV) pytest $(FILE) -v


# ── Shells ──────────────────────────────────────────────────
.PHONY: shell-be
shell-be:
	$(BACKEND_DEV) bash

.PHONY: shell-fe
shell-fe:
	$(FRONTEND_DEV) bash

.PHONY: python
python:
	$(BACKEND_DEV) python


# ── Dependencies ────────────────────────────────────────────
.PHONY: freeze
freeze:
	$(BACKEND_DEV) pip freeze > backend/requirements.lock
	@echo "✅ requirements.lock updated"


# ── Setup ───────────────────────────────────────────────────
.PHONY: seed
seed:
	$(BACKEND_DEV) python scripts/seed_dev_data.py

# Run once on Raspberry Pi before first docker compose up
.PHONY: setup-dirs
setup-dirs:
	mkdir -p /home/pi/tax-return-data/db
	mkdir -p /home/pi/tax-return-data/documents
	mkdir -p /home/pi/tax-return-data/exports
	@echo "✅ Data directories created at /home/pi/tax-return-data/"

.PHONY: env
env:
	@if [ -f .env ]; then echo ".env already exists — not overwriting"; exit 1; fi
	cp .env.example .env
	@echo "✅ .env created — edit it before starting services"


# ── Maintenance ─────────────────────────────────────────────
.PHONY: health
health:
	@echo "── Backend ──"
	@curl -sf http://localhost:8060/api/v1/health | python3 -m json.tool || echo "❌ Backend not responding"
	@echo ""
	@echo "── Frontend ──"
	@curl -sf http://localhost:3060 > /dev/null && echo "✅ Frontend OK" || echo "❌ Frontend not responding"

.PHONY: ps
ps:
	$(COMPOSE) ps

.PHONY: clean
clean:
	$(COMPOSE) down --remove-orphans
	docker image prune -f

# WARNING: removes all data volumes
.PHONY: clean-all
clean-all:
	@echo "⚠️  WARNING: This will delete ALL data including the database."
	@echo "   Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	$(COMPOSE) down -v --remove-orphans
	docker image prune -af


# ── Backup & Restore ────────────────────────────────────────
BACKUP_DIR = ./backups
TIMESTAMP  = $(shell date +%Y%m%d_%H%M%S)

.PHONY: backup
backup:
	mkdir -p $(BACKUP_DIR)
	tar -czf $(BACKUP_DIR)/tax-data-$(TIMESTAMP).tar.gz \
		-C /home/pi tax-return-data
	@echo "✅ Backup saved to $(BACKUP_DIR)/tax-data-$(TIMESTAMP).tar.gz"

.PHONY: restore
restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backups/tax-data-xxx.tar.gz"; exit 1; fi
	@echo "⚠️  WARNING: This will overwrite current data."
	@echo "   Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	$(COMPOSE) down
	tar -xzf $(FILE) -C /home/pi
	$(COMPOSE) up -d
	@echo "✅ Restore complete"


# ── Pi-specific shortcuts ────────────────────────────────────
# Useful when SSH'd into the Raspberry Pi

.PHONY: pi-deploy
pi-deploy:
	git pull
	$(COMPOSE) build
	$(COMPOSE) up -d
	$(BACKEND) alembic upgrade head
	@echo "✅ Deployed successfully"

.PHONY: pi-status
pi-status:
	@echo "── Containers ──"
	$(COMPOSE) ps
	@echo ""
	@echo "── Disk Usage ──"
	@du -sh /home/pi/tax-return-data/* 2>/dev/null || echo "No data yet"
	@echo ""
	@echo "── System ──"
	@df -h /
	@free -h
