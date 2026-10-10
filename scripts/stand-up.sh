#!/usr/bin/env bash
# Поднять/обновить helm-стенд: stand-up.sh k3d|k3s
set -euo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/stand-env.sh" "${1:?usage: stand-up.sh k3d|k3s}"

use_ctx
kubectl get namespace "$NS" >/dev/null 2>&1 || {
  kubectl create namespace "$NS" >/dev/null
  echo "namespace: $NS создан"
}
ensure_secret

helm upgrade --install "$RELEASE" "$CHART_DIR" \
  --namespace "$NS" \
  --values "$CHART_DIR/$VALUES" \
  --atomic --wait --timeout 3m
echo
helm history "$RELEASE" -n "$NS" | tail -3
