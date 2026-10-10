#!/usr/bin/env bash
# Быстрый срез стенда: stand-status.sh k3d|k3s
set -euo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/stand-env.sh" "${1:?usage: stand-status.sh k3d|k3s}"

use_ctx
echo "--- helm"
helm history "$RELEASE" -n "$NS" | tail -5
echo
echo "--- pods"
kubectl -n "$NS" get pods
echo
port_forward "$RELEASE-api" 18080 80
echo "--- api"
printf 'GET /version  -> '; curl -s --max-time 5 http://127.0.0.1:18080/version; echo
printf 'GET /releases -> '; curl -s --max-time 5 http://127.0.0.1:18080/releases; echo
