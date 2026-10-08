#!/usr/bin/env bash
# scripts/k8s-load-test.sh — доказательство ТЗ по этапу 4, п.7:
# 30 запросов к ClusterIP Service с интервалом 1 c, curl --max-time 2
# --retry 0; один из Pod'ов API удаляется после 10-го запроса;
# при удалении ошибок клиента быть не должно (каждый FAIL = ошибка).
# Перед отсчётом — прогрев: первый запрос свежесозданного пода-клиента
# стабильно получал connection refused (гонка старта), фиксируем в отчёте.
set -euo pipefail

NS="${NS:-release-board-raw}"
SVC="${SVC:-release-board-api}"
IMG="${IMG:-curlimages/curl:8.9.1}"
TOTAL="${TOTAL:-30}"
KILL_AFTER="${KILL_AFTER:-10}"

cleanup() { kubectl delete pod -n "$NS" api-load --ignore-not-found >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "контекст: $(kubectl config current-context)"

wait_for() {  # $1 = grep-паттерн в логе api-load; следит за фазой пода
  while true; do
    if kubectl logs -n "$NS" api-load 2>/dev/null | grep -q "$1"; then return 0; fi
    phase=$(kubectl get pod -n "$NS" api-load -o jsonpath='{.status.phase}' 2>/dev/null || echo Gone)
    case "$phase" in
      Succeeded|Failed) echo "api-load в фазе $phase, но '$1' не найден"; return 1 ;;
    esac
    sleep 1
  done
}

# ── под-клиент: прогрев → отсчёт из 30 запросов → DONE ──
kubectl run api-load -n "$NS" --restart=Never --image="$IMG" --command -- sh -c "
echo '--- прогрев соединения:'
ok=0
for a in 1 2 3; do
  c=\$(curl -sS --max-time 2 --retry 0 -o /dev/null -w '%{http_code}' http://$SVC/live 2>/dev/null)
  if [ \"\$c\" = 200 ]; then echo \"warmup ok (попытка \$a)\"; ok=1; break; fi
  echo \"warmup попытка \$a: code=\$c\"
  sleep 1
done
[ \"\$ok\" = 1 ] || { echo 'warmup не прошёл — сервис недоступен'; exit 2; }
for i in \$(seq 1 $TOTAL); do
  t=\$(date +%H:%M:%S)
  code=\$(curl -sS --max-time 2 --retry 0 -o /dev/null -w '%{http_code}' http://$SVC/live)
  rc=\$?
  [ \$rc -ne 0 ] && code=\"FAIL(rc=\$rc,\$(date +%H:%M:%S))\"
  echo \"\$i \$t \$code\"
  sleep 1
done
echo DONE"

VICTIM=$(kubectl get pod -n "$NS" -l app="$SVC" \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[0].metadata.name}')
echo "→ после $KILL_AFTER-го запроса удаляем: $VICTIM"
wait_for "^$KILL_AFTER " || exit 1
kubectl delete pod -n "$NS" "$VICTIM"

wait_for '^DONE' || exit 1
kubectl rollout status deployment/"$SVC" -n "$NS" --timeout=120s

kubectl logs -n "$NS" api-load > /tmp/api-load.log
echo "── итог ──"
echo "успехов (200): $(grep -c ' 200$' /tmp/api-load.log || true)"
echo "ошибок (FAIL): $(grep -c 'FAIL' /tmp/api-load.log || true)"
echo "DONE:          $(grep -c '^DONE' /tmp/api-load.log || true)"
echo "лог: /tmp/api-load.log"