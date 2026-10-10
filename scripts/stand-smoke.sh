#!/usr/bin/env bash
# Smoke стенда: stand-smoke.sh k3d|k3s
set -euo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/stand-env.sh" "${1:?usage: stand-smoke.sh k3d|k3s}"

use_ctx
echo "--- pods,svc,pvc"
kubectl -n "$NS" get pods,svc,pvc
echo
echo "--- api"
port_forward "$RELEASE-api" 18080 80
for path in live releases version; do
  printf 'GET /%-9s -> ' "$path"
  curl -s --max-time 5 "http://127.0.0.1:18080/$path" || echo "(нет ответа)"
  echo
done
