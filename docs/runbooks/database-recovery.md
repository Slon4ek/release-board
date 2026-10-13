# Runbook: восстановление PostgreSQL

Назначение: порядок действий, когда данные в учебной/рабочей базе
потеряны (удалены, испорчены, «пропали после деплоя»). Не заменяет
официальную документацию PostgreSQL, а фиксирует порядок, команды и
критерии, принятые в проекте. У каждой команды указан вопрос, который
она закрывает.

Стек: PostgreSQL 16.15 (StatefulSet Helm-чарта `release-board`),
`pg_dump`/`pg_restore` из официального образа, kubectl, Helm.
Имена подов/неймспейсов подставляются свои.

```bash
NS=release-board-incidents          # вопрос: в каком неймспейсе работает БД?
PG=release-board-postgres-0         # вопрос: какой именно pod — источник и цель?
DB=<имя_потерянной_базы>            # вопрос: какую базу чиним?
```

## 0. Правила безопасности (прочитать до любых команд)

1. **Не восстанавливай дамп поверх единственной копии базы.** Цель
   restore — новая пустая база (или новый неймспейс). Исходная база и
   её PVC не трогаются до полной проверки.
2. **Не пиши в потерянную базу.** Каждая запись после инцидента
   сдвигает окно потери и ломает сверку.
3. **Зафиксируй время инцидента (t_del)** сразу: `date -u +%FT%TZ` —
   иначе потерю относительно backup посчитать нельзя.
4. Секреты (`DB_PASSWORD`) не попадают в логи, отчёты и runbook —
   берутся из окружения пода (`$POSTGRES_PASSWORD`), не из вывода.

## 1. Сводная таблица: симптом → первая секция

| Симптом | Секция |
| --- | --- |
| Строки пропали / удалены, REST отдаёт меньше записей | 2. Фиксация → 4. Backup |
| «Надо откатить» — идея починить `helm rollback` | 3. Почему rollback не лечит |
| Backup есть, данные нужны снова | 4. Restore в новую базу |
| Restore прошёл, но «а точно всё вернулось?» | 5. Сверка |
| Данные восстановлены, приложение смотрит в старую базу | 6. Переключение |

## 2. Фиксация инцидента — «что и когда случилось?»

```bash
date -u +%FT%TZ
# вопрос: сколько времени прошло с backup (это и есть RPO-риск)?

kubectl -n "$NS" exec "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB" -Atc \
  "SELECT count(*) FROM releases"'
# вопрос: сколько строк осталось — начальная точка потери

kubectl -n "$NS" exec "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB" -Atc \
  "SELECT max(created_at) FROM releases"'
# вопрос: есть ли записи НЕПОСРЕДСТВЕННО перед инцидентом —
# подтверждает, что удалены были именно (недавние) данные, а не пустая таблица
```

Дальше — ничего не записывать в эту базу до конца сверки.

## 3. Почему helm rollback НЕ вернёт строки

Helm хранит манифесты, историю релизов и значения (secret-объект
`sh.helm.release.v1.*`); данные PostgreSQL живут на PVC и в state
релиза не входят. Поэтому `helm rollback` пересоздаёт workload'ы, а
содержимое тома оставляет как есть — проверено на стенде: два
отката, строк осталось столько же.

```bash
helm history <release> -n "$NS"
# вопрос: какие ревизии существуют и какая из них последняя deployed?
# НЕ брать failed-ревизии: rollback по умолчанию идёт на предыдущий
# НОМЕР ревизии, а не на последнюю успешную (грабль этапа 8:
# откат на failed-ревизию вернул битый тег → ImagePullBackOff)

helm rollback <release> <номер_последней_deployed> -n "$NS"
kubectl -n "$NS" rollout status deploy/<release>-api --timeout=120s
# вопрос: откат прошёл успешно — и данные всё равно не вернулись?
# Это ожидаемо: rollback ≠ восстановление базы. Дальше — только backup.
```

## 4. Backup и restore в НОВУЮ базу

### 4.1. Найти и проверить backup

```bash
sha256sum ~/.config/release-board/canonical.dump
# вопрос: сходится ли checksum с тем, что записан на момент backup?
# Не сходится — restore не начинать (см. раздел 7, критерии отказа)
```

Формат — `pg_dump -Fc` (custom): сжатый, переносимый, грузится
только `pg_restore`.

```bash
kubectl -n "$NS" exec "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -Fc "$DB" -f /tmp/canonical.dump'
kubectl -n "$NS" exec "$PG" -- cat /tmp/canonical.dump > ~/.config/release-board/canonical.dump
sha256sum ~/.config/release-board/canonical.dump
# вопрос: снят ли актуальный backup и зафиксирован ли его checksum?
# (для backup ПЕРЕД инцидентом этот шаг уже выполнен — идём к restore)
```

### 4.2. Restore в пустую базу

```bash
date -u +%FT%TZ
# вопрос: t1 — когда начали восстановление (считаем RTO)?

kubectl -n "$NS" exec "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" <новая_пустая_база>'
# вопрос: база-цель создана отдельно, исходная не тронута? (правило 0.1)

kubectl -n "$NS" exec -i "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" \
  -d <новая_пустая_база> --no-owner --exit-on-error' \
  < ~/.config/release-board/canonical.dump
# вопрос: `--exit-on-error` не выдал ошибок — схема и данные легли целиком?
# (тихая ошибка без него = «восстановилось», но неполно)

date -u +%FT%TZ
# вопрос: t2 — restore завершён, сколько секунд занял?
```

## 5. Сверка с каноническим экспортом

Снимок всех предметных полей тем же запросом, что и до инцидента:

```bash
kubectl -n "$NS" exec -i "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" \
  -d <новая_пустая_база> -At -F ","' \
  > /tmp/restored.tsv <<'SQL'
SELECT id, service, version, environment, status, created_at FROM releases ORDER BY id;
SQL

wc -l /tmp/restored.tsv                          # вопрос: count совпал?
diff ~/.config/release-board/canonical.tsv /tmp/restored.tsv \
  && echo "IDENT: 0 различий"                     # вопрос: UUID и ВСЕ поля идентичны?
sha256sum ~/.config/release-board/canonical.tsv /tmp/restored.tsv
# вопрос: контрольные суммы равны — сверка побайтовая, а не «на глаз»
```

Сверка обязательна по трём осям: **количество строк**, **набор UUID**,
**значения всех предметных полей**. Любое расхождение — не переключать
приложение (раздел 7).

```bash
date -u +%FT%TZ
# вопрос: t3 — восстановление подтверждено; RTO = t3 − t1
```

## 6. Переключение приложения на восстановленную базу

`DB_NAME` пода берётся из Secret (`secretKeyRef`, deployment.yaml),
`DB_HOST`/`DB_PORT` — из ConfigMap; env фиксируется при старте пода,
поэтому обязателен рестарт.

```bash
kubectl -n "$NS" patch secret <secret_базы> --type merge \
  -p "{\"data\":{\"DB_NAME\":\"$(printf '<новая_пустая_база>' | base64 -w0)\"}}"
# вопрос: переключено только имя базы, пароль не затронут?

kubectl -n "$NS" delete pod -l app.kubernetes.io/component=api
kubectl -n "$NS" wait --for=condition=Ready pod \
  -l app.kubernetes.io/component=api --timeout=120s
# вопрос: поды встали Ready — readiness проходит на новой базе?

# свежий port-forward (старый переживает смерть пода и врёт 000):
pkill -f 'port-forward' || true; sleep 1
kubectl -n "$NS" port-forward svc/<release>-api 8080:80 &
sleep 3
curl -s http://localhost:8080/releases | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
# вопрос: API отдаёт восстановленное количество записей?

kubectl -n "$NS" exec "$PG" -- \
  sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB" -Atc \
  "SELECT count(*) FROM releases"'
# вопрос: ИСХОДНАЯ база по-прежнему на месте — единственная копия
# сохранена (правило 0.1), PVC не удалён и не переиспользован
```

## 7. Метрики, владелец и критерии отказа (заполнить в отчёте)

| Показатель | Как считать | Лаборатория (этап 8) |
| --- | --- | --- |
| Целевой RPO | периодичность логического backup | по требованию в лаборатории; на проде — ежесуточный `pg_dump` → RPO ≤ 24 ч |
| Целевой RTO | бюджет времени на restore + сверку | ≤ 30 мин |
| Фактическое время восстановления | t2 − t1 | 80 с (09:03:06Z → 09:04:26Z) |
| Фактическое время до подтверждения | t3 − t1 | 176 с (… → 09:06:02Z) |
| Потеря относительно момента backup | записи ПОСЛЕ backup, не попавшие в дамп | 0 записей (записей после backup не создавалось) |
| Фактическая потеря до restore | удалённые строки | 5 из 20, восстановлены полностью |

- **Владелец решения о переключении:** владелец проекта (единолчно).
  Переключение приложения — только после раздела 5 без расхождений.
- **Критерии отказа от восстановления** (restore признаётся неудачным,
  работа продолжается на текущей базе):
  - не сходится checksum дампа;
  - `pg_restore` выдал ошибку (`--exit-on-error`);
  - сверка count/UUID/полей даёт хоть одно расхождение;
  - восстановление с проверкой не уложилось в целевой RTO.
- **После переключения:** исходную базу и PVC сохранить до тех пор,
  пока владелец не подтвердил работоспособность восстановленных
  данных (минимум — один полный цикл проверок приложения).
