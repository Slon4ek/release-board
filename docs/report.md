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
| `7c1911d` | `Dockerfile`, `.dockerignore`, `Makefile` (docker-*), отчёт (этап 3), `docs/environment.md` | [#17](https://github.com/Slon4ek/release-board/pull/17) |
| `6791ae7` | манифесты k8s для стенда k3d (namespace, configmap, secret.example, postgres, api, serviceaccount, pdb, networkpolicy), `deploy/k8s/README.md`, `scripts/k8s-load-test.sh`, runbook диагностики, отчёт (этап 4) | [#18](https://github.com/Slon4ek/release-board/pull/18) |
| `a1e4c35` | отчёт: срезы #17–#18 в таблице этапа 2, ссылка `PR #18 (6791ae7)` в итогах этапа 4 | [#19](https://github.com/Slon4ek/release-board/pull/19) |
| `10be8e4` | отчёт (этап 5: k3s-кластер), `docs/environment.md` (kubectl, kubeconform, k3s на VM, QEMU, раздел VM), `.gitignore`: блок kubeconfig | [#20](https://github.com/Slon4ek/release-board/pull/20) |

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
  `docs/runbooks/kubernetes-diagnostics.md`, `docs/report.md` — единым PR #18 (6791ae7).

---

# Черновик раздела отчёта: «## Этап 5. Отдельный k3s-кластер»

Назначение: вставить в `docs/report.md` **перед** заголовком `## Этапы 5–8`
(заголовок «Этапы 5–8» оставить на месте — под ним позже допишутся
разделы 6–8). Дата проверок агентом: 2026-10-09.

---

## Этап 5. Отдельный k3s-кластер

Дата работ: 2026-10-08 – 2026-10-09. Контекст кластера: `k3s-release-board`
(проверка контекста перед любой командой очистки — ТЗ, строка 245).
Команды и подтверждающие строки зафиксированы по факту выполнения; полные
логи не копируются. Коды завершения указаны для проверок, перепроверенных
2026-10-09.

### Профиль VM (ТЗ, строка 234)

| Параметр | Значение |
| --- | --- |
| Гипервизор | KVM: `qemu-system-x86_64` 10.2.1, запуск `-enable-kvm -cpu host -smp 2 -m 4096` (скрипт `start-vm.sh`, консоль `-nographic` в tmux) |
| ОС | Ubuntu 24.04.5 LTS, kernel `6.8.0-146-generic` (в журнале при закрытии 5.1 — `6.8.0-142`; пакет `-146` установлен apt 2026-10-08 18:36 по `dpkg.log`, активен после ребута) |
| CPU | 2 vCPU (`-smp 2`, Intel Core i5-12450H) |
| RAM | 4096 MiB (`-m 4096` = ровно 4 ГБ; в госте видно ~3.8 GiB из-за firmware-резервов), swap 0 B |
| Диск | qcow2: виртуальный 50 GiB, на диске 3.25 GiB (2026-10-09), backing-файл — cloud-образ `noble-server-cloudimg-amd64.img`; в госте `/dev/vda` 50 ГБ, раздел `/` = 48 ГБ (занято ~4.5 ГБ) |
| Сеть | qemu user-mode (slirp) NAT: `ens3` 10.0.2.15/24, шлюз 10.0.2.2 (DHCP), пробросы 2222→22 и 6443→6443 |
| Доступ | SSH `ubuntu@localhost -p 2222`, парольный `sudo` не требуется; развёрнута cloud-инициализацией (`seed.iso`) |

Требование ТЗ «2 vCPU, 4 ГБ RAM, диск от 20 ГБ» выполнено: `-m 4096` даёт
ровно 4 ГБ, диск — с запасом. Swap отсутствует (0 B): на стенд api+postgres
хватает (после подъёма k3s доступно ~2.7 GiB), при OOM — добавить.
SSH-консоль qemu держалась в tmux.

### Установка: сверка install.sh (ТЗ, строка 233)

Установщик брался не «с полки», а с точного upstream-коммита и сверялся в
двух независимых копиях до запуска:

| Команда | Код | Подтверждающий фрагмент |
| --- | --- | --- |
| `git ls-remote --tags https://github.com/k3s-io/k3s 'refs/tags/v1.35.5+k3s1*'` | 0 | lightweight-тег (без `^{}`), коммит `6a4781ad53ee5cad273bedcd9462ae36ac97d798` |
| `git show 6a4781a:install.sh` (клон `--depth 1`) vs `curl raw.githubusercontent.com/.../6a4781a/install.sh` → `diff` | 0 | `DIFF OK`, 1160 строк |
| `sha256sum install.sh` (обе копии) | 0 | `8598e002e61d658fed7b7542fc6d2c66d8da6eae69e088830105d2ee1ffb6d91` |
| повторная сверка 2026-10-09: `curl -sL raw.../6a4781ad.../install.sh \| sha256sum` | 0 | тот же хеш `8598e002…` |
| `sudo INSTALL_K3S_VERSION=v1.35.5+k3s1 sh /tmp/install-raw.sh` | 0* | `Using v1.35.5+k3s1 as release`, `Verifying binary download`, юнит `enabled` + `started` |

\* Коды строк «diff» и установки — из журнала 2026-10-08: они не
перепроверялись повторно (временные файлы удалены), результат
подтверждён выходными данными (`DIFF OK`; юнит `enabled`+`started`) и
повторной сверкой SHA-256 2026-10-09.

Код установщика просмотрен до запуска (1160 строк): скачивает только с
`github.com/k3s-io/k3s/releases` (плюс S3 для dev-сборок), сверяет SHA-256
бинаря с release-asset, ставит `/usr/local/bin/k3s` и симлинки
`kubectl`/`crictl`/`ctr`, создаёт systemd-юнит `Type=notify,
Restart=always`, env-файл с правами 0600, чистит старые iptables-правила
`KUBE-`/`CNI-`/flannel и имеет штатный `uninstall`. Версия закреплена
параметром установщика `INSTALL_K3S_VERSION` (ТЗ, строка 233).

### Роли k3s server и agent (ТЗ, строка 235)

`k3s` — один бинарник с двумя режимами: `k3s server` и `k3s agent`.

**Server** в нашей single-server установке совмещает три роли на одном узле:

- **control-plane**: `kube-apiserver` (точка входа кластера),
  `kube-scheduler` (распределение Pod'ов по нодам), `kube-controller-manager`
  (следит, чтобы реальность совпала с описанным состоянием),
  `cloud-controller-manager` — имена видны по клиентским сертификатам в
  `/var/lib/rancher/k3s/server/tls/` (`client-kube-apiserver`,
  `client-scheduler`, `client-kube-controller-manager`,
  `client-k3s-cloud-controller`);
- **datastore**: вместо etcd — SQLite через kine: сокет
  `server/kine.sock`, данные в `server/db/state.db` (+ `-shm`, `-wal`).
  Хранилище кластера лежит на диске того же узла — свойство
  single-server, а не отдельный кластер БД;
- **worker**: `kubelet` (запускает Pod'ы), `kube-proxy` (программирует
  сетевые правила), `containerd` (контейнерный рантайм), flannel/CNI,
  а также управляющие Pod'ы из статичных манифестов: CoreDNS,
  Traefik, local-path-provisioner, metrics-server.

**Agent** — только worker-часть: kubelet + kube-proxy + containerd,
подключается к API server. В нашей установке agent-узлов нет — всё
перечисленное живёт на единственной ноде `k3s-vm`.

Практическое подтверждение: taint на server-ноде не ставится, и системные
Pod'ы, и наши `release-board-api`/`postgres` бегают на том же узле:

```text
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.node-role\.kubernetes\.io/control-plane}{"\t"}{range .spec.taints[*]}{.key}={.value}{end}{"\n"}{end}'
k3s-vm  true      ← роль control-plane есть, тaint-строки нет (exit 0)
```

### Проверки установки (ТЗ, строка 236)

| Проверка | Команда | Код | Результат |
| --- | --- | --- | --- |
| Служба | `systemctl is-enabled k3s` / `systemctl is-active k3s` | 0 / 0 | `enabled` / `active` — автозапуск при загрузке ОС |
| Узел | `kubectl --context k3s-release-board get nodes` | 0 | `k3s-vm  Ready  control-plane  v1.35.5+k3s1  10.0.2.15  containerd://2.2.3-k3s1` (версии k3s и узла перекрёстно совпадают) |
| Контейнеры CRI | `ssh … 'sudo crictl ps -q \| wc -l'` | 0 | `6` до стенда (coredns, traefik, svclb ×2, metrics-server, local-path), `9` после — + postgres + 2×api |
| Версия | `ssh … 'sudo k3s --version'` | 0 | `k3s version v1.35.5+k3s1 (6a4781ad)` / `go version go1.25.9` — SHA бинаря совпадает с upstream-коммитом установки |
| API на хосте | `curl -sk https://127.0.0.1:6443/` | 0 | `401` — проброс 6443 работает, без клиента сертификата API отвечает отказом |

`k3s version` (без `--`) отвечает `No help topic for 'version'` (rc=3) —
рабочая форма на этой версии `k3s --version`.

### kubeconfig: защищённый локальный путь (ТЗ, строки 238–240)

- kubeconfig на VM уже содержал `server: https://127.0.0.1:6443` — подмена
  адреса API не понадобилась; проброс 6443 на хост подтверждён ответом 401.
- Перенос: копия в `/tmp` на VM → `scp -P 2222` на ноутбук →
  `~/.kube/k3s-release-board.yaml`, `chmod 600` →
  `kubectl config rename-context default k3s-release-board` (имя контекста
  по ТЗ, строка 245) → временная копия на VM удалена.
- В основной конфиг добавлен без подмены: `kubectl config get-contexts`
  показывает оба контекста (`k3d-release-board`, `k3s-release-board`), `get
  nodes` отвечает на обоих.

Проверки для ТЗ, строки 239–240:

| Команда | Код | Результат |
| --- | --- | --- |
| `git check-ignore -v k3s-release-board.yaml` | 0 | `.gitignore:58:k3s-release-board.yaml` — файл под правилом |
| `git ls-files \| grep -i kubeconfig` | 1 | пусто: в Git нет ни kubeconfig, ни файлов с этим именем (grep exit 1 = «не найдено», здесь это успех) |
| `git check-ignore -v kubeconfig.yaml` | 0 | `.gitignore:57:kubeconfig*.yaml` — файл под правилом |

В `.gitignore` блок kubeconfig-файлов дополнен (`568daf0`, ветка
`feature/stage5-report`): 8 добавленных и 4 удалённых строк — блок собран
в конец файла (строки 53–58), добавлены `kubeconfig*.yaml` и
`k3s-release-board.yaml`.

### Перечень упакованных компонентов (ТЗ, строка 241)

Состав зафиксирован по факту установки `v1.35.5+k3s1` (ТЗ требует
оговорку: между релизами состав меняется):

- **статичные манифесты** `/var/lib/rancher/k3s/server/manifests/`:
  `ccm.yaml`, `coredns.yaml`, `local-storage.yaml`, `metrics-server/`,
  `rolebindings.yaml`, `runtimes.yaml`, `traefik.yaml`;
- **чарты** `/var/lib/rancher/k3s/server/static/charts/`:
  `traefik-39.0.701+up39.0.7.tgz`, `traefik-crd-39.0.701+up39.0.7.tgz`
  (klipper-helm ставит Traefik при старте);
- **datastore**: `server/db/state.db` + `-shm` + `-wal`, сокет
  `server/kine.sock` (SQLite через kine);
- **бинари** `data/<sha>/bin/`: k3s (+ `k3s-agent`, `k3s-server`,
  `k3s-certificate`, `k3s-etcd-snapshot`, `k3s-secrets-encrypt`,
  `k3s-token`, `k3s-completion`), kubectl, containerd,
  containerd-shim-runc-v2, runc, ctr, crictl, cni, flannel, host-local,
  conntrack, slirp4netns, fuse-overlayfs, busybox (+ applets);
- **сетевой тулсет** `bin/aux/`: iptables/ip6tables/arptables/ebtables в
  вариантах legacy и nft, nft, xtables-multi — упакован k3s, не зависит от
  iptables хоста;
- **образы** (`crictl images --digests`, 2026-10-09): mirrored-coredns
  1.14.3, mirrored-metrics-server v0.8.1, mirrored-library-traefik 3.6.13,
  local-path-provisioner v0.0.36, klipper-lb v0.4.17, klipper-helm
  v0.10.0-build20260513, mirrored-pause 3.6, mirrored-library-busybox
  1.37.0 — плюс наши postgres 16.15, busybox 1.37.0 и release-board 1.0.0.

### Передача образа в k3s (ТЗ, строка 242)

Registry k3d (`k3d-release-board-registry.localhost:5000`) находится в
Docker-сети k3d и из VM недоступен — поэтому выбран второй путь ТЗ:
документированный импорт в containerd:

```text
docker save release-board:1.0.0 -o /tmp/release-board.tar   → 77M (одна картинка, два имени)
scp -P 2222 /tmp/release-board.tar ubuntu@localhost:/tmp/
ssh … 'sudo k3s ctr images import /tmp/release-board.tar'    → namespace k8s.io (= k3s)
k3s ctr images tag docker.io/library/release-board:1.0.0 \
  k3d-release-board-registry.localhost:5000/release-board@sha256:727536d5…
```

Алиас создан на digest-destination: `k3s ctr -n k8s.io images ls | grep
release-board` показывает **две ссылки на один digest**
`sha256:727536d53a127…aae8159b5` (тот же, что push в registry на этапе 3).
Pod'ы работают по ссылке из манифестов
`…registry.localhost:5000/release-board@sha256:727536d5…`, и
`status.containerStatuses.imageID` возвращает тот же digest — манифесты
этапа 4 применимы на k3s без правок. Временные tar удалены после импорта.

### Перезапуск VM и сохранность данных (ТЗ, строка 243)

Порядок: стенд `release-board-raw` развёрнут на контексте
`k3s-release-board` (те же манифесты `deploy/k8s/base/`, порядок из
`deploy/k8s/README.md`) → маркер в базе → `sudo reboot` → ожидание →
проверки:

```bash
# до ребута: маркер в той же таблице, что и в проверке этапа 4 (п.5)
kubectl --context k3s-release-board exec -n release-board-raw postgres-0 -- \
  psql -U release_board -d release_board -c "CREATE TABLE IF NOT EXISTS durability_check(note text, at timestamp default now()); INSERT INTO durability_check(note) VALUES ('before-reboot-k3s');"
#   CREATE TABLE / INSERT 0 1

# после ребута
kubectl --context k3s-release-board wait --for=create node/k3s-vm --timeout=180s        # node/k3s-vm condition met
kubectl --context k3s-release-board wait --for=condition=Ready node/k3s-vm --timeout=300s  # node/k3s-vm condition met
kubectl --context k3s-release-board get pods -n release-board-raw -o wide
#   postgres-0, release-board-api ×2 — 1/1 Running, RESTARTS 1 (70s ago)  ← Pod'ы не пересоздавались
kubectl --context k3s-release-board wait --for=condition=Ready pod/postgres-0 -n release-board-raw --timeout=180s
#   pod/postgres-0 condition met
kubectl --context k3s-release-board exec … psql -c "SELECT note, at FROM durability_check;"
#   before-reboot-k3s | 2026-10-09 08:34:16.587177   ← строка пережила reboot
kubectl --context k3s-release-board port-forward -n release-board-raw svc/release-board-api 8081:8000 &
sleep 3; curl -sS localhost:8081/ready; kill %1
#   {"status":"ready"}   ← 200, SELECT 1 до базы проходит
```

Дополнительно после перезагрузки сессии проверено повторно
(2026-10-09, только чтение): `ssh … 'uptime; systemctl is-active k3s'` →
`up 21 min` + `active` — k3s поднялся сам, юнит `enabled` при установке;
маркер и `/ready` — как выше (exit 0 на обеих проверках).

Что это доказывает и чего не доказывает: перезапуск узла не привёл к потере
данных на PVC и кластер вернулся в ожидаемое состояние без ручных
действий. Это **не** защита от потери диска или всей VM: для таких
сценариев backup/restore выполняется на этапе 8 (ТЗ, строка 243).

### Итоги этапа 5

- Пункты 1–7 ТЗ (строки 234–242) и проверка п.243 выполнены: профиль VM,
  сверенный установщик, роли server/agent, systemctl/kubectl/crictl,
  kubeconfig `0600` вне Git, перечень компонентов, импорт образа в
  containerd, перезапуск VM с сохранением данных.
- Изменения в репозитории на этот этап: `.gitignore` (kubeconfig-блок) —
  коммит `568daf0` в ветке `feature/stage5-report`; сам отчёт и
  `docs/environment.md` — этим же PR.
- Данные PostgreSQL в k3s живут на PVC `local-path` (`pg-data-postgres-0`);
  устойчивость к ребуту подтверждена, устойчивость к потере диска — нет
  (этап 8).

---

## Этап 6. Helm chart и жизненный цикл релиза

Дата работ: 2026-10-09 – 2026-10-10.

### Развилки и версия Helm (ТЗ, строки 247–307)

| Развилка | Решение | Почему |
| --- | --- | --- |
| Версия Helm | **3.20.2** (коммит `8fb76d6`, go1.25.9) | Требуется 3.19+; `3.20.3` на get.helm.sh ещё нет. Флаги Helm 3: `--install --atomic --wait --timeout 3m`; версия зафиксирована в `docs/environment.md` |
| PostgreSQL | **Свой StatefulSet** в chart | ТЗ допускает; переиспользованы проверенные манифесты этапа 4, без внешних репозиториев и сети |
| Миграции | **Hook Job** `post-install,pre-upgrade` + retry-цикл | Чистый `pre-install` сработал бы ДО появления postgres; при `helm rollback` хук не выполняется — совпадает с требованием «rollback не откатывает данные» |

### Состав chart (`deploy/helm/release-board`, 17 файлов)

| Файл | Назначение |
| --- | --- |
| `Chart.yaml` | `version: 0.1.0` (версия chart'а) против `appVersion: "1.0.0"` (версия приложения) — не путать |
| `values.yaml` | значения по умолчанию; без `latest`, привилегий и выключенных limits |
| `values-k3d.yaml` / `values-k3s.yaml` | только различия сред: registry k3d vs `repository: release-board` + `pullPolicy: Never` (импорт в containerd) |
| `values.schema.json` | ловит `latest`, плавающий minor postgres, выкинутые поля — ошибку отдаёт helm-команда, а не кластер |
| `templates/_helpers.tpl` | имена, общие лейблы, selector-лейблы (name + instance — «адрес» Pod'а) |
| `serviceaccount.yaml`, `configmap.yaml` | SA без токена; MODE/DB_HOST/DB_PORT |
| `deployment.yaml`, `service.yaml` | API: env из ConfigMap/Secret, пробы, preStop, readOnlyRootFilesystem + emptyDir `/tmp` |
| `pdb.yaml` | `minAvailable: 1` |
| `networkpolicy.yaml` | default-deny + allow-api-from-namespace + allow-postgres-from-api (api и migrate) |
| `postgres-statefulset.yaml`, `postgres-service.yaml` | STS + PVC из `volumeClaimTemplates`, init-контейнер chown (local-path игнорирует `fsGroup`) |
| `migrate-job.yaml` | хук alembic с retry ожидания БД до 3 минут |
| `tests/test-live.yaml` | helm test: `/live` + чтение `/releases` из БД |
| `NOTES.txt` | подсказки после установки |

Секреты: chart только ссылается на заранее созданный Secret
(`dbSecret.name`) — ни в values, ни в `--set`, ни в shell-историю, ни в
отчёт пароль не попадает.

### Проверки перед установкой (ТЗ, строка 299)

| Команда | Код | Подтверждающий фрагмент |
| --- | --- | --- |
| `helm lint deploy/helm/release-board` | 0 | `1 chart(s) linted, 0 chart(s) failed` |
| `helm template … \| kubeconform -strict -summary -kubernetes-version 1.35.5` | 0 | `Summary: 12 resources found - Valid: 12, Invalid: 0` |
| то же `--show-only templates/migrate-job.yaml` | 0 | `1 resource found - Valid: 1` |
| `helm template … --set image.tag=latest` | ≠0 | отклонён schema: `Does not match pattern` — негативный тест «охранника» |

Версия кластера для kubeconform — 1.35.5 (совпадает с k3s на VM).

### Установка на k3d и helm test (2026-10-09)

```text
ns release-board-helm (отдельный от release-board-raw)
Secret release-board-db создан руками — chart только ссылается
helm install release-board deploy/helm/release-board -n release-board-helm \
  -f values-k3d.yaml --atomic --wait --timeout 3m
→ STATUS: deployed, REVISION: 1; хук migrate — job Completed (retry дождался postgres)
GET /live → {"status":"alive"};  GET /releases → [];  PVC Bound
helm test → Phase: Succeeded (rev 3)
```

### Сценарий релиза (ТЗ, строки 286–297)

| Пункт | Действие | Результат |
| --- | --- | --- |
| 1 | install `1.0.0` | rev 1 deployed (плюс rev 2–3 — upgrade на сохранённый chart, см. грабли) |
| 2 | `POST /releases` | запись UUID `de46081a-7412-47e1-93e4-6f980f4a4e3e` |
| 3–4 | `make docker-build TAG=1.1.0`, push (digest `sha256:e3db450c…`), `helm upgrade --set image.tag=1.1.0` | rev 4; `GET /version` → `{"version":"1.1.0","git_sha":"10be8e4"}`; запись пережила upgrade |
| 5–6 | `--set image.tag=1.2.0-bad --atomic --wait --timeout 2m` | битый тег пойман **раньше раскатки** — на pre-upgrade хуке миграций (ImagePullBackOff → hook timed out): rev 5 failed, автооткат rev 6 «Rollback to 4». Остаточный hook-job удалён вручную (`hook-succeeded` чистит только успешные) |
| 7 | тот же bad-тег + `--no-hooks`, затем `helm rollback release-board 4 --wait` | rev 7 failed `context deadline exceeded`, Pod'ы ImagePullBackOff **рядом с живыми старыми** (rolling update держит старую RS); явный rollback → rev 8 deployed |
| 8 | history, pods, API | 8 ревизий; API Running 1.1.0; UUID записи на месте |

**Развести в отчёте (ТЗ, строка 303):** `helm rollback` возвращает
ресурсы, но **не** восстанавливает содержимое PostgreSQL и **не**
отменяет миграции данных. В прогоне это подтверждено: все миграции до
rollback были идемпотентными для данных, изменений схемы между rev 4 и
rollback не было. При несовместимой миграции — остановить авто-rollback
и применить план совместимости схемы.

### Установка на k3s и перезапуск VM (2026-10-10)

```text
scripts/stand-up.sh k3s → ns release-board-k3s, Secret, STATUS: deployed, REVISION: 1
  (образ берётся из containerd VM — values-k3s.yaml, pullPolicy Never)
GET /live → alive; /version → {"version":"1.0.0","git_sha":"d0a5cbe"}
helm test → Phase: Succeeded
POST /releases → UUID 63d5cdda-181f-4823-847b-3ca907460f82
sudo reboot → systemctl is-enabled k3s = enabled, is-active = active, up 18 min
после ребута: api ×2 и postgres-0 Running (RESTARTS 2 — рестарт после ребута, не падение),
PVC Bound, GET /releases возвращает тот же UUID  ← данные пережили ребут
```

### Скрипты стенда (`scripts/stand-*.sh`)

Повторяющиеся команды вынесены в скрипты; шпаргалка — `scripts/README.md`,
таргеты Makefile: `make stand-{up,smoke,test,status}-{k3d,k3s}`.

| Скрипт | Что делает |
| --- | --- |
| `stand-env.sh` | общий модуль: `CTX/NS/VALUES` по аргументу `k3d\|k3s`, `use_ctx`, `ensure_secret`, `port_forward` |
| `stand-up.sh` | ns + Secret + `helm upgrade --install --atomic --wait --timeout 3m` |
| `stand-smoke.sh` | pods/svc/pvc + `/live` `/releases` `/version` |
| `stand-test.sh` | helm test → Phase + history |
| `stand-status.sh` | history + pods + версия + UUID записей |

Пароль генерируется при первом запуске (`openssl rand -hex 16`) в
`~/.config/release-board/db.env` (chmod 600, вне git); Secret создаётся
только если его нет в кластере.

### Грабли этапа 6

| Проявление | Причина | Решение |
| --- | --- | --- |
| `helm template` падал: YAML parse error в NetworkPolicy | `nindent 16` вместо 14 в `from:` поддокумента | `nindent 14` (уровень matchLabels под-уровня) |
| kubeconform: `volumeClaimTemplates not allowed at /spec/template/spec` | отступ 6 пробелов — уровень контейнеров вместо уровня spec | отступ 2 пробела |
| kubelet: «image has non-numeric user» в helm test | `runAsNonRoot` + именованный юзер `curl_user` образа curlimages/curl | pod-level `runAsUser: 100` |
| Правки шаблонов «не применяются» | `helm test` берёт chart **из релиза**, не с диска | `helm upgrade` перед повторным test (rev 2–3) |
| Первый SYN свежего пода — `Connection refused` (повторение этапа 4) | kube-router допрограммирует Pod в ipsets после старта контейнера | в тесте `curl --retry 8 --retry-connrefused --retry-delay 1` |
| `helm test --logs` → «pod not found», exit ≠ 0 | `hook-succeeded` удаляет успешный test-под мгновенно | в `stand-test.sh`: вывод через `grep -E 'Phase:…' \|\| true` |
| `POST /releases` → 422 «Field required: environment» | API требует `environment`, а не `env` (грабль этапа 5 повторился) | поле `environment` в запросе |

### Итоги этапа 6

- Chart построен и проверен (lint, template→kubeconform, негативный
  schema-тест); оба стенда подняты одним и тем же chart'ом:
  k3d — сценарий релиза п.1–8 пройден, k3s — install + test + ребут VM
  с сохранением данных.
- Версия Helm 3.20.2 зафиксирована в `docs/environment.md`.
- Изменения этапа: `deploy/helm/release-board/` (17 файлов),
  `scripts/stand-*.sh`, `scripts/README.md`, таргеты `stand-*` в
  `Makefile`, `docs/environment.md` (строка Helm), `docs/report.md`.

---

## Этапы 7–8

Записи добавляются по мере выполнения.
