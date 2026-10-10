# Шпаргалка: скрипты стенда (`scripts/stand-*.sh`)

Все команды запускаются из корня проекта. Аргумент — стенд: `k3d` или `k3s`.

## Команды

| Команда | Что делает |
|---|---|
| `scripts/stand-up.sh k3d` | Поднять/обновить стенд: namespace + Secret + `helm upgrade --install --atomic --wait` |
| `scripts/stand-smoke.sh k3d` | Smoke: состав стенда (pods/svc/pvc) + `GET /live`, `/releases`, `/version` |
| `scripts/stand-test.sh k3d` | `helm test --logs` → Phase + последние ревизии `helm history` |
| `scripts/stand-status.sh k3d` | Быстрый срез: helm history, pods, `/version`, UUID записей Release |
| `scripts/stand-env.sh k3d` | Общий модуль (его source'ят остальные скрипты; сам запускать не нужно) |
| `scripts/k8s-load-test.sh` | Нагрузочный тест ТЗ (этап 4, п.7): 30 запросов к `/live` с убийством Pod'а на 10-м. По умолчанию — raw-стенд (`NS=release-board-raw`); переменными `NS`/`SVC` переключается на любой стенд |

## Примеры

```bash
scripts/stand-up.sh k3d          # первый запуск создаст ns, secret, установит chart
scripts/stand-smoke.sh k3d       # проверить, что API отвечает
scripts/stand-test.sh k3s        # прогнать helm test на VM
scripts/stand-status.sh k3s      # что за ревизия/версия сейчас крутится
```

## Как это работает

- **Контекст/стенд.** `k3d` → контекст `k3d-release-board`, ns `release-board-helm`;
  `k3s` → контекст `k3s-release-board`, ns `release-board-k3s`. Chart берётся
  из `deploy/helm/release-board` с нужными values (`values-k3d.yaml` / `values-k3s.yaml`).
- **Secret.** Пароль генерируется один раз (`openssl rand -hex 16`) и хранится в
  `~/.config/release-board/db.env` (chmod 600, **вне git**). Повторные запуски
  переиспользуют файл; если Secret уже есть в кластере — ничего не пересоздаётся.
- **port-forward.** Скрипты сами поднимают forward на локальный порт 18080 и
  убивают его при выходе — руками запускать `kubectl port-forward` не нужно.

## Через make (Makefile)

В этом Makefile `.PHONY` объявлен в строке 3, поэтому:

1. В строку 3 (после `docker-scan`) дописать новые имена:
   `stand-up-k3d stand-up-k3s stand-smoke-k3d stand-smoke-k3s stand-test-k3d stand-test-k3s stand-status-k3d stand-status-k3s`
2. В **конец файла** добавить сами таргеты:

```make
# ── стенды (scripts/stand-*.sh) ──
stand-up-k3d:     ; scripts/stand-up.sh k3d
stand-up-k3s:     ; scripts/stand-up.sh k3s
stand-smoke-k3d:  ; scripts/stand-smoke.sh k3d
stand-smoke-k3s:  ; scripts/stand-smoke.sh k3s
stand-test-k3d:   ; scripts/stand-test.sh k3d
stand-test-k3s:   ; scripts/stand-test.sh k3s
stand-status-k3d: ; scripts/stand-status.sh k3d
stand-status-k3s: ; scripts/stand-status.sh k3s
```

Тогда вместо `scripts/stand-up.sh k3d` — `make stand-up-k3d`.
Плюс в `help` по желанию:

```make
	@echo "  make stand-up-k3d     — поднять/обновить helm-стенд k3d"
	@echo "  make stand-smoke-k3d  — smoke k3d (pods + /live /releases /version)"
	@echo "  make stand-test-k3d   — helm test k3d"
	@echo "  make stand-status-k3d — быстрый срез k3d"
	@echo "  (... то же для k3s)"
```

## Нагрузочный тест (k8s-load-test.sh)

```bash
scripts/k8s-load-test.sh                    # raw-стенд (по умолчанию)
NS=release-board-helm scripts/k8s-load-test.sh   # helm-стенд (см. оговорку ниже)
```

**Оговорка для helm-стенда:** скрипт выбирает жертву по лейблу
`app=<SVC>` (метка raw-манифестов этапа 4). В helm chart лейблы другие
(`app.kubernetes.io/name: release-board` + `component: api`), поэтому
переменная `LABEL` сейчас не параметризована — для helm-стенда либо
добавить в скрипт переменную `LABEL_SELECTOR`, либо править селектор
руками. На этапе 8 (backup/restore) разберёмся.

## Куда класть

Скопировать в `release_board/scripts/`, сделать исполняемыми (`chmod +x`).
