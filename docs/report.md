# Технический отчёт

Накопительный журнал проекта. Ведётся по мере выполнения этапов: после каждого
этапа сюда попадают выполненные проверки и их результаты. Полные логи сюда не
копируются, фиксируются команда, код завершения, коммит и подтверждающие строки.

Репозиторий: `git@github.com:Slon4ek/release-board.git`, публичный.
URL: `https://github.com/Slon4ek/release-board`.

---

## Этап 1. Сервис и тесты

Проверки выполнены локально и подтверждены в `main`: сервис, тесты и CI с шагом
`Test` влиты PR #7. Текущий `main` — `29fd6a0` от 2026-10-04.

| Команда | Код завершения | Подтверждающий фрагмент |
| --- | --- | --- |
| `make lint` | 0 | `All checks passed!` / `24 files already formatted` |
| `make typecheck` | 0 | `0 errors, 0 warnings, 0 informations` |
| `make test` | 0 | `72 passed in 0.60s` |

Тесты выполняются на отдельной базе данных `release_board_test`. Схема сбрасывается
`DROP SCHEMA public CASCADE` и пересоздаётся через `alembic upgrade head`.
База разработки `release_board` тестами не затрагивается.

### Разбор тестов по классам

Всего 72 теста в 13 классах. Процент покрытия не измерялся сознательно: он не
является доказательством качества проверки, поэтому ниже указано, какую именно
поломку ловит каждый класс.

| Класс | Тестов | Какую поломку ловит |
| --- | --- | --- |
| `test_validation.py::TestSemVer` | 29 | Регрессии в регулярном выражении SemVer 2.0.0: ведущие нули вроде `01.2.3`, пустой пререлиз, двойная точка, мусор в build-метаданных. Здесь же ловится ошибка слипшегося комментария, продублировавшая невалидный случай `1.0.0-` в списке. |
| `test_validation.py::TestEnvironmentEnum` | 9 | Что допустимы ровно `dev`, `stage`, `prod`. Ловит подмену `stage` на `staging`: проверка на недопустимость `staging` упала бы сразу при первой попытке. |
| `test_validation.py::TestRequiredFields` | 5 | Обязательные поля и правило, что строка из одних пробелов не считается именем сервиса. |
| `test_validation.py::TestStatusTransitions` | 7 | Таблица переходов: запрещённые переходы (`planned` → `rolled_back`, `deployed` → `deployed`) и терминальные состояния `failed` и `rolled_back`. |
| `test_api.py::TestCreateRelease` | 3 | Контракт `POST /releases`: код 201 и фактическая запись в базу с последующим чтением. |
| `test_api.py::TestFiltering` | 3 | Фильтры `service`, `environment`, `status`, включая алиас `?status=` при именованном параметре `status_filter`. |
| `test_api.py::TestGetRelease` | 3 | `GET /releases/{uuid}`, в том числе 404 на несуществующий идентификатор. |
| `test_api.py::TestUpdateRelease` | 3 | `PATCH /releases/{uuid}/status`: успешный переход, 404 на неизвестный UUID, 409 при запрещённом переходе. |
| `test_api.py::TestDeleteRelease` | 3 | `DELETE /releases/{uuid}`: код 204, фактическое удаление строки, 404 на неизвестный UUID. |
| `test_ready.py::TestLive` | 1 | `GET /live` отвечает без обращения к базе. |
| `test_ready.py::TestReady` | 2 | `GET /ready`: готовность при живой базе и 503 при недоступной. |
| `test_ready.py::TestVersion` | 2 | `GET /version` возвращает версию приложения и короткий Git SHA. |
| `test_migration.py::test_releases_table_matches_model` | 1 | Имена колонок таблицы `releases` совпадают с ORM-моделью, `service`, `version` и `created_at` — NOT NULL. |
| `test_migration.py::test_releases_column_types` | 1 | Типы колонок: UUID для `id`, `String(255)` / `String(50)`, ENUM с именами `release_environment` и `release_status`, `DateTime` с часовым поясом, серверный дефолт `now()`. |

---

## Этап 2. Удалённый репозиторий и стратегия веток

История `main` линейна, каждый срез ложится одним squash-коммитом с номером PR.
Merge-коммитов нет.

| SHA | Назначение | PR |
| --- | --- | --- |
| `256773e` | bootstrap: только `.gitignore`, базовая ветка для первого PR | — |
| `819b1fe` | инфраструктура, конфигурация, базовый CI | [#1](https://github.com/Slon4ek/release-board/pull/1) |
| `4ec8fbf` | передача pyright абсолютного пути интерпретатора | [#3](https://github.com/Slon4ek/release-board/pull/3) |
| `ebd3f9c` | конфигурация, подключение к БД, зависимости | [#2](https://github.com/Slon4ek/release-board/pull/2) |
| `07a0f15` | модель Release, схемы, начальная миграция | [#4](https://github.com/Slon4ek/release-board/pull/4) |
| `59cd029` | HTTP API, сервисный слой, обработка доменных ошибок | [#5](https://github.com/Slon4ek/release-board/pull/5) |
| `5424302` | отчёт, ADR, окружение | [#6](https://github.com/Slon4ek/release-board/pull/6) |
| `29fd6a0` | тесты DELETE и 409, сверка миграции с моделью, шаг Test в CI, отчёт | [#7](https://github.com/Slon4ek/release-board/pull/7) |

Номер PR не совпадает с порядком слияния: PR с исправлением интерпретатора был
открыт раньше, чем PR со схемой базы.

### Защита `main`

Настроена через GitHub Rulesets, Enforcement status `Active`, таргет `main`:

- `Restrict deletions` — удаление ветки запрещено;
- `Block force pushes` — перезапись истории запрещена;
- `Require a pull request before merging` — прямые пушты невозможны;
- `Require status checks to pass`, обязательная проверка `check`;
- `Require branches to be up to date before merging`;
- разрешён только squash как метод слияния.

Обязательное одобрение не включено намеренно: при работе в одиночку его получить
невозможно, и тогда невозможно было бы ни слить, ни закрыть PR.
Репозиторий публичный, поэтому ограничений тарифа на эти настройки нет.

### CI

В `main` один job `check` с тремя шагами: `Lint`, `Typecheck`, `Test`.
Шаг `Test` поднимает сервис `postgres:16` (пользователь `postgres`/`postgres`,
healthcheck `pg_isready`), задаёт переменные `MODE=TEST`,
`DB_NAME=release_board_test`, `DB_HOST=localhost` и запускает `make test` с кодом
завершения 0. Дополнительно заданы `concurrency` с `cancel-in-progress`
(устаревшие запуски той же ветки отменяются), `timeout-minutes: 15`, переменная
`GIT_SHA` — короткий Git SHA уходит в ответ `/version`, и кэш pip.

Зависимости в CI устанавливаются из `requirements-dev.lock`. Lock-файлы разделены:
`requirements.lock` содержит только runtime-зависимости (27 пакетов, включая
`python-dotenv`, который нужен `pydantic-settings`), а `requirements-dev.lock`
включает его через `-r requirements.lock` и добавляет девять пакетов разработки —
pytest, ruff, pyright, httpx и их транзитивные зависимости. Локально
`make install` ставит только runtime-зависимости, `make install-dev` — все.
Цель разделения: dev-пакеты не должны попадать в Docker-образ на этапе 3.

### Что ещё предстоит в этом этапе

- Git-упражнения с двумя клонами, включая разрешение конфликта при rebase.
- `docs/runbooks/git-recovery.md` со сравнением `revert`, `reset`, `restore`,
  `reflog`, `cherry-pick` и `rebase`.
- `CONTRIBUTING.md` и шаблон PR (ТЗ, строка 150).

---

## Обнаруженные расхождения

Фиксируются те, что влияли на воспроизводимость или приводили к падению CI.

| Расхождение | Симптом | Проявляется | Статус |
| --- | --- | --- | --- |
| `pyright` проверялся на файлах без внешних импортов | Ноль ошибок на заведомо неверном интерпретаторе. Правка не попала в первый PR, и CI упал на следующем срезе с ошибками разрешения импортов | любое окружение | исправлено в `4ec8fbf` |
| Ручная правка одной строки `requirements.lock` | Откат `pydantic` без синхронного изменения `pydantic_core` сломал чистую установку в CI, хотя локальное окружение работало | любое окружение | исправлено в `819b1fe` |
| Молчаливый откат настроек при ненайденном `.env` | Запуск с рабочим каталогом `src/` приводил к подстановке `DB_USER=postgres`; такой роли в базе нет, и `/ready` отвечал 503 | только при запуске из исходников: относительный путь `env_file=".env"` разрешается от рабочего каталога | исправлено: `env_file` указывает на `BASE_DIR / ".env"` — абсолютный путь от расположения `src/config.py` |
| `/ready` гасит исключение без логирования | Любая ошибка превращалась в голый 503, причина терялась полностью | только при запуске из исходников без Docker | исправлено: в `except SQLAlchemyError` добавлен `logger.exception` с трейсбеком |

Оба исправления, а также разделение lock-файлов подготовлены отдельным
фикс-коммитом; после его слияния сюда будет подставлен номер PR.

---

## Этапы 3-8

Записи добавляются по мере выполнения. Разделы заведены заранее, чтобы итоговая
сводка не собиралась по памяти.
