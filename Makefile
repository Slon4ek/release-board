VENV ?= .venv
PYTHON := $(VENV)/bin/python

.PHONY: venv install lint lint-fix typecheck test check help

venv:
	python3 -m venv $(VENV)

install: venv
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check --fix .

typecheck:
	$(PYTHON) -m mypy src tests

test:
	$(PYTHON) -m pytest

check: lint typecheck test

help:
	@grep -E '^[a-z-]+:' $(MAKEFILE_LIST) | cut -d: -f1
