# release-board

HTTP API для учёта выпусков приложений. Данные хранятся в PostgreSQL,
работа ведётся с сущностью `Release`.

## Требования

- Linux (WSL2), Python 3.12 или новее
- Docker Engine — для тестовой базы и локальных кластеров
- kubectl, k3d, Helm, Trivy, kubeconform

Точные версии зафиксированы в [docs/environment.md](docs/environment.md).

## Подготовка

    make install

Команда создаёт виртуальное окружение `.venv` и устанавливает закреплённые
версии инструментов из `requirements-dev.txt`.

## Проверки

    make lint
    make typecheck
    make test
    make check

Локальная работа и CI выполняют одни и те же команды.

## Структура

- `src/release_board/` — исходный код приложения
- `tests/` — тесты
- `deploy/k8s/` — манифесты Kubernetes
- `deploy/helm/` — Helm chart
- `deploy/k3d/` — конфигурация локального кластера
- `scripts/` — вспомогательные скрипты
- `docs/` — отчёты, ADR, runbook'и, фиксация окружения

## Статус

В работе: инфраструктура проекта, окружение, проверки качества, CI.
Доменная логика сервиса ещё не реализована.