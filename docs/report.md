# Технический отчёт

Накопительный журнал проекта. Ведётся по мере выполнения этапов: после каждого
этапа сюда попадают выполненные проверки и их результаты. Полные логи сюда не
копируются, фиксируются команда, код завершения, коммит и подтверждающие строки.

Репозиторий: `git@github.com:Slon4ek/release-board.git`, публичный.
URL: `https://github.com/Slon4ek/release-board`.

---

## Этап 1. Сервис и тесты

Проверки выполнены локально и подтверждены в `main`: сервис, тесты и CI с шагом
`Test` влиты PR #7. Срез этапа 1 — `29fd6a0` от 2026-10-04; на 2026-10-05
текущий `main` — `d0a5cbe` (см. таблицу этапа 2).

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
| `7da226f` | разделение lock-файлов, CI: concurrency, timeout, GIT_SHA, кэш pip; `BASE_DIR` для `.env`; `logger.exception` в `/ready`; `make install-dev` | [#8](https://github.com/Slon4ek/release-board/pull/8) |
| `59afb8d` | `CONTRIBUTING.md`, шаблон PR, `README.md` | [#9](https://github.com/Slon4ek/release-board/pull/9) |
| `3e33dff` | README: `make test-db` в таблице команд; CONTRIBUTING: предупреждение о перезаписи файлов `make format` — squash ветки `feature/api` | [#10](https://github.com/Slon4ek/release-board/pull/10) |
| `0538926` | `logger.exception` → `logger.debug` в `/ready` | [#11](https://github.com/Slon4ek/release-board/pull/11) |
| `eba9367` | `git revert 0538926`: возврат `logger.exception` в `/ready` | [#12](https://github.com/Slon4ek/release-board/pull/12) |
| `7c3fef9` | объединение формулировок Swagger в README — squash ветки `fix/readme-wording` (пункт 4) | [#13](https://github.com/Slon4ek/release-board/pull/13) |
| `21d6f87` | отчёт: журнал работы с remote (пункты 1–6), срезы #8–#13, вводная этапа 1 | [#14](https://github.com/Slon4ek/release-board/pull/14) |
| `6380e10` | cherry-pick коммита `49ab4f7`: уточнение описания `make test-db` в README (пункт 7) | [#15](https://github.com/Slon4ek/release-board/pull/15) |
| `d0a5cbe` | runbook `docs/runbooks/git-recovery.md` (ТЗ, строка 178) и обновление отчёта | [#16](https://github.com/Slon4ek/release-board/pull/16) |

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

### Работа с remote и совместные изменения (ТЗ, строки 154–163)

Второй клон — полная копия origin: `/home/slon4ek/PycharmProjects/release-board-2`.
Пункты 1–8 выполнены; ветки пунктов 1–3 (`feature/api`) и 4
(`fix/readme-wording`) слиты squash-PR #10 и #13, `fix/readme-clarity`
удалена без слияния — её содержимое вошло в `fix/readme-wording`.

| Пункт | Что отработано | Ключевые SHA и подтверждение |
| --- | --- | --- |
| 1. Tracking | `push -u origin feature/api`; в обоих клонах `* feature/api` со связью `[origin/feature/api]` | `59afb8d` |
| 2. Совместная ветка | коммит во втором клоне и `push`; в первом `fetch` даёт `[позади 1]`, `log feature/api..origin/feature/api` и `diff` показывают ровно одну строку до интеграции | `bf72f93` |
| 3. Non-fast-forward | push отклонён (non-fast-forward), затем `fetch`, `rebase origin/feature/api`, обычный push. Линейная история, merge-коммитов нет, force на `main` не применялся | `0bd600d` → пересоздан `8a469f6` |
| 4. Конфликт | две ветки (`fix/readme-wording`, `fix/readme-clarity`) правят строку 20 README; rebase остановился на маркерах строк 20–24. Две попытки разруления через GUI оставили версию upstream — коммит становился пустым и пропускался; итоговое разруление — механическая замена диапазона маркеров одной строкой. `72 passed`, финальный push прошёл как fast-forward | `7150d5a`, `8b14c29` → `85e7c20` |
| 5. Публичная отмена | PR #11 перевёл `logger.exception` в `logger.debug` на `/ready`; PR #12 — `git revert 0538926`, `1 insertion(+), 1 deletion(-)`, строка вернулась к `logger.exception`. `72 passed` | #11 `0538926`, #12 `eba9367` |
| 6. Локальная история | локальная ветка `feature/reflog-lab`: три коммита, `rebase -i HEAD~3` с `fixup` → два коммита; `reset --hard HEAD~1` сделал верхний коммит недостижимым; `reflog` показал его SHA; `switch -c feature/reflog-restore 49ab4f7` восстановил веткой. Reflog локальный, в `origin` не попадает | `49ab4f7` |
| 7. Перенос исправления | `git cherry-pick 49ab4f7` на локальную `fix/test-db-docs` → новый коммит с тем же диффом `README.md\| 4 ++--`; проверка `git show --stat` и `git diff main`, `72 passed`, push. Источник `49ab4f7` остался на месте, история ветки не переписывалась. | ветка `e731b5b` → на `main` `6380e10` (PR #15) |
| 8. Поиск регрессии | цепочка из четырёх коммитов на локальной `fix/bisect-chain` (D сдвигает строку валидации, добавляет тест с предсказуемым падением); `git bisect start` + `git bisect run python -m pytest tests/test_validation.py::TestStatusTransitions::test_planned_cannot_rollback -q` нашёл первого плохого коммита за 2 шага из 4 (`log₂4 = 2`); `git bisect reset`, ветка удалена. Тест без БД, поэтому годится для `run` | `a44845f` (первый плохой) |

Практический вывод: пока истории расходятся, после rebase нужен
`--force-with-lease`; когда родитель уже лежит на сервере, обычный push
проходит как fast-forward. Коммит, ставший пустым, Git не создаёт — защита от
тихой ошибки при неверно выбранной стороне конфликта.

### Итоги этапа 2

- Пункты 1–8 выполнены: заранее сжатая сводка по ним — в таблице выше.
- `docs/runbooks/git-recovery.md` создан и слит PR #16 (`d0a5cbe`):
  сравнение `revert`, `reset`, `restore`, `reflog`, `cherry-pick`,
  `rebase` (ТЗ, строка 178).
- Уборка временных веток завершена: `fix/readme-wording` (PR #13),
  `fix/readme-clarity`, `fix/test-db-docs` (PR #15), `feature/reflog-lab`,
  `feature/reflog-restore`, `fix/bisect-chain` — все удалены, в обоих
  клонах остаётся только `main`.
- Документация этапа: `CONTRIBUTING.md`, шаблон PR и `README.md` слиты
  PR #9; дополнение командами Makefile — PR #10; журнал remote — PR #14.

---

## Обнаруженные расхождения

Фиксируются те, что влияли на воспроизводимость или приводили к падению CI.

| Расхождение | Симптом | Проявляется | Статус |
| --- | --- | --- | --- |
| `pyright` проверялся на файлах без внешних импортов | Ноль ошибок на заведомо неверном интерпретаторе. Правка не попала в первый PR, и CI упал на следующем срезе с ошибками разрешения импортов | любое окружение | исправлено в `4ec8fbf` |
| Ручная правка одной строки `requirements.lock` | Откат `pydantic` без синхронного изменения `pydantic_core` сломал чистую установку в CI, хотя локальное окружение работало | любое окружение | исправлено в `819b1fe` |
| Молчаливый откат настроек при ненайденном `.env` | Запуск с рабочим каталогом `src/` приводил к подстановке `DB_USER=postgres`; такой роли в базе нет, и `/ready` отвечал 503 | только при запуске из исходников: относительный путь `env_file=".env"` разрешается от рабочего каталога | исправлено: `env_file` указывает на `BASE_DIR / ".env"` — абсолютный путь от расположения `src/config.py` |
| `/ready` гасит исключение без логирования | Любая ошибка превращалась в голый 503, причина терялась полностью | только при запуске из исходников без Docker | исправлено: в `except SQLAlchemyError` добавлен `logger.exception` с трейсбеком |

Все перечисленные исправления и разделение lock-файлов слиты единым срезом —
PR #8 (`7da226f`).

---

## Этап 3. Контейнер

Дата работ: 2026-10-05 – 2026-10-06.

### Сборка образа (ТЗ, этап 3, п. 1–4)

`Dockerfile` — multi-stage, обе стадии от закреплённого базового образа:

```text
python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
```

Digest, а не тег: содержимое базы зафиксировано байт-в-байт, перезапись
тега при пересборке невозможна.

- **`builder`**: в отдельный venv (`/opt/venv`) ставится только
  `requirements.lock` — 27 runtime-пакетов. `requirements-dev.lock`
  в образ не попадает: цель разделения lock-файлов из среза 8 выполнена.
- **`runtime`**: копируется только готовый venv, `src/`, `migrations/`,
  `alembic.ini`. Ни pip, ни компиляторов, ни `.git`, ни `.env`, ни тестов.
  Слой обновления ОС: `apt-get update && apt-get upgrade -y
  --no-install-recommends && rm -rf /var/lib/apt/lists/*` (добавлен после
  первого скана Trivy, см. ниже).
- **Непривилегированный пользователь**: `useradd --system --uid 10001
  --no-create-home --shell /usr/sbin/nologin app`, далее `USER app`.
- **Версия и Git SHA при сборке**: `--build-arg APP_VERSION=1.0.0
  --build-arg GIT_SHA=$(git rev-parse --short HEAD)` → `ARG`/`ENV` →
  `src/api/health.py` читает через `os.getenv`.
- **`.dockerignore`** — whitelist (`*` + `!src` `!migrations`
  `!requirements.lock` `!alembic.ini`): build context = 57.88 kB,
  `.git`, `.env`, тесты и кэши физически не доезжают до сборки.
  Требование ТЗ «не копируй `.git`, кэш, тестовые данные, `.env` в build
  context» выполнено конструктивно.

Команды и результаты:

```text
make docker-build → exit 0, 28.2s (15/15 слоёв); после правки Dockerfile
                    пересборка 12.7s, builder полностью CACHED
make docker-run   → контейнер 9d70039b1d5b, порт 8000
make docker-version → {"version":"1.0.0","git_sha":"d0a5cbe"}
docker exec release-board id → uid=10001(app) gid=999(app)
docker inspect health → healthy
```

`git_sha=d0a5cbe` совпадает с `git rev-parse --short HEAD` для `main` —
цепочка build-arg → env → ответ `/version` подтверждена.

### Завершение по SIGTERM (ТЗ, этап 3, п. 5)

```text
(for i in $(seq 1 60); do curl ... /live; done > flow.log) &  # фоновый поток
time docker stop release-board
→ real 0m0.448s        # grace 10s не исчерпан, SIGKILL не понадобился
docker inspect → ExitCode=0
docker logs:
  Shutting down
  Waiting for application shutdown.
  Application shutdown complete.
  Finished server process [1]
поток: 6×200 до SIGTERM, 1×(000/ERR) после закрытия listen-сокета,
       ни один запрос не завис (все --max-time 2 отработали)
```

`CMD` записан в exec-форме (`["python", "-m", "uvicorn", ...]`), поэтому
uvicorn — PID 1 и получает SIGTERM напрямую; в shell-форме сигнал
поглотил бы `/bin/sh` и пришлось бы убивать процесс через SIGKILL.

### Healthcheck (ТЗ, этап 3, п. 6)

Реализован: `HEALTHCHECK --interval=30s --timeout=3s --start-period=10s
--retries=3` на `/live` через `python -c urllib.request` (в slim-образе
нет curl/wget). `/live` выбран вместо `/ready` намеренно: `/ready`
зависит от PostgreSQL, и healthcheck контейнера не должен падать из-за
здоровья отдельного сервиса — проверка готовности с учётом базы
относится к Kubernetes probes (этап 4).

### Скан Trivy (ТЗ, этап 3, п. 7)

Инструмент: **Trivy 0.75.0** (закреплённая версия, запуск в контейнере
`aquasec/trivy:0.75.0`, кэш в `.trivy/` — в `.gitignore`).
База уязвимостей: schema 2, `UpdatedAt 2026-10-05 19:07 UTC`,
скачана `2026-10-05 20:13 UTC`.

```text
make docker-scan → aquasec/trivy:0.75.0 image --exit-code 1
                   --severity HIGH,CRITICAL release-board:1.0.0
```

Первый скан: **Total 63 (HIGH: 58, CRITICAL: 5)** — все находки в
ОС-слое `debian 12.15`; Python-пакеты: 12 находок, все LOW/MEDIUM,
**HIGH: 0, CRITICAL: 0**.

Разбор CRITICAL:

| Пакет | CVE | Статус | Действие |
| --- | --- | --- | --- |
| `perl-base` | CVE-2026-13221, CVE-2026-42496, CVE-2026-8376 | `fixed` (`5.36.0-7+deb12u4`) | закрыты обновлением ОС |
| `libsqlite3-0` | CVE-2025-7458 | `affected` — фикса нет | остаётся, разбор ниже |
| `zlib1g` | CVE-2023-45853 | `will_not_fix` | остаётся, разбор ниже |

Принятая мера — слой `apt-get upgrade` в Dockerfile; `apt-get -s upgrade`
показал 5 обновляемых пакетов. Пересборка и повторный скан:
**Total 55 (HIGH: 53, CRITICAL: 2)** — perl-base закрыт. `make docker-scan`
завершается с exit 1: команда настроена падать при остатке HIGH/CRITICAL,
игнор запрещён.

Состав остатка по статусам: **`fixed` — 0** (догонять в репозитории нечего,
обновление исчерпано), `affected` — 47, `fix_deferred` — 7,
`will_not_fix` — 1:

```text
affected:      bsdutils, libblkid1, libmount1, libsmartcols1, libuuid1,
               mount, util-linux, util-linux-extra, libncursesw6,
               ncurses-base, ncurses-bin, libtinfo6, libssl3, openssl,
               libsqlite3-0
fix_deferred:  gzip, libacl1, libsystemd0, libudev1, libsqlite3-0,
               perl-base
will_not_fix:  zlib1g
```

Письменный разбор остатка (ТЗ: «Не игнорируй находки уровня
high/critical без письменного разбора»):

1. **Фиксов в репозитории нет** — все 55 находок имеют статус `affected`
   (Debian признал уязвимым, патча нет), `fix_deferred` (публикация фикса
   отложена security-командой Debian) или `will_not_fix` (отказ от фикса).
   Состояние зафиксировано по базе от 2026-10-05.
2. **Утилиты не используются приложением.** Основная масса —
   `util-linux`/`mount`/`bsdutils`/`libblkid`/`ncurses`: это системные
   команды, процесс контейнера — только `python -m uvicorn`, эти бинарники
   не вызываются.
3. **`libsqlite3-0`**: в коде используется PostgreSQL (`psycopg`),
   `import sqlite3` отсутствует; CVE требует обработки враждебного
   SQLite-файла, а канала загрузки файлов у API нет.
4. **`zlib1g` (CVE-2023-45853)**: затрагивает `zipOpenNewFileInZip4`
   (minizip) — сервис не создаёт и не читает zip-архивы.
5. **`openssl`/`libssl3`**: исходящих внешних TLS-соединений у сервиса
   нет (база данных — внутри сети, соединение без TLS).
6. **Факторы смягчения**: контейнер работает от uid 10001; приложение
   получает входящий трафик только через ClusterIP-Service без вывода
   наружу (NodePort запрещён, этап 4 — NetworkPolicy); эксплуатация
   перечисленных уязвимостей требует локального выполнения враждебных
   сценариев внутри контейнера, для которых у сервиса нет входных точек.
7. **Дальнейшие меры**: повторный скан при каждом изменении образа
   (`make docker-scan`), пересборка базового образа при обновлении digest,
   обновление базы Trivy перед выпуском релиза (этап 7).

### Локальный registry (ТЗ, этап 3, финал)

```text
k3d registry create release-board-registry.localhost --port 5000
  → контейнер k3d-release-board-registry.localhost, образ registry:2
docker tag release-board:1.0.0 release-board-registry.localhost:5000/release-board:1.0.0
docker push release-board-registry.localhost:5000/release-board:1.0.0
  → digest: sha256:727536d53a127f4c8aaf40facb6b1f128afd3bda186faae2f8d3034aae8159b5 (size: 856)
```

Сверка digest:

| Источник | Digest |
| --- | --- |
| сборка (`exporting manifest list`) | `sha256:727536d53a12...` |
| push в registry | `sha256:727536d53a12...` |
| `docker images --digests` (RepoDigests) | `sha256:727536d53a12...` |

Digest сборки и образа в registry совпадают. В Kubernetes-манифестах
(этап 4) образ будет указан по этому digest с адресом
`k3d-release-board-registry.localhost:5000` (k3d добавляет контейнеру
префикс `k3d-`); тег `1.0.0` сохраняется как метаданные релиза.

### Итоги этапа 3

- Пункты 1–7 ТЗ выполнены: multi-stage от digest-базы, uid 10001,
  whitelist-контекст, версия/SHA в `/version`, SIGTERM — ExitCode=0 за
  0.448 с, healthcheck реализован, Trivy 0.75.0 с письменным разбором
  остатка.
- Размер образа: 347 MB.
- Изменения этапа: `Dockerfile`, `.dockerignore`, `Makefile`
  (таргеты `docker-*`), `docs/environment.md`, `docs/report.md`.

---

## Этап 4. Kubernetes-манифесты в k3d

Дата работ: 2026-10-06 – 2026-10-08.

### Кластер и цикл проверки манифестов

Кластер описан декларативно в `deploy/k3d/cluster.yaml`: один `server`,
два `agent`, локальный registry `release-board-registry.localhost:5000`.
Инструменты закреплены версиями: kubectl 1.35.9, kubeconform 0.8.0.
Контекст `k3d-release-board`, k3s v1.35.5-k3s1.

Каждый манифест прошёл один цикл:

```text
kubeconform -strict -summary -kubernetes-version 1.35.5 <файл>
→ kubectl apply --dry-run=client -f <файл>
→ kubectl apply -f <файл>
→ проверка состояния (get / rollout status)
```

### Манифесты (ТЗ, строки 196–212)

| Объект | Файл | kubeconform |
| --- | --- | --- |
| Namespace `release-board-raw` | `deploy/k8s/base/namespace.yaml` | `Valid: 1` |
| ConfigMap `release-board-config` | `configmap.yaml` | `Valid: 1` |
| Secret-шаблон (реальный `secret.yaml` создаётся локально и в git не попадает) | `secret.example.yaml` | `Valid: 1` |
| Service + StatefulSet PostgreSQL, PVC создаётся из `volumeClaimTemplates` | `postgres.yaml` | `Valid: 2` |
| Deployment (2 реплики, образ по digest) + ClusterIP Service | `api.yaml` | `Valid: 2` |
| ServiceAccount (без токена) | `serviceaccount.yaml` | `Valid: 1` |
| PodDisruptionBudget | `pdb.yaml` | `Valid: 1` |
| NetworkPolicy: default-deny-ingress + allow-api-from-raw + allow-postgres-from-api | `networkpolicy.yaml` | `Valid: 3` |

`kubectl apply --dry-run=client` прогнан по каждому файлу до записи;
исходники манифестов построчно прокомментированы («что и зачем»).

### Восемь доказательств (ТЗ, строки 214–223)

| № | Доказательство | Как проверялось | Подтверждение |
| --- | --- | --- | --- |
| 1 | Кластер и все ноды готовы | `kubectl get nodes` | 3 ноды `Ready`, `v1.35.5+k3s1` |
| 2 | Rollout готовится за ограниченное время | `kubectl rollout status ... --timeout=120s` | `successfully rolled out` |
| 3 | Service выбирает именно Pod'ы приложения | `kubectl get endpointslice -l kubernetes.io/service-name=release-board-api` | `ENDPOINTS 10.42.0.6,10.42.2.9`, порт 8000 |
| 4 | Readiness исключает неготовый Pod из обработки | цикл scale 3→2 с полусекундным срезом подов, slice и флагов | `13:27:19 \| pods: 1/1,1/1,0/1 \| slice: 3 \| ready: true true false` — неготовый Pod попадает в EndpointSlice с `ready: false`, и именно такие записи kube-proxy не программирует в iptables; через секунду флаг стал `true` |
| 5 | Данные PostgreSQL переживают пересоздание Pod | `INSERT` → `delete pod postgres-0` → `wait` → `SELECT` | `before-pod-recreate \| 2026-10-08 09:47:04.303007 (1 row)`, затем `/ready` → `{"status":"ready"}` |
| 6 | NetworkPolicy пропускает нужный трафик и режет запрещённый | запросы из `release-board-raw` и из `default` через ClusterIP | разрешённый: `{"status":"alive"}`; запрещённый: `Connection refused` (k3s применяет iptables REJECT, а не DROP — трафик рвётся сразу) |
| 7 | 30 запросов из отдельного Pod через ClusterIP, удаление Pod после 10-го | `./scripts/k8s-load-test.sh` | итог скрипта: `успехов (200): 30`, `ошибок (FAIL): 0`, `DONE: 1`; запросы 11–30 после удаления `release-board-api-65d6466679-jtvf5` — все `200` |
| 8 | Лимиты, probes и securityContext в фактическом Pod spec | jsonpath по живому Pod | `resources: {"limits":{"cpu":"500m","memory":"256Mi"},"requests":{"cpu":"50m","memory":"96Mi"}}`; `probes: startup=/live readiness=/ready liveness=/live`; `podSC: runAsUser=10001 runAsNonRoot=true seccomp=RuntimeDefault`; `roRoot=true noEscalate=false caps=["ALL"] sa=release-board-api grace=30` |

### PDB, остановка трафика и доступ (ТЗ, строка 225)

- `preStop: sleep 5` при `terminationGracePeriodSeconds: 30` и
  максимальной длительности запроса 2 с (`--max-time 2`): под сначала
  выводится из среза адресов, и только потом получает SIGTERM.
- PDB `minAvailable: 1` ограничивает **добровольные** прерывания
  (drain, eviction из-за обслуживания), но не защищает от прямого
  `kubectl delete pod` и от падения узла — это практическое
  подтверждение: все тестовые удаления подов проходили напрямую и PDB
  их не блокировал (см. также `ALLOWED DISRUPTIONS` в выдаче
  `kubectl get pdb`).
- NodePort не открывался. Ручные проверки — только через
  `kubectl port-forward`; нагрузочный тест шёл из отдельного Pod
  внутри кластера через ClusterIP, потому что port-forward привязан
  к одному Pod'у и балансировку не доказывает.

### Runbook и воспроизводимость

- `docs/runbooks/kubernetes-diagnostics.md` — порядок диагностики:
  context → events → workload → describe → logs → endpoints → DNS →
  сеть → ресурсы → storage; у каждой команды указан закрываемый
  вопрос и что означает её вывод (exit codes, Reason/Message в Events).
- `scripts/k8s-load-test.sh` — доказательство п.7 одной командой:
  прогрев соединения, 30 запросов раз в секунду через ClusterIP из
  одноразового пода `api-load`, удаление Pod после 10-го запроса,
  дожидание rollout, счётчики итога и лог в `/tmp/api-load.log`.

### Решения стенда

| Проявление | Причина | Решение |
| --- | --- | --- |
| `Key is duplicated` при apply одного файла | потерян разделитель `---` между документами YAML | разделитель восстановлен, `Valid: 2` |
| StatefulSet не пересоздавал упавший Pod после правки спеки | режим `OrderedReady` создаёт Pod только при нехватке реплик | `kubectl delete pod postgres-0`, затем `wait --for=create` → `wait Ready` |
| Pod PostgreSQL работал от root и не писал в том | local-path не применяет `fsGroup` | init-контейнер `chown-pg-data` (busybox) |
| Пробы не срабатывали | k3s не исполняет `sh -c` внутри `CMD-SHELL` | exec-форма `["sh", "-c", ...]` |
| Первый запрос свежесозданного пода-клиента — `Connection refused` | гонка контейнера при старте (в спокойном состоянии не воспроизводится) | прогрев соединения в скрипте до начала отсчёта; факт зафиксирован: попытка 1 прогрева — `code=000`, успешна со 2-й |
| `kubectl wait` отвечал `NotFound` сразу после удаления | wait не ждёт появления объекта | сначала `--for=create`, затем `condition=Ready` |
| После выключения хоста контейнеры `Up`, но API кластера не отвечает | k3s не поднимается автоматически | `docker restart k3d-release-board-server-0` |

### Итоги этапа 4

- Все объекты ТЗ (строки 196–212) применены в `release-board-raw`;
  каждый прошёл kubeconform закреплённой версии, клиентский dry run
  и проверку состояния после записи.
- Восемь доказательств строк 214–223 выполнены (таблица выше), включая
  п.7: `30` успехов, `0` ошибок, `DONE`.
- Стенд воспроизводим одной командой на каждый блок: кластер —
  `deploy/k3d/cluster.yaml`, тест п.7 — `scripts/k8s-load-test.sh`,
  диагностика — `docs/runbooks/kubernetes-diagnostics.md`.
- Изменения этапа: `deploy/k3d/cluster.yaml`, `deploy/k8s/base/`
  (namespace, configmap, secret.example, postgres, api, serviceaccount,
  pdb, networkpolicy), `scripts/k8s-load-test.sh`,
  `docs/runbooks/kubernetes-diagnostics.md`, `docs/report.md` — единым PR.

---

## Этапы 5–8

Записи добавляются по мере выполнения.
