# Окружение

Фиксируются название инструмента, версия, операционная система и архитектура.
Полный вывод окружения не копируется. Плавающий тег `latest` не используется.

Дата фиксации: 2026-10-04, коммит `59cd029`.
Обновлено: 2026-10-06, этап 3 (Docker-образ, Trivy, k3d registry).
Обновлено: 2026-10-09, этап 5 (k3s на VM; версии хоста и инструментов
перепроверены, добавлен раздел VM).

## Хост

| Параметр | Значение |
| --- | --- |
| ОС | Ubuntu 26.04.1 LTS |
| Ядро | Linux 7.0.0-38-generic |
| Архитектура | x86_64 |
| Python | 3.12.15 (`python3.12`, окружение проекта; `python3` указывает на 3.14.4 и проектом не используется — `requires-python = ">=3.12,<3.14"`) |

## Инструменты

| Инструмент | Версия |
| --- | --- |
| Git | 2.53.0 |
| Docker | 29.8.2 |
| Docker Compose | 5.6.0 |
| k3d | 5.9.0 (в комплекте k3s v1.35.5-k3s1) |
| kubectl | 1.35.9 (клиент; сервер k3s — v1.35.5+k3s1) |
| kubeconform | 0.8.0 |
| k3s (на VM, этап 5) | v1.35.5+k3s1 (`k3s --version`: `6a4781ad`, go1.25.9) |
| QEMU/KVM (гипервизор VM) | qemu-system-x86_64 10.2.1 (`Debian 1:10.2.1+ds-1ubuntu3.2`) |
| Helm | не установлен — потребуется на этапе 6 (ТЗ: 3.19+ или 4.x) |
| Trivy | 0.75.0 (запуск в контейнере `aquasec/trivy:0.75.0`) |
| Pyright | 1.1.414 |
| Ruff | 0.16.10 |
| pytest | 9.1.1 |

## VM (k3s, этап 5)

| Параметр | Значение |
| --- | --- |
| Гипервизор | KVM: `qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m 4096`, `-nographic` |
| ОС | Ubuntu 24.04.5 LTS, ядро 6.8.0-146-generic |
| CPU | 2 vCPU (`-smp 2`, Intel Core i5-12450H) |
| RAM | 4096 MiB (`-m 4096` = 4 ГБ), в госте ~3.8 GiB, swap 0 B |
| Диск | qcow2: виртуальный 50 GiB (файл 3.25 GiB), backing — `noble-server-cloudimg-amd64.img`; в госте `/dev/vda` 50 ГБ |
| Сеть | qemu user-mode (slirp) NAT: `ens3` 10.0.2.15/24, шлюз 10.0.2.2; пробросы 2222→22 (SSH), 6443→6443 (Kubernetes API) |
| k3s | v1.35.5+k3s1, single-server, юнит systemd `enabled` |
| kubeconfig | `~/.kube/k3s-release-board.yaml`, права 0600, контекст `k3s-release-board` |
| Файлы VM | `/mnt/B4A692EBA692AD7C/vm/k3s-vm/`: `start-vm.sh`, `k3s-vm.qcow2`, `seed.iso` (cloud-init), `SHA256SUMS` |

## Пакеты Python

| Пакет | Версия | Lock |
| --- | --- | --- |
| fastapi | 0.142.2 | runtime |
| uvicorn | 0.54.0 | runtime |
| SQLAlchemy | 2.1.3 | runtime |
| psycopg | 3.3.6 | runtime |
| pydantic | 2.13.5 | runtime |
| pydantic-settings | 2.15.0 | runtime |
| alembic | 1.20.0 | runtime |
| httpx | 0.28.1 | dev |
| pytest-asyncio | 1.4.0 | dev |
| pytest-dotenv | 0.5.2 | dev |

Все версии зафиксированы точными номерами релизов, без бета-версий и без
плавающих диапазонов. Источник истины — два lock-файла, согласованные
с `pyproject.toml`:

- `requirements.lock` — 27 пакетов, только runtime: fastapi, uvicorn,
  SQLAlchemy, psycopg, pydantic, alembic и их транзитивные зависимости.
  Этот файл копируется в сборочную стадию Dockerfile и ставится в venv
  образа (этап 3, выполнено).
- `requirements-dev.lock` — включает runtime через `-r requirements.lock`
  и добавляет 9 пакетов разработки: pytest, pytest-asyncio, pytest-dotenv,
  httpx, ruff, pyright и их транзитивные (pluggy, iniconfig, nodeenv).

Локально `make install` ставит только runtime-зависимости, `make install-dev` —
все. В CI устанавливается `requirements-dev.lock`: шагу `Test` нужны pytest и
httpx.

Ранее в `pyproject.toml` была объявлена экстра `uvicorn[standard]`, которая тянет
`uvloop`, `httptools`, `watchfiles` и `websockets`. Ни одна из них не попадала в
lock и не устанавливалась, то есть объявление расходилось с реальностью и
`pip install .` давал другое окружение, чем `pip install -r requirements.lock`.
Экстра убрана, зависимости совпадают.

## Образы

| Образ | Версия | Digest |
| --- | --- | --- |
| `python` (база Dockerfile) | 3.12.14-slim-bookworm, linux/amd64 | `sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` |
| `postgres` | 16.15 (Debian 16.15-1.pgdg13+2), linux/amd64 | `sha256:11a9d238fbb48bab14599c57e41123254452b1a2d93c6c8595bce96f346bd082` |
| `release-board` (этап 3) | 1.0.0, linux/amd64 | `sha256:727536d53a127f4c8aaf40facb6b1f128afd3bda186faae2f8d3034aae8159b5` |
| `registry` (k3d registry) | 2 | `sha256:a3d8aaa63ed8681a604f1dea0aa03f100d5895b6a58ace528858a7b332415373` |

Базовый образ `python` закреплён по digest прямо в `Dockerfile` — перезапись
тега при пересборке невозможна. Сборочный образ `release-board:1.0.0`
зафиксирован в таблице digest'ом; в манифестах Kubernetes (этап 4) он будет
указываться как
`k3d-release-board-registry.localhost:5000/release-board@sha256:727536d5...`.

В `compose.yaml` для локальной разработки указан тег `postgres:16`
(плавающий major-тег); digest выше — фактически развёрнутая версия,
его нужно перепроверять при пересборке окружения.

### Образы k3s (этап 5)

Фактический состав containerd в VM, `crictl images --digests`
(2026-10-09); digest в выдаче crictl усечён до 13 символов:

| Образ | Тег |
| --- | --- |
| `rancher/mirrored-coredns-coredns` | 1.14.3 |
| `rancher/mirrored-metrics-server` | v0.8.1 |
| `rancher/mirrored-library-traefik` | 3.6.13 |
| `rancher/local-path-provisioner` | v0.0.36 |
| `rancher/klipper-lb` | v0.4.17 |
| `rancher/klipper-helm` | v0.10.0-build20260513 |
| `rancher/mirrored-pause` | 3.6 |
| `rancher/mirrored-library-busybox` | 1.37.0 |
| `library/postgres` | 16.15 (наш стенд) |
| `library/busybox` | 1.37.0 (init-контейнер `chown-pg-data`) |
| `library/release-board` | 1.0.0 + алиас по digest `sha256:727536d5…` (импорт из tar, этап 5) |

Теги только точные, `latest` отсутствует.
