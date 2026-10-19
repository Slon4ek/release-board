#!/usr/bin/env bash
# E2E живого стенда: API → outbox → relay → Kafka → notifier → processed_events
# + негативная ветка: кривое сообщение → DLQ. Запуск: scripts/e2e-kafka.sh
set -euo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPTS/.."

DB_USER="${DB_USER:-slon4ek}"
DB_NAME="${DB_NAME:-release_board}"
set -a
# shellcheck disable=SC1091
source .env
set +a

psql_t() {
  docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc "$1"
}

fail() {
  echo "FAIL: $1"
  exit 1
}

echo "--- стенд"
for s in postgres kafka app relay notifier; do
  running="$(docker compose ps --format '{{.Service}}' --status running 2>/dev/null | grep -x "$s" || true)"
  [ -n "$running" ] || fail "сервис '$s' не запущен — make compose-up (и убери хостовые uvicorn/relay/notifier, если крутятся)"
done
echo "ok: все сервисы running"
printf 'GET /live     -> %s\n' "$(curl -s --max-time 5 http://localhost:8000/live || echo '(нет ответа)')"

echo "--- позитив: релиз сквозь конвейер"
version="1.0.$(date +%s)"
resp="$(curl -s --max-time 5 -X POST http://localhost:8000/releases \
  -H 'Content-Type: application/json' \
  -d "{\"service\":\"e2e\",\"version\":\"$version\",\"environment\":\"stage\"}")"
id="$(printf '%s' "$resp" | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])' 2>/dev/null || true)"
[ -n "$id" ] || fail "POST /releases не вернул id: $resp"
echo "POST /releases -> id=$id version=$version"

deadline=$((SECONDS + 20))
done_ok=""
while [ "$SECONDS" -lt "$deadline" ]; do
  got="$(psql_t "SELECT count(*) FROM outbox_events o JOIN processed_events p ON p.event_id = o.id WHERE o.aggregate_id = '$id' AND o.published_at IS NOT NULL")"
  if [ "$got" = "1" ]; then
    done_ok="1"
    break
  fi
  sleep 0.5
done
[ -n "$done_ok" ] || fail "событие не прошло конвейер за 20с (outbox → published_at → processed)"
echo "ok: outbox -> relay (published_at) -> notifier (processed_events)"

notifier_log="$(docker compose logs --since 2m notifier 2>/dev/null || true)"
case "$notifier_log" in
  *"created release e2e $version"*) echo "ok: NOTIFY в логах notifier" ;;
  *) fail "NOTIFY не найден в логах notifier" ;;
esac

bad_lag="$(docker compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group notifier --describe 2>/dev/null | awk 'NR>1 && $6 ~ /^[0-9]+$/ && $6 != 0' | wc -l)"
[ "$bad_lag" -eq 0 ] || fail "у группы notifier есть ненулевой LAG"
echo "ok: LAG=0 у группы notifier"

echo "--- негатив: кривое сообщение -> DLQ"
printf '{"hello": 999}\n' | docker compose exec -i -T kafka kafka-console-producer \
  --bootstrap-server localhost:9092 --topic release.events.v1 >/dev/null

dlq="$(docker compose exec -T kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 --topic release.events.dlq --from-beginning --timeout-ms 5000 2>/dev/null || true)"
case "$dlq" in
  *'"hello":999'*|*'"hello": 999'*) echo "ok: кривое сообщение в DLQ (original/error/failed_at)" ;;
  *) fail "сообщение не появилось в DLQ (диагностика: docker compose logs --since 5m notifier | grep 'invalid event')" ;;
esac

echo "E2E OK: весь конвейер жив (API → outbox → relay → Kafka → notifier + DLQ)"
