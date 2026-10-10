#!/usr/bin/env bash
# helm test + последние ревизии: stand-test.sh k3d|k3s
set -uo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPTS/stand-env.sh" "${1:?usage: stand-test.sh k3d|k3s}"

use_ctx
# hook-succeeded удаляет успешный test-под мгновенно, поэтому --logs часто
# отвечает "pod not found" — нас интересует Phase, код возврата глотаем
helm test "$RELEASE" -n "$NS" --logs 2>&1 | grep -E 'Phase:|STATUS:|Error:' || true
echo
helm history "$RELEASE" -n "$NS" | tail -5
