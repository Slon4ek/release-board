# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование: [Semantic Versioning](https://semver.org/lang/ru/).

## [1.1.0] - 2026-10-10

Релиз первого полного стенда: Helm chart, стенды k3d/k3s, скрипты.

### Added
- Helm chart `deploy/helm/release-board`: API (Deployment/Service/SA/ConfigMap),
  PostgreSQL (StatefulSet + PVC), PDB, NetworkPolicy, hook-миграции alembic,
  helm test, `values.schema.json`, values для k3d и k3s.
- Скрипты стенда `scripts/stand-*.sh` (up/smoke/test/status) + make-таргеты
  `stand-{up,smoke,test,status}-{k3d,k3s}`.
- `scripts/README.md` — шпаргалка по скриптам стенда.

### Changed
- `Makefile`: `TAG ?= 1.1.0`.
- `docs/environment.md`: зафиксирована версия Helm 3.20.2.

### Notes
- Миграции БД выполняются Helm-хуком `post-install,pre-upgrade`;
  `helm rollback` НЕ откатывает данные и НЕ выполняет миграции.

## [1.0.0] - 2026-10-08

Первый рабочий релиз приложения (этапы 1–5): HTTP API, PostgreSQL,
docker-образ, k3d/k3s-стенды, нагрузочный тест, перезапуск VM с сохранением данных.