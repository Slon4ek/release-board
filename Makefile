PYTHON := $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then echo "$(CURDIR)/.venv/bin/python"; else echo python3; fi)

.PHONY: help install lint format typecheck test test-unit test-integration check all migrate-up migrate-down test-db

help:
	@echo "Команды:"
	@echo "  make install          — установить зависимости"
	@echo "  make lint             — проверить стиль (без правок)"
	@echo "  make format           — отформатировать код"
	@echo "  make typecheck        — проверить типы (pyright)"
	@echo "  make test             — все тесты"
	@echo "  make test-unit        — только unit-тесты"
	@echo "  make test-integration — только интеграционные тесты"
	@echo "  make check            — lint + typecheck + test"
	@echo "  make all              — format + check (перед коммитом)"
	@echo "  make migrate-up       — применить миграции"
	@echo "  make migrate-down     — откатить миграции"
	@echo "  make test-db          — создать тестовую БД (для make test)"

install:
	$(PYTHON) -m pip install -r requirements.lock

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test-db:
	@$(PYTHON) -c "import psycopg; from src.config import Settings; s=Settings(_env_file='.env-test'); c=psycopg.connect(host=s.DB_HOST, port=s.DB_PORT, user=s.DB_USER, password=s.DB_PASSWORD, dbname='postgres', autocommit=True); c.execute('CREATE DATABASE '+s.DB_NAME)" && echo "БД создана" || echo "БД уже существует"

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m pyright --pythonpath $(PYTHON) src/

test:
	$(PYTHON) -m pytest -v

test-unit:
	$(PYTHON) -m pytest tests/test_validation.py -v

test-integration:
	$(PYTHON) -m pytest tests/test_api.py tests/test_ready.py -v

check: lint typecheck test

all: format check

migrate-up:
	$(PYTHON) -m alembic upgrade head

migrate-down:
	$(PYTHON) -m alembic downgrade base