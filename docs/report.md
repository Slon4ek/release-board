# Технический отчёт

Накопительный журнал проекта. Ведётся по мере выполнения этапов: после каждого
этапа сюда попадают выполненные проверки и их результаты. Полные логи сюда не
копируются, фиксируются команда, код завершения, коммит и подтверждающие строки.

Репозиторий: `git@github.com:Slon4ek/release-board.git`, публичный.
URL: `https://github.com/Slon4ek/release-board`.

---

## Карта требований → разделы отчёта → доказательства

Первая навигационная таблица по замечанию проверяющего: где что доказано.

| Требование ТЗ | Раздел отчёта | Доказательство |
| --- | --- | --- |
| Свой репозиторий, лабораторные кластеры локальны (стр. 9–10) | §Шапка, §Этап 2 | `https://github.com/Slon4ek/release-board`; k3d/k3s запущены локально, в git только манифесты |
| Контексты названы `k3d-release-board`/`k3s-release-board`, проверка контекста перед удалением | §Этап 9, «Финальная очистка» | `scripts/stand-cleanup.sh`: guard читает `kubectl config current-context`, сверяет с двумя именами |
| Очистка ограничена двумя именами, ошибка при другом контексте | §Этап 9 | Тест: `KUBECONFIG=/tmp/foreign.kubeconfig` → «чужой контекст», `exit=1`; пустой контекст → `exit=1` |
| Учебные пароли в локальном файле вне git | §Этап 4 | `~/.config/release-board/db.env`, chmod 600, в `.gitignore` |
| Не публиковать kubeconfig, токены, дампы, Secret | §Этап 2, §Этап 5, §Этап 8 | `git ls-files \| grep -i kubeconfig` — пусто; дамп `canonical.dump` — только локально |
| Удалить лабораторные ресурсы, сохранить результат очистки | §Этап 9, «Финальная очистка» | Выводы `stand-cleanup.sh` обеих веток — в разделе ниже |
| Этап 1: сервис и тесты | §Этап 1 | `make lint/typecheck/test` → 0, `72 passed`, срез `29fd6a0` |
| Этап 2: удалённый репозиторий, стратегия веток | §Этап 2 | Таблица срезов (SHA + PR), ruleset Active |
| Ветка поддержки и hotfix | §Ветка поддержки и hotfix | PR #25 (`2b04e1f`), revert #12, forward-port #26 (`9c58706`), тег `v1.1.1` |
| Этап 3: контейнер | §Этап 3 | multi-stage Dockerfile, digest, healthcheck `/live`, скан Trivy |
| Этап 4: манифесты в k3d | §Этап 4 | Доказательства 1–8 (EndpointSlice, PDB, durability_check), тест 30/30 |
| Этап 5: отдельный k3s-кластер | §Этап 5 | `install.sh` SHA-256, готовность узла, reboot-доказательство (маркер пережил ребут) |
| Этап 6: Helm chart и жизненный цикл релиза | §Этап 6 | Revisions стенда до `11`, сценарий релиза, `helm rollback` ≠ восстановление БД |
| Этап 7: CI и выпуск версии | §Этап 7 | Пайплайн, тег `v1.1.0`, `SHA256SUMS`, артефакты по digest |
| Этап 8: диагностика и восстановление | §Этап 8 | Причины инцидентов A–D, `canonical.dump`/`restored.tsv`, runbook `database-recovery.md` |
| Итоговый технический отчёт (стр. 367–389) | §Итоговый технический отчёт | Таблица «укажи» (6 пунктов) и «объясни» (10 пунктов) |
| Официальные материалы (стр. 391) | §Официальные материалы | Ссылки на документацию |

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

| SHA | Назначение | PR                                                      |
| --- | --- |---------------------------------------------------------|
| `256773e` | bootstrap: только `.gitignore`, базовая ветка для первого PR | —                                                       |
| `819b1fe` | инфраструктура, конфигурация, базовый CI | [#1](https://github.com/Slon4ek/release-board/pull/1)   |
| `4ec8fbf` | передача pyright абсолютного пути интерпретатора | [#3](https://github.com/Slon4ek/release-board/pull/3)   |
| `ebd3f9c` | конфигурация, подключение к БД, зависимости | [#2](https://github.com/Slon4ek/release-board/pull/2)   |
| `07a0f15` | модель Release, схемы, начальная миграция | [#4](https://github.com/Slon4ek/release-board/pull/4)   |
| `59cd029` | HTTP API, сервисный слой, обработка доменных ошибок | [#5](https://github.com/Slon4ek/release-board/pull/5)   |
| `5424302` | отчёт, ADR, окружение | [#6](https://github.com/Slon4ek/release-board/pull/6)   |
| `29fd6a0` | тесты DELETE и 409, сверка миграции с моделью, шаг Test в CI, отчёт | [#7](https://github.com/Slon4ek/release-board/pull/7)   |
| `7da226f` | разделение lock-файлов, CI: concurrency, timeout, GIT_SHA, кэш pip; `BASE_DIR` для `.env`; `logger.exception` в `/ready`; `make install-dev` | [#8](https://github.com/Slon4ek/release-board/pull/8)   |
| `59afb8d` | `CONTRIBUTING.md`, шаблон PR, `README.md` | [#9](https://github.com/Slon4ek/release-board/pull/9)   |
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
| `aeded65` | Helm chart этапа 6 (стенды k3d/k3s), скрипты stand-*, make-таргеты, отчёт (этап 6), environment.md (Helm 3.20.2) | [#21](https://github.com/Slon4ek/release-board/pull/21) |
| `648eddb` | Релиз 1.1.0: CHANGELOG, версии chart/app/Makefile; CI: 6 стадий, артефакты для SemVer-тега | [#22](https://github.com/Slon4ek/release-board/pull/22) |
| `f44535d` | Chart: поддержка image.digest (деплой по неизменяемому digest) | [#23](https://github.com/Slon4ek/release-board/pull/23) |
| `9d39dfb` | отчёт (этап 7: CI и релиз v1.1.0) | [#24](https://github.com/Slon4ek/release-board/pull/24) |
| `2b04e1f` | Hotfix: выбор жертвы нагрузочного теста по селектору лейблов (линия 1.1.x) | [#25](https://github.com/Slon4ek/release-board/pull/25) |
| `12af380` | Релиз 1.1.1: синхронизация версий chart/app/Makefile (вершина release/1.1) | — (коммит ветки, не PR)                                 |
| `9c58706` | Hotfix 1.1.1 перенесён в main (forwardport) | [#26](https://github.com/Slon4ek/release-board/pull/26) |
| `08b8cf2` | docs: этап 8 — четыре инцидента, runbook восстановления БД, отчёт | [#27](https://github.com/Slon4ek/release-board/pull/27) |
| `364b717` | docs: Итоговый отчёт — свод всех пунктов ТЗ таблицами | [#28](https://github.com/Slon4ek/release-board/pull/28) |
| `2723173` | Docker: база slim-trixie без apt-get upgrade, `.trivyignore.yaml` — CI зелёный | [#29](https://github.com/Slon4ek/release-board/pull/29) |
| `2e0ecc5` | ci: release зависит от скана, actions по SHA, dependabot weekly | [#30](https://github.com/Slon4ek/release-board/pull/30) |
| `43b51fe` | fix: скрипт очистки стендов с guard'ом по контексту | [#31](https://github.com/Slon4ek/release-board/pull/31) |
| `a958a0e` | feat: bootstrap-скрипт VM k3s (start-vm.sh) | [#32](https://github.com/Slon4ek/release-board/pull/32) |
| `5c47bd8` | docs: scripts README — флаг --tmux в описании start-vm.sh | [#33](https://github.com/Slon4ek/release-board/pull/33) |

Номер PR не совпадает с порядком слияния: PR с исправлением интерпретатора был
открыт раньше, чем PR со схемой базы.

### Защита `main`

Настроена через GitHub Rulesets, Enforcement status `Active`, таргет `main`:

- `Restrict deletions` — удаление ветки запрещено;
- `Block force pushes` — перезапись истории запрещена;
- `Require a pull request before merging` — прямые пушты невозможны;
- `Require status checks to pass`, обязательные проверки `check`, `docker`, `helm` (расширено 2026-10-14 — красный скан теперь блокирует мерж);
- `Require branches to be up to date before merging`;
- разрешён только squash как метод слияния.

Обязательное одобрение не включено намеренно: при работе в одиночку его получить
невозможно, и тогда невозможно было бы ни слить, ни закрыть PR.
Репозиторий публичный, поэтому ограничений тарифа на эти настройки нет.

### CI

В `main` один job `check` с тремя шагами: `Lint`, `Typecheck`, `Test`.
С 2026-10-14 (этап 9) в воротах мержа три job — `check`, `docker`
(сборка образа + Trivy) и `helm`; job `release` зависит от всех трёх.
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
python:3.12.14-slim-trixie@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
```

Digest, а не тег: содержимое базы зафиксировано байт-в-байт, перезапись
тега при пересборке невозможна.

- **`builder`**: в отдельный venv (`/opt/venv`) ставится только
  `requirements.lock` — 27 runtime-пакетов. `requirements-dev.lock`
  в образ не попадает: цель разделения lock-файлов из среза 8 выполнена.
- **`runtime`**: копируется только готовый venv, `src/`, `migrations/`,
  `alembic.ini`. Ни pip, ни компиляторов, ни `.git`, ни `.env`, ни тестов.
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
**Постскриптум 2026-10-14 (этап 9):** база образа переведена на
slim-trixie, слой `apt-get upgrade` удалён; скан: **48 HIGH,
0 CRITICAL** (было 5 CRITICAL), после `.trivyignore.yaml` — `Total: 0`,
job `docker` впервые зелёный.

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
| Гипервизор | KVM: `qemu-system-x86_64` 10.2.1, запуск `-enable-kvm -cpu host -smp 2 -m 4096` (скрипт [`scripts/start-vm.sh`](../scripts/start-vm.sh), в репозитории с PR #32; консоль `-nographic` в tmux) |
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

## Этап 7. CI и выпуск версии

Дата работ: 2026-10-10.

### Пайплайн: шесть стадий (ТЗ, строки 309–323)

`.github/workflows/ci.yml` переписан под шесть стадий ТЗ. Триггеры:
push во все ветки, PR в `main` **и** `release/**`, SemVer-теги `v*`.

| Job | Стадия ТЗ | Что делает | Gate merge |
| --- | --- | --- | --- |
| `check` | 1–2 | lint + typecheck + тесты (postgres service-контейнер) | **да** — Ruleset требует job `check` |
| `docker` | 3–4 | `make docker-build` + Trivy 0.75.0 (HIGH/CRITICAL → exit 1) | нет — остаток 55 разобран в отчёте этапа 3, иначе все PR были бы красными |
| `helm` | 5 | `helm lint` + `template \| kubeconform -strict` (0.8.0, k8s 1.35.5) | нет |
| `release` | 6 | **только SemVer-тег**: `docker save` + `helm package` + проверка содержимого + `SHA256SUMS` + upload-artifact (90 дней) | нет; `needs: [check, helm]` — от `docker` не зависит |

На первом PR этапа поведение подтвердилось: `check`/`helm` —
Successful, `docker` — Failing (Trivy, по задумке), `release` —
Skipped (условие «только тег»).

Соответствие ТЗ:

- **секретов нет ни в одном шаге** — передавать fork'ам нечего;
  `permissions: contents: read` — CI-токен только читает;
- версии actions закреплены (`checkout@v7`, `setup-python@v7`,
  `upload-artifact@v7`), Trivy `0.75.0` и kubeconform `0.8.0` — числами;
- кэш pip по `requirements-dev.lock`;
- runner **не** подключается к k3d/k3s: Docker socket и K8s API наружу
  не открываются, deploy-job'а в CI нет — локальное развёртывание
  выполняется вручную из артефактов (ниже).

### Релиз v1.1.0 (ТЗ, строки 325–334)

| Пункт ТЗ | Выполнено |
| --- | --- |
| `CHANGELOG.md` | создан (Keep a Changelog): 1.1.0 (Added/Changed/Notes) + 1.0.0 |
| сверка Git tag ↔ Chart.yaml ↔ appVersion ↔ тег контейнера | `Chart.yaml` version 1.1.0 + appVersion "1.1.0", values tag "1.1.0", Makefile `TAG ?= 1.1.0` — один коммит `9b68242` |
| аннотированный тег, отдельный push | `git tag -a v1.1.0` → `git push origin v1.1.0` отдельной командой; `git cat-file -t v1.1.0` → `tag` (не lightweight) |
| проверка в интерфейсе | `git ls-remote --tags origin v1.1.0` → `5984bc80…`; Release-страница: `releases/tag/v1.1.0` |
| архив chart + проверка содержимого до публикации | в job `release`: `helm package` + `tar -tzf` (содержимое в логе job'а) + `sha256sum > SHA256SUMS` |
| release notes: изменения / миграция / откат | три секции в Release v1.1.0 (`gh release create`) |

Артефакты release-job'а (`release-1.1.0`, хранение 90 дней):
OCI-образ `release-board-1.1.0.tar.gz` (76 MB), Helm chart
`release-board-1.1.0.tgz` (5.8 KB), `SHA256SUMS`.

### Локальное развёртывание из OCI-архива без пересборки (ТЗ, строки 319–323)

```text
gh run download --name release-1.1.0 → 3 файла
sha256sum -c SHA256SUMS              → оба: OK
docker load -i release-board-1.1.0.tar.gz  (без пересборки)
docker tag + docker push в registry k3d
  → digest: sha256:ab58e992bee6...   ← OCI-манифест в registry
helm upgrade ... --set image.digest=sha256:ab58e992...
  → REVISION: 11
GET /version → {"version":"1.1.0","git_sha":"648eddb"}  ← коммит тега
imageID обоих Pod'ов: ...@sha256:ab58e992...            ← байты CI-артефакта
```

Цепочка доказана двумя независимыми сверками: контрольная сумма
**файла** (`b1b3b25c…` — скачано без искажений) и digest
**манифеста** (`ab58e992…` — в registry ровно те байты); сравнение —
по ссылкам на один platform manifest (`docker manifest inspect`),
как требует ТЗ.

### Грабль: тег перезаписан, кэш IfNotPresent взял старое

Первый upgrade на тег 1.1.0 поднял **старый** образ: `/version`
ответил `git_sha: 10be8e4` (коммит этапа 5) вместо `648eddb` (коммит
тега). Причина: в registry k3d уже лежал `1.1.0` от этапа 6
(digest `e3db450c…`), ноды закэшировали его по тегу, `IfNotPresent`
свежий pull не сделал. Подтверждение: `imageID` Pod'ов =
`sha256:e3db450c…`.

Фикс — требование ТЗ «укажи digest в workload»: в chart добавлен
`image.digest` (default пустой = поведение прежнее), хелпер
`release-board.imageRef` рендерит `repository@digest` приоритетно над
`repository:tag`, schema принимает только `^$|^sha256:[a-f0-9]{64}$`.
PR #23 (`f44535d`). Повторный upgrade с digest: `/version` →
`git_sha: 648eddb`, `imageID` = `ab58e992…`.

Вывод: тег — имя, digest — байты. При перезаписи тега в registry
кэш `IfNotPresent` молча отдаст старое; для воспроизводимого деплоя
workload должен ссылаться на digest.

### Итоги этапа 7

- Пайплайн из 6 стадий работает на push/PR/SemVer-тег; gate merge —
  только `check` (имя сохранено под Ruleset), Trivy-остаток виден, но
  не блокирует (на момент этапа 7; с 2026-10-14 gate — `check`,
  `docker`, `helm`, остаток закрыт ignore'ом — см. «Этап 9»).
- Релиз `v1.1.0`: аннотированный тег `5984bc80…` → коммит `648eddb`,
  Release с notes (изменения/миграция/откат), артефакты в Actions.
- Артефакты развёрнуты на k3d **без пересборки**, деплой по digest
  `ab58e992…`, `/version` сверяет с коммитом тега.
- Изменения этапа: `.github/workflows/ci.yml`, `CHANGELOG.md`,
  версии в `Chart.yaml`/`values.yaml`/`Makefile`, поддержка
  `image.digest` в chart — PR #22 и #23.

---
## Ветка поддержки и hotfix

Дата работ: 2026-10-12. Пункты ТЗ: строки 165–178 (п. 1–7), выполнены
после этапа 7.

### Сценарий и что получилось

Линия `release/1.1` отпочковалась от тега `v1.1.0`, получила hotfix и
закрылась; фикс перенесён в `main` отдельным PR.

```text
648eddb ── v1.1.0 ── 2b04e1f (фикс) ── 12af380 ── v1.1.1 ── [release/1.1 удалена]
   │                                                линия 1.1.x
   └── f44535d (#23) ── 9d39dfb (#24) ── 9c58706 (#26 forwardport) ── [main]
```

| П. ТЗ | Выполнено |
| --- | --- |
| 1. main уходит вперёд | Проверено: `main` впереди тега на 2 коммита (#23, #24) — отдельного изменения не потребовалось |
| 2. `release/1.1` от тега → push | `git branch release/1.1 v1.1.0` → push; Ruleset: restrict deletions, block force pushes, require PR + check `check` |
| 3. `hotfix/1.1.1`, проверяемая ошибка, PR → squash | Ошибка: `k8s-load-test.sh` выбирал жертву по жёсткому `app=$SVC`, на helm-стенде лейблы `app.kubernetes.io/*` → пустой селектор, падение. Фикс: `LABEL_SELECTOR` с дефолтом прежнего поведения. PR #25 → squash `2b04e1f` |
| 4. аннотированный тег `v1.1.1`, отдельный push, проверка в интерфейсе | Тег на `12af380` (вершина линии), push отдельной командой, `ls-remote` подтверждает; release-job CI зелёный |
| 5. `fix/forwardport-1.1.1` от `main`, cherry-pick, отдельный PR | Перенесён только фикс `2b04e1f` (версионный коммит линии — нет). PR #26 → squash `9c58706` в `main` |
| 6. удалить `hotfix/1.1.1` и `release/1.1`, `fetch --prune` в обоих клонах | Удалены локально и на сервере; prune в `release_board` и `release-board-2`; Ruleset на удалённую ветку убран |
| 7. runbook сравнения команд | Выполнен ранее — PR #16 (`docs/runbooks/git-recovery.md`) |

### Функциональная проверка фикса

Прогон на helm-стенде k3s (ns `release-board-k3s`, лейблы
`app.kubernetes.io/*`):

```text
LABEL_SELECTOR=app.kubernetes.io/name=release-board scripts/k8s-load-test.sh
→ после 10-го запроса удаляем: release-board-api-67b8c554b9-rtt5t
успехов (200): 30
ошибок (FAIL): 0
```

До фикса на том же стенде `kubectl get pod -l app=release-board-api` →
`No resources found` — баг воспроизводился детерминированно. Дефолт
`LABEL_SELECTOR=app=$SVC` равен прежней строке — raw-стенд без
изменений.

### Итоги

- Полный цикл ветки поддержки отработан на реальном фиксе: ветка
  линии → hotfix → PR/squash → тег → forwardport → закрытие веток.
- Имена обязательных проверок (`check`) и правила squash merge
  действовали на `release/1.1` так же, как на `main` — линия
  поддержки не была «дырой» в защите.
- CI release-job впервые отказал в выпуске и обоснованно — это была
  не поломка CI, а неполный релиз со стороны релизёра.
- Изменения этапа в репозитории: `scripts/k8s-load-test.sh` (фикс),
  `CHANGELOG.md`/`Makefile`/`Chart.yaml`/`values.yaml` (версии 1.1.1)
  — PR #25, #26.

---

## Этап 8. Диагностика и восстановление

Дата работ: 2026-10-13. Пункты ТЗ: строки 338–364. Все четыре
инцидента воспроизведены во временном k3d-кластере `incidents`
(контекст `k3d-incidents`, неймспейс `release-board-incidents`),
после инцидентов лаборатория раскатана.

### Лаборатория (ТЗ, строки 338–339)

```text
k3d cluster create incidents -p 8081:80 --registry-create k3d-incidents-registry:0.0.0.0:5002
namespace release-board-incidents + secret release-board-db (пароль openssl rand -hex 16)
локальный образ 1.1.0 → mirror k3d-incidents-registry:5002
helm upgrade --install ... --set image.tag=1.1.0 --atomic   → REVISION 1
GET /live 200, GET /version {"version":"1.1.0","git_sha":"648eddb"}  ← стартовое состояние
```

### Инцидент A: ImagePullBackOff (ТЗ, строка 340)

| Шаг | Что сделано и что получено |
| --- | --- |
| Гипотеза | Несуществующий тег образа → kubelet не может получить манифест |
| Наблюдение | `kubectl get pods` → `ImagePullBackOff`; `describe` → Events: `manifest unknown` / `ErrImagePull`, `Back-off 21s`; перезапуск Pod не помогает (тот же pull) |
| Команды | `kubectl set image deploy/release-board-api ...=release-board:9.9.9-not-exist` (слом мимо helm); `describe pod` |
| Причина | registry отвечает NotFound → ErrImagePull → экспоненциальный back-off. Rolling update держал старые поды, трафик не прерывался |
| Исправление | `helm upgrade --set image.digest=sha256:ab58e992bee6...` → REVISION 3 deployed |
| Проверка | `rollout status` → успешно; `imageID` обоих подов = `@sha256:ab58e992...`; `/live` `{"status":"alive"}`, `/version` `{"version":"1.1.0","git_sha":"648eddb"}` |

`helm upgrade --set image.tag=9.9.9` сломал бы и pre-upgrade
хук миграции (общий `imageRef`) — слом только через `kubectl set image`
или `--no-hooks`.

### Инцидент B: трафик не приходит к Pod (ТЗ, строка 342)

| Шаг | Что сделано и что получено |
| --- | --- |
| Гипотеза | Разойдутся readiness пода и маршрут Service (probe или labels) |
| Наблюдение | JSON-патч readiness `/ready` → `/wrong-path`: новый под `0/1`, condition `Ready=False (ContainersNotReady)`, в EndpointSlice его адрес `ready: false`, старые поды `ready: true`; при стратегии Recreate все адреса `ready: false` → изнутри кластера `000` (DNAT-правила нет); рестарт подов не помогает — новый под из того же шаблона |
| Команды | `kubectl patch deployment --type=json` (слом/фикс пути probe), `--type=strategic` (Recreate), `get endpointslice ... grep -B4 'ready:'`, `kubectl run tmp-curl ... curl -w '%{http_code}'` |
| Причина | kubelet помечает контейнер неготовым → endpoints убирает адрес из EndpointSlice → kube-proxy не программирует DNAT → connection refused. Лечит только правка конфигурации, не перезапуск |
| Исправление | патч probe обратно на `/ready` + `type: RollingUpdate` (`rollingUpdate` после Recreate возвращается `op:"add"`) |
| Проверка | `rollout status` → `successfully rolled out`; slice `ready: true`; tmp-curl → `200` |

Грабли: селектор по
`instance=` ловит и slice postgres (точный —
`kubernetes.io/service-name=release-board-api`); первый `000` — гонка
netpol (лечится `--retry-connrefused`), слом даёт стабильный `000`
после всех ретраев.

### Инцидент C: ошибочная конфигурация (ТЗ, строка 344)

| Шаг | Что сделано и что получено |
| --- | --- |
| Гипотеза | Неверный адрес базы в ConfigMap при живом процессе |
| Наблюдение | `patch configmap DB_HOST=release-board-postgres-typo` + рестарт подов: `/live` → `200`, `/ready` → `503`; в логах `psycopg.OperationalError: connection to server at "198.20.0.34" ... server closed the connection unexpectedly` рядом с `GET /live 200 OK` |
| Команды | `kubectl patch configmap`, `delete pod`, port-forward + `curl -w '%{http_code}'` на `/live` и `/ready`, `logs -l ... \| grep -ci 'DB_PASSWORD\|password='` → `0` |
| Причина | DSN указывает мимо postgres → readiness (`SELECT 1`) падает → 503; `/live` от БД не зависит. В traceback есть хост/порт, но нет пароля — секрет не логируется |
| Исправление | `DB_HOST` обратно на `release-board-postgres` + рестарт (env читается при старте) |
| Проверка | `wait --for=condition=Ready pod` → мет-condition; `/live 200`, `/ready 200`; grep пароля в логах → `0` |

Грабль: ошибка резолва пришла не как NXDOMAIN — ndots:5 прогоняет
search-домены, «голое» имя уходит в upstream-DNS провайдера, wildcard
даёт parking-IP. Порт-форвард, переживший смерть пода, врёт `000`
при полностью здоровом стенде — перед проверкой `pkill -f port-forward`.

### Инцидент D: потеря данных (ТЗ, строки 346–364)

Сценарий по пунктам ТЗ:

| П. ТЗ | Выполнено |
| --- | --- |
| 1. ≥20 записей с известными UUID | `INSERT ... generate_series(1,20)`: UUID `00000000-0000-4000-8000-000000000001..0020`, фиксированные service/version/environment/status/created_at; API отдаёт `20` |
| 2. логический backup + checksum | t0 = `08:46:55Z`; `pg_dump -Fc` → `canonical.dump` (3773 B), sha256 `33122558da36...cd544`; канонический снимок полей `canonical.tsv` (20 строк), sha256 `0c7c1118ee02...85bd` |
| 3. удалить строки | `DELETE ... BETWEEN ...0001 AND ...0005` → `DELETE 5`; API → `15` |
| 4. helm rollback не вернёт | два отката (`helm rollback` и `helm rollback 3`), после обоих — `15` |
| 5. t1 + restore в новую базу | t1 = `09:03:06Z`; `createdb release_board_restore` (исходную не трогаем); `pg_restore --exit-on-error` из canonical.dump; t2 = `09:04:26Z` → **80 с**; `count(*)` → `20` |
| 6. сверка + окончание | `restored.tsv` тем же запросом: sha256 **совпадает** с canonical (`0c7c1118...`), `diff` → `IDENT: 0 различий`, `wc -l` → 20 (count + UUID + все предметные поля); окончание проверки `09:06:02Z` (**176 с** от t1) |
| 7. переключить экземпляр | патч Secret `DB_NAME=release_board_restore` (base64, пароль не трогаем) + рестарт подов → API отдаёт `20` (id ...0001–...0020); исходная база — `15`, её PVC сохранён |

Грабль: `helm rollback` **без индекса** идёт на предыдущий **номер**
ревизии, а не на последнюю успешную — откат ушёл на failed-ревизию 2
(битый тег инцидента A) → rollout завис в ImagePullBackOff; лечится
явным номером `helm rollback <release> 3`. Время удаления строк (t_del)
зафиксировано не было — в runbook вынесено как обязательная метка.

### Почему rollback workload не равен восстановлению базы (ТЗ, строка 388)

Helm хранит манифесты, значения и историю релизов (secret
`sh.helm.release.v1.*`); данные PostgreSQL живут на PVC и в state
релиза не входят. `helm rollback` пересоздаёт/откатывает только
объекты манифестов и не читает том вообще — на стенде после двух
откатов строк осталось `15`. Единственный путь к данным — логический
backup + `pg_restore` в **новую** базу + сверка + переключение;
rollback полезен только чтобы вернуть корректную конфигурацию
workload'ов (и то — на явный номер успешной ревизии).

### Runbook и метрики восстановления (ТЗ, строка 364)

`docs/runbooks/database-recovery.md`: порядок «фиксация → почему
rollback не лечит → backup/checksum → restore в новую базу → сверка
count/UUID/полей → переключение через Secret», у каждой команды —
вопрос, который она закрывает.

| Показатель | Значение |
| --- | --- |
| Целевой RPO | периодичность логического backup: лаборатория — по требованию; прод-рекомендация — ежесуточный `pg_dump` → RPO ≤ 24 ч |
| Целевой RTO | ≤ 30 мин (restore + сверка + переключение) |
| Фактическое время восстановления | 80 с (09:03:06Z → 09:04:26Z) |
| Фактическое время до подтверждения | 176 с (t1 → t3 09:06:02Z) |
| Потеря относительно момента backup | 0 записей (после backup записей не создавалось); до restore фактически потеряно 5 строк из 20 — восстановлены полностью |
| Владелец решения о переключении | владелец проекта (единолчно), только после сверки без расхождений |
| Критерии отказа от восстановления | не сошёлся checksum дампа; ошибка `pg_restore`; любое расхождение count/UUID/полей; не уложились в RTO → отказ, работа на текущей базе |

### Как подтвердить исправление после инцидента (ТЗ, строка 389)

Единый шаблон, отработанный на всех четырёх инцидентах:

1. **Симптом закрыт** — та же команда диагностики, что его показала,
   теперь даёт норму: A — `imageID` = digest, B — `200` из кластера,
   C — `/ready 200`, D — `count(*) = 20`.
2. **Независимая вторая проверка** — другой уровень стека: поды и
   slice (B), EndpointSlice и curl из пода (B), логи и grep секрета
   (C), sha256 + `diff` канонического снимка (D).
3. **Отрицательный контроль** — показать, что лечится именно фикс:
   рестарт без правки конфига не помогает (B, C), rollback не возвращает
   данные (D).
4. **Время и владелец** — метки t0/t1/t2/t3 и решение о переключении
   зафиксированы до, а не после проверки.

### Грабли этапа 8

- k3d: `--registry-create` (не `--registry-name`), `.localhost`-имена
  mirror'ов в incidents не работают, kubeconfig `0.0.0.0` требует
  прокси/`set-cluster`.
- `--type=strategy` → `strategic`; JSON-альтернатива — `op:replace` +
  `op:remove`; после удаления `rollingUpdate` возвращать через `op:add`.
- Селекторы: `-l app.kubernetes.io/instance=` захватывает соседние
  объекты — для EndpointSlice точный ключ `kubernetes.io/service-name`.
- Гонка netpol даёт единичный `000` сразу после старта пода —
  отличать от поломки по ретраям (`--retry-connrefused`).
- `helm rollback` без индекса → предыдущий номер ревизии, включая
  failed; port-forward переживает смерть пода и отвечает `000`.
- env из ConfigMap/Secret фиксируется при старте пода — без рестарта
  патч не виден.

### Очистка лаборатории

```text
k3d cluster delete incidents → Successfully deleted cluster incidents!
  (ноды, сеть, volume, запись cluster/context в kubeconfig удалены самим k3d)
docker ps -a | grep k3d-incidents → 0 контейнеров
kubectl config delete-cluster/delete-context k3d-incidents → not in config (уже удалены k3d)
kubectl config unset users.k3d-incidents → unset
kubectl config get-contexts → k3d-release-board (текущий), k3s-release-board (ВМ, этап 5) — incidents нет
артефакты инцидента D сохранены вне git: ~/.config/release-board/canonical.dump (3773 B),
  canonical.tsv и restored.tsv (1721 B, sha256 идентичны)
```

### Итоги этапа 8

- Четыре инцидента (A–D) воспроизведены, диагностированы и закрыты:
  причины — битая ссылка на образ, рассинхрон probe и EndpointSlice,
  неверный DSN в ConfigMap, удаление строк; для каждого зафиксированы
  гипотеза, наблюдение, команды, причина, фикс и проверка (FLOW.md
  8.1–8.4).
- Backup → restore в новую базу → побайтовая сверка прошли без
  расхождений (20/20, sha256 идентичны), приложение переключено на
  восстановленную базу, исходная копия (15 строк) и PVC сохранены.
- Rollback workload доказательно не равен восстановлению данных;
  runbook `docs/runbooks/database-recovery.md` фиксирует RPO/RTO,
  метрики, владельца и критерии отказа.
- Изменения этапа в репозитории: `docs/runbooks/database-recovery.md`,
  этот раздел отчёта — один PR.

---

## Этап 9. Доработки по замечаниям

Замечания закрыты четырьмя PR и настройками
GitHub; очистка лаборатории выполнена 2026-10-14.

| Замечание | Что сделано | PR |
| --- | --- | --- |
| CI красный из-за Trivy, релиз без скана; неповторяемый `apt-get upgrade` | База `python:3.12.14-slim-trixie@sha256:f77ac9e44…` (CRITICAL 5 → 0), слой `apt-get upgrade` удалён, остаток в `.trivyignore.yaml` (10 CVE, `expiring_at` 2026-11-01/12-01), `release` → `needs: [check, docker, helm]` | #29 `2723173`, #30 `2e0ecc5` |
| Процесс: закрепление действий | Все `uses:` по SHA с комментарием `# v7`, `.github/dependabot.yml` (github-actions, weekly) | #30 `2e0ecc5` |
| Merge-ворота | Ruleset: required checks `check`, `docker`, `helm` (strict); репозитория: только squash (`allow_merge_commit=false`, `allow_rebase_merge=false`) | настройки 2026-10-14 |
| Нет скрипта очистки стендов (ТЗ, стр. 11–12, 15) | `scripts/stand-cleanup.sh`: guard по текущему контексту (только `k3d-release-board`/`k3s-release-board`, чужой → `exit 1`); k3d — целиком, k3s — только неймспейсы проекта | #31 `43b51fe` |
| Нет скрипта запуска VM, битая ссылка | `scripts/start-vm.sh`: зависимости, cloud-образ + SHA-256, overlay 50G, seed.iso, `--check`/`--tmux`, запрос каталога | #32 `a958a0e` |

**Смена базы образа (сноска к этапу 3):** 2026-10-14 база переведена со
`slim-bookworm` на `slim-trixie` (Debian 13, digest-pin), слой
`apt-get upgrade` удалён — на digest-pinned базе он делал сборку
невоспроизводимой. Скан на новой базе: **48 HIGH, 0 CRITICAL** (было 5
CRITICAL); после `.trivyignore.yaml` — `Total: 0`, job `docker` зелёный.
Формат ignore — YAML с `expiring_at`: по дате запись перестаёт
действовать и CI снова упадёт, если проблема не решена.

### Финальная очистка (ТЗ, стр. 15)

Команды выполнялись 2026-10-14; VM поднята новым `scripts/start-vm.sh
--tmux`, неймспейсы и стенд удалены, вывод сохранён.

**k3s (контекст `k3s-release-board`), exit=0:**

```text
[stand-cleanup] контекст: k3s-release-board
ns release-board-helm: не найден — пропуск
namespace "release-board-raw" deleted
[stand-cleanup] ns release-board-raw: удалён
namespace "release-board-k3s" deleted
[stand-cleanup] ns release-board-k3s: удалён
[stand-cleanup] итог: неймспейсы проекта удалены, VM и k3s не тронуты
```

**k3d (контекст `k3d-release-board`), exit=0:**

```text
[stand-cleanup] контекст: k3d-release-board
--- k3d cluster delete release-board
INFO[0000] Deleting cluster 'release-board'
INFO[0003] Deleting cluster network 'k3d-release-board'
WARN[0003] Failed to delete cluster network 'k3d-release-board': ... active endpoints (name:"k3d-release-board-registry.localhost" ...)
INFO[0003] Deleting 1 attached volumes...
INFO[0003] Removing cluster details from default kubeconfig...
INFO[0003] Successfully deleted cluster release-board!
--- k3d registry delete k3d-release-board-registry.localhost
[stand-cleanup] итог: кластер и registry удалены (контекст k3d снимает сам)
```

WARN объясним: k3d удаляет сеть раньше registry, тот ещё держал
endpoint; после удаления registry сеть осталась осиротевшей и снята
вручную: `docker network rm k3d-release-board`.

**Контроль после очистки:** `k3d cluster list` и `k3d registry list`
пусты; `docker ps` — только локальный PostgreSQL и посторонний контейнер
`jackett` (скрипт их не трогает — работает только с двумя именами
стендов); в kubeconfig остался контекст `k3s-release-board`; в кластере —
только системные неймспейсы (`default`, `kube-*`). VM оставлена рабочей
(решение: очищаем стенды, машину не выключаем).

---

## Итоговый технический отчёт

| Пункт | Значение                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --- |-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| URL репозитория без учётных данных | `https://github.com/Slon4ek/release-board` — паролей и токенов в URL нет, доступ ключами/токенами GitHub (§Шапка)                                                                                                                                                                                                                                                                                                                                                                                                           |
| Защита `main` и тариф | Ruleset (Active, `main`): запрет удаления и force-push, обязательный PR, required check **`check`**, **`docker`**, **`helm`**, «ветка обновлена», только squash; одобрение намеренно не требуется (работа в одиночку). Репозиторий публичный — ограничений тарифа на эти настройки нет (§Этап 2, «Защита `main`»)                                                                                                                                                                                                                                     |
| PR: обычное / revert / hotfix / forward-port | обычное: #21–#24, #27 · revert: #12 (`eba9367`) · hotfix: #25 (`2b04e1f`) · forward-port: #26 (`9c58706`); полная таблица — в начале отчёта                                                                                                                                                                                                                                                                                                                                                                                 |
| Команды проверок, коды, SHA, результат | `make lint` → 0 · `make typecheck` → 0 · `make test` → 0 (`72 passed in 0.60s`); каждый PR проходил CI-job `check` (Lint/Typecheck/Test на `postgres:16`); SHA каждого изменения — в таблице срезов (§Шапка), короткий SHA уходит в `/version`                                                                                                                                                                                                                                                                              |
| Версии инструментов, digest, revisions | Python 3.12.15 · Git 2.53.0 · Docker 29.8.2 · k3d 5.9.0 (k3s v1.35.5-k3s1) · kubectl 1.35.9 · Helm 3.20.2 · Trivy 0.75.0 · pytest 9.1.1 (`docs/environment.md`); образ развёрнут по digest `sha256:ab58e992bee6…` (§Этап 7); Helm revisions: стенд — до `11`, лаборатория инцидентов — `1–5`                                                                                                                                                                                                                                |
| Причины четырёх инцидентов и восстановление | **A**: несуществующий тег → `ErrImagePull` → ImagePullBackOff, фикс по digest · **B**: битый readiness → `Ready=False` → в EndpointSlice `ready: false` → нет DNAT → `000` · **C**: неверный `DB_HOST` → `/live 200` при `/ready 503`, пароля в логах нет · **D**: удалено 5 строк из 20, `helm rollback` не вернул. **Восстановление**: `pg_dump` → новая база → 20/20, sha256 идентичны, `diff` пуст, 80 с до конца restore / 176 с до подтверждения; приложение переключено, исходные 15 строк и PVC сохранены (§Этап 8) |

| Вопрос | Ответ |
| --- | --- |
| Commit, branch, tag, remote-tracking branch | **Commit** — неизменяемый снимок истории с SHA. **Branch** — подвижная ссылка на коммит. **Tag** — метка на коммит (аннотированный — отдельный объект, пушится отдельной командой). **`origin/main`** — локальная копия ветки на сервере, обновляется только `fetch` и сама не двигается. На практике: этап 2 (non-fast-forward, reflog), этап 7 (`v1.1.0`, `v1.1.1`) |
| Когда merge, rebase, revert, reset | **rebase** — перенос *неопубликованных* локальных коммитов, линейная история (этап 2, п.3). **merge** — соединение историй; публичный путь проекта — squash через PR. **revert** — публичная отмена обратным коммитом, история не переписывается (PR #12). **reset** — локальный откат указателя; на remote это force-push, запрещённый ruleset'ом. Сравнение состояний и проверок — `docs/runbooks/git-recovery.md` |
| Deployment, ReplicaSet, Pod, Service, EndpointSlice | **Deployment** задаёт шаблон и стратегию, управляет **ReplicaSet**'ами (новый шаблон = новый RS); RS держит **Pod**'ы. **Service** даёт ClusterIP и DNS, **EndpointSlice** — адреса подов по Pod condition `Ready`; kube-proxy программирует DNAT только для `ready: true`. Путь запроса: DNS → ClusterIP → DNAT → Pod. Разрыв цепочки — инцидент B; та же механика в норме — инцидент 4 этапа 4 |
| Readiness vs liveness vs startup | **Startup** — «процесс поднялся» (до успеха остальные пробы ждут). **Readiness** — «могу обрабатывать трафик»: выводит из балансировки, но не перезапускает. **Liveness** — «процесс жив»: рестарт контейнера. Внешние зависимости — только на readiness, иначе петля рестартов. Проект: startup/liveness `/live`, readiness `/ready` (`SELECT 1`); инцидент C — `200` и `503` у одного пода |
| Requests и limits | **Requests** — для планировщика: под встаёт на ноду с заявленным запасом, иначе `Pending`. **Limits** — для работающего контейнера: CPU — throttling, память — OOMKill. Проект: cpu 50m/500m, memory 96Mi/256Mi, класс Burstable (§Этап 4, доказательство 8) |
| Где k3d заканчивается и начинается k3s | **k3d** поднимает k3s нодами-контейнерами в docker; его граница — docker-хост (volume'ы, проброс портов, `k3d cluster delete` удаляет всё — лаборатория этап 8). **k3s** — сам дистрибутив (один бинарник, containerd, sqlite): у нас на VM под systemd, переживает ребут (§Этап 5). Общее — объекты и kubectl; разница — контекст, поэтому первая команда — `kubectl config current-context` |
| Какие части k3s server и agent запускают | Один бинарник, два режима. **Server** совмещает control-plane (apiserver, scheduler, controller-manager), datastore (sqlite через kine) и worker-часть (kubelet, kube-proxy, containerd, flannel, CoreDNS/Traefik/local-path/metrics-server). **Agent** — только worker-часть. Agent-узлов нет, всё на `k3s-vm` без taint (§Этап 5, «Роли k3s server и agent») |
| Какие данные хранит Helm release | Secret `sh.helm.release.v1.<name>.v<N>`: отрендеренные манифесты, **все** значения (values + `--set`, включая чувствительные), история и статусы ревизий. Данных приложения (БД, PVC) там **нет** — см. следующий пункт |
| Почему rollback workload ≠ восстановление базы | Rollback читает только Helm-секрет и переписывает манифесты; PVC с данными PostgreSQL в state релиза не входит. На стенде: два отката — строк осталось `15`. Лечит только backup → restore в новую базу → сверка → переключение (§Этап 8, D) |
| Как подтвердить исправление после инцидента | Шаблон этапа 8: (1) симптом закрыт **той же командой**, что его показала; (2) независимая вторая проверка на другом уровне стека; (3) отрицательный контроль — без фикса не работает (рестарт, rollback); (4) зафиксированы время и владелец решения (§Этап 8, «Как подтвердить исправление после инцидента») |
