#!/usr/bin/env bash
# Общий модуль для stand-*.sh. Вызывать через: source stand-env.sh k3d|k3s
set -euo pipefail

STAND="${1:?usage: stand-env.sh k3d|k3s}"
case "$STAND" in
  k3d) CTX="k3d-release-board"; NS="release-board-helm"; VALUES="values-k3d.yaml" ;;
  k3s) CTX="k3s-release-board"; NS="release-board-k3s"; VALUES="values-k3s.yaml" ;;
  *) echo "stand-env.sh: ожидается k3d или k3s" >&2; exit 2 ;;
esac

CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../deploy/helm/release-board"
SECRET_DIR="${RELEASE_BOARD_HOME:-$HOME/.config/release-board}"
SECRET_FILE="$SECRET_DIR/db.env"
RELEASE="release-board"

use_ctx() {
  kubectl config use-context "$CTX" >/dev/null
  echo "context: $CTX  (namespace: $NS)"
}

ensure_secret() {
  if [[ ! -f "$SECRET_FILE" ]]; then
    mkdir -p "$SECRET_DIR" && chmod 700 "$SECRET_DIR"
    printf 'DB_NAME=release_board\nDB_USER=release_board\nDB_PASSWORD=%s\n' \
      "$(openssl rand -hex 16)" > "$SECRET_FILE"
    chmod 600 "$SECRET_FILE"
    echo "secret: сгенерирован $SECRET_FILE"
  fi
  # shellcheck disable=SC1090
  source "$SECRET_FILE"
  if kubectl -n "$NS" get secret "$RELEASE-db" >/dev/null 2>&1; then
    echo "secret: release-board-db уже есть в $NS"
  else
    kubectl -n "$NS" create secret generic "$RELEASE-db" \
      --from-literal=DB_NAME="$DB_NAME" \
      --from-literal=DB_USER="$DB_USER" \
      --from-literal=DB_PASSWORD="$DB_PASSWORD" >/dev/null
    echo "secret: release-board-db создан в $NS"
  fi
}

port_forward() {
  local svc="$1" lport="$2" tport="${3:-80}"
  kubectl -n "$NS" port-forward "svc/$svc" "$lport:$tport" >/dev/null 2>&1 &
  PF_PID=$!
  trap 'kill $PF_PID 2>/dev/null || true; wait $PF_PID 2>/dev/null || true' EXIT
  for _ in $(seq 1 15); do
    curl -s -o /dev/null --max-time 1 "http://127.0.0.1:$lport/live" && return 0
    sleep 0.5
  done
  echo "port-forward: $svc:$lport не отвечает" >&2
  return 1
}
