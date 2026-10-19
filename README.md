# Release Board

HTTP API для учёта выпусков приложений. Сервис хранит релизы сервисов в
PostgreSQL: валидирует SemVer, отслеживает статус деплоя по окружениям
`dev`, `stage`, `prod` и переходы `planned → deployed → failed → rolled_back`.
События релизов публикуются в Kafka через outbox-паттерн и обрабатываются
нотификатором (см. «Событийная шина»).

## API

| Метод | Путь | Описание |
| --- | --- | --- |
| `POST` | `/releases` | создать релиз, ответ `201` |
| `GET` | `/releases` | список с фильтрами `service`, `environment`, `status` |
| `GET` | `/releases/{id}` | один релиз, `404` для неизвестного UUID |
| `PATCH` | `/releases/{id}/status` | смена статуса с проверкой перехода, `409` при запрещённом |
| `DELETE` | `/releases/{id}` | удалить релиз, `204` |
| `GET` | `/live` | живость процесса |
| `GET` | `/ready` | готовность и связь с PostgreSQL, `503` при недоступной базе |
| `GET` | `/version` | версия приложения и короткий Git SHA |

Документация и интерфейс Swagger UI доступны по адресу `/docs`.

## Событийная шина

События релизов уходят в Kafka через outbox-паттерн: запись в таблицу
`outbox_events` выполняется в одной транзакции с релизом, поэтому API не
зависит от доступности брокера.

```text
POST /releases → outbox_events → relay → Kafka (release.events.v1) → notifier
                                                    │
                              невалидные / после ретраев → Kafka (release.events.dlq)
```

| Сервис | Роль | Запуск |
| --- | --- | --- |
| `app` | HTTP API, пишет релизы и события в `outbox_events` | `python -m src.main` |
| `relay` | переносит события из outbox в Kafka (`SKIP LOCKED`, `published_at`/`attempts`) | `make relay-run` |
| `notifier` | faststream-подписчик: дедупликация по `processed_events`, отправка в DLQ при невалидности/сбое | `make notifier-run` |

Доставка at-least-once: дубликаты гасит `processed_events`; сбой обработки
нотификатор ретраит с нарастающей паузой (до 5 попыток), затем событие
уходит в DLQ с причиной и переигрывается вручную. Проверка всего конвейера
на живом стенде: `make e2e-kafka`.

## Стек

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic ·
pydantic 2 · faststream · confluent-kafka · Ruff · pyright (strict) ·
pytest (79 тестов)

## Быстрый старт

```bash
git clone git@github.com:Slon4ek/release-board.git
cd release-board
python3 -m venv .venv && source .venv/bin/activate

make install-dev                # зависимости из requirements-dev.lock
cp .env.example .env            # доступы к PostgreSQL и Kafka
cp .env-test.example .env-test  # окружение тестов (MODE=TEST)

docker compose up -d            # PostgreSQL 16 + Kafka (KRaft)
make migrate-up                 # схема БД
python -m src.main              # http://0.0.0.0:8000
```

Запуск обязателен через `python -m src.main`: при обычном `python src/main.py`
корень проекта не попадает в `sys.path`, и импорт `src` падает с
`ModuleNotFoundError`.

## Проверки

```bash
make test-db   # создать тестовую БД release_board_test
make check     # lint + typecheck + test
```

| Команда | Что делает |
| --- | --- |
| `make install` | только runtime-зависимости (`requirements.lock`) |
| `make install-dev` | все зависимости (`requirements-dev.lock`) |
| `make lint` | Ruff: стиль и формат, без правок файлов |
| `make format` | автоформатирование (перезаписывает файлы) |
| `make typecheck` | pyright в strict-режиме |
| `make test` | pytest: валидация, API, readiness, миграции |
| `make check` | lint + typecheck + test |
| `make test-db` | создать тестовую БД release_board_test (однократно) |
| `make migrate-up` | применить миграции Alembic |
| `make migrate-down` | откатить миграции Alembic |
| `make kafka-up` / `kafka-stop` | запустить/остановить Kafka в compose |
| `make kafka-topics` | список топиков |
| `make kafka-consume` | читать `release.events.v1` с начала |
| `make kafka-consume-dlq` | читать `release.events.dlq` с начала |
| `make relay-run` | запустить relay локально |
| `make notifier-run` | запустить нотификатор локально |
| `make compose-up` / `compose-down` | весь стенд: PostgreSQL, Kafka, app, relay, notifier |
| `make compose-status` / `compose-logs` | статус/логи стенда |
| `make migrate-docker` | миграции внутри контейнера app |
| `make e2e-kafka` | E2E: релиз → outbox → relay → Kafka → нотификатор → DLQ |

## Структура

```text
release-board/
├── src/
│   ├── api/            # роутеры и обработчики ошибок
│   ├── services/       # прикладной слой
│   ├── events/         # envelope-модели событий шины
│   ├── relay/          # outbox → Kafka
│   ├── notifier/       # Kafka → обработка / DLQ (faststream)
│   ├── models.py       # ORM-модели Release, OutboxEvent, ProcessedEvent
│   ├── schemas.py      # pydantic-схемы, правила переходов статусов
│   ├── database.py     # engine и сессии
│   ├── dependencies.py # зависимости FastAPI
│   ├── config.py       # настройки из переменных окружения
│   └── main.py         # сборка приложения
├── tests/              # 79 тестов: валидация, API, readiness, миграции, relay, нотификатор
├── scripts/            # e2e-kafka.sh, стендовые скрипты
├── migrations/         # ревизии Alembic
├── docs/               # отчёт, ADR, окружение
├── .github/workflows/  # CI: lint, typecheck, test
├── compose.yaml        # PostgreSQL 16, Kafka, app, relay, notifier
├── Makefile
└── pyproject.toml
```

## Документация

- [`docs/report.md`](docs/report.md) — технический отчёт: проверки, расхождения, история PR
- [`docs/environment.md`](docs/environment.md) — версии инструментов и образов
- [`docs/adr/0001-fastapi.md`](docs/adr/0001-fastapi.md) — обоснование выбора FastAPI
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — стратегия веток и порядок работы

## Конфигурация

Настройки читаются из переменных окружения, шаблон — `.env.example`:
`MODE`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
Шина событий: `KAFKA_BOOTSTRAP_SERVERS` (по умолчанию `localhost:29092`;
в compose для контейнеров — `kafka:9092`), `RELAY_TOPIC`
(`release.events.v1`), `DLQ_TOPIC` (`release.events.dlq`).
Версия приложения и Git SHA для `/version` приходят через `APP_VERSION` и
`GIT_SHA`. Файлы `.env` и `.env-test` не коммитятся — они в `.gitignore`.
