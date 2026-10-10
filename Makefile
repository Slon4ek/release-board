PYTHON := $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then echo "$(CURDIR)/.venv/bin/python"; else command -v python3 || echo python3; fi)

.PHONY: help install install-dev lint format typecheck test test-unit test-integration check all migrate-up migrate-down test-db docker-build docker-run docker-version docker-stop docker-scan stand-up-k3d stand-up-k3s stand-smoke-k3d stand-smoke-k3s stand-test-k3d stand-test-k3s stand-status-k3d stand-status-k3s

help:
	@echo "Команды:"
	@echo "  make install           — установить runtime-зависимости"
	@echo "  make install-dev       — установить зависимости для разработки (включая runtime)"
	@echo "  make lint              — проверить стиль (без правок)"
	@echo "  make format            — отформатировать код"
	@echo "  make typecheck         — проверить типы (pyright)"
	@echo "  make test              — все тесты"
	@echo "  make test-unit         — только unit-тесты"
	@echo "  make test-integration  — интеграционные тесты (API + ready + миграции)"
	@echo "  make check             — lint + typecheck + test"
	@echo "  make all               — format + check (перед коммитом)"
	@echo "  make migrate-up        — применить миграции"
	@echo "  make migrate-down      — откатить миграции"
	@echo "  make test-db           — создать тестовую БД (для make test)"
	@echo "  make docker-build      — собрать образ (APP_VERSION, GIT_SHA подставляются)"
	@echo "  make docker-run        — запустить контейнер release-board на :8000"
	@echo "  make docker-version    — GET /version из запущенного контейнера"
	@echo "  make docker-stop       — остановить контейнер (SIGTERM)"
	@echo "  make docker-scan       — Trivy: HIGH/CRITICAL по образу (закреплённая версия)"
	@echo "  make stand-up-k3s     — поднять/обновить helm-стенд k3s"
	@echo "  make stand-up-k3d     — поднять/обновить helm-стенд k3d"
	@echo "  make stand-smoke-k3s  — smoke k3s (pods + /live /releases /version)"
	@echo "  make stand-smoke-k3d  — smoke k3d (pods + /live /releases /version)"
	@echo "  make stand-test-k3s   — helm test k3s"
	@echo "  make stand-test-k3d   — helm test k3d"
	@echo "  make stand-status-k3s — быстрый срез k3s"
	@echo "  make stand-status-k3d — быстрый срез k3d"

install:
	$(PYTHON) -m pip install -r requirements.lock

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.lock

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test-db:
	@$(PYTHON) -c "import psycopg; from src.config import Settings; s=Settings(_env_file='.env-test'); c=psycopg.connect(host=s.DB_HOST, port=s.DB_PORT, user=s.DB_USER, password=s.DB_PASSWORD, dbname='postgres', autocommit=True); c.execute('CREATE DATABASE '+s.DB_NAME)" && echo "БД создана" || echo "БД уже существует"

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m pyright --pythonpath $(shell command -v $(PYTHON)) src/

test:
	$(PYTHON) -m pytest -v

test-unit:
	$(PYTHON) -m pytest tests/test_validation.py -v

test-integration:
	$(PYTHON) -m pytest tests/test_api.py tests/test_ready.py tests/test_migration.py -v

check: lint typecheck test

all: format check

migrate-up:
	$(PYTHON) -m alembic upgrade head

migrate-down:
	$(PYTHON) -m alembic downgrade base

IMAGE ?= release-board
TAG ?= 1.1.0
TRIVY_IMAGE ?= aquasec/trivy:0.75.0

docker-build:
	docker build --build-arg APP_VERSION=$(TAG) --build-arg GIT_SHA=$$(git rev-parse --short HEAD) -t $(IMAGE):$(TAG) .

docker-run:
	docker run -d --name release-board -p 8000:8000 $(IMAGE):$(TAG)

docker-version:
	curl -s http://localhost:8000/version; echo

docker-stop:
	docker stop release-board

docker-scan:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $(CURDIR)/.trivy:/root/.cache $(TRIVY_IMAGE) image --exit-code 1 --severity HIGH,CRITICAL $(IMAGE):$(TAG)

# ── стенды (scripts/stand-*.sh) ──
stand-up-k3d:     ; scripts/stand-up.sh k3d
stand-up-k3s:     ; scripts/stand-up.sh k3s
stand-smoke-k3d:  ; scripts/stand-smoke.sh k3d
stand-smoke-k3s:  ; scripts/stand-smoke.sh k3s
stand-test-k3d:   ; scripts/stand-test.sh k3d
stand-test-k3s:   ; scripts/stand-test.sh k3s
stand-status-k3d: ; scripts/stand-status.sh k3d
stand-status-k3s: ; scripts/stand-status.sh k3s