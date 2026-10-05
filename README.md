# Release Board

HTTP API для учёта выпусков приложений. Сервис хранит релизы сервисов в
PostgreSQL: валидирует SemVer, отслеживает статус деплоя по окружениям
`dev`, `stage`, `prod` и переходы `planned → deployed → failed → rolled_back`.

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

## Стек

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic ·
pydantic 2 · Ruff · pyright (strict) · pytest (72 теста)

## Быстрый старт

```bash
git clone git@github.com:Slon4ek/release-board.git
cd release-board
python3 -m venv .venv && source .venv/bin/activate

make install-dev                # зависимости из requirements-dev.lock
cp .env.example .env            # доступы к PostgreSQL
cp .env-test.example .env-test  # окружение тестов (MODE=TEST)

docker compose up -d            # PostgreSQL 16
make migrate-up                 # схема БД
python -m src.main              # http://0.0.0.0:8000
```

Запуск обязателен через `python -m src.main`: при обычном `python src/main.py`
корень проекта не попадает в `sys.path`, и импорт `src` падает с
`ModuleNotFoundError`.

## Проверки

```bash
make test-db   # однократно создать тестовую БД release_board_test
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
| `make test-db` | создать тестовую БД release_board_test |
| `make migrate-up` | применить миграции Alembic |
| `make migrate-down` | откатить миграции Alembic |

## Структура

```text
release-board/
├── src/
│   ├── api/            # роутеры и обработчики ошибок
│   ├── services/       # прикладной слой
│   ├── models.py       # ORM-модель Release
│   ├── schemas.py      # pydantic-схемы, правила переходов статусов
│   ├── database.py     # engine и сессии
│   ├── dependencies.py # зависимости FastAPI
│   ├── config.py       # настройки из переменных окружения
│   └── main.py         # сборка приложения
├── tests/              # 72 теста: валидация, API, readiness, миграции
├── migrations/         # ревизии Alembic
├── docs/               # отчёт, ADR, окружение
├── .github/workflows/  # CI: lint, typecheck, test
├── compose.yaml        # PostgreSQL 16 для разработки
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
Версия приложения и Git SHA для `/version` приходят через `APP_VERSION` и
`GIT_SHA`. Файлы `.env` и `.env-test` не коммитятся — они в `.gitignore`.
