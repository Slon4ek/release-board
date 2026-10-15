#!/usr/bin/env bash
# scripts/stand-cleanup.sh — очистка стендов
# Действует по ТЕКУЩЕМУ контексту kubectl:
#   k3d-release-board → k3d-стенд целиком (кластер + registry);
#   k3s-release-board → только неймспейсы проекта, VM НЕ трогаем;
#   любой другой или пустой контекст → отказ (exit 1).
# Всё пишется в stdout — этот вывод и вставляем в отчёт.
set -euo pipefail

K3D_CLUSTER="release-board"
K3D_REGISTRY="k3d-release-board-registry.localhost"
K3S_NAMESPACES=(release-board-helm release-board-raw release-board-k3s)

current="$(kubectl config current-context)"

case "$current" in
  k3d-release-board)
    echo "[stand-cleanup] контекст: $current"
    echo "--- k3d cluster delete $K3D_CLUSTER"
    k3d cluster delete "$K3D_CLUSTER"
    echo "--- k3d registry delete $K3D_REGISTRY"
    k3d registry delete "$K3D_REGISTRY"
    echo "[stand-cleanup] итог: кластер и registry удалены (контекст k3d снимает сам)"
    ;;

  k3s-release-board)
    echo "[stand-cleanup] контекст: $current"
    if ! kubectl get --raw=/readyz >/dev/null 2>&1; then
      echo "[stand-cleanup] ОШИБКА: API k3s недоступен — VM не запущена" >&2
      echo "[stand-cleanup] запусти VM (scripts/start-vm.sh) и повтори" >&2
      exit 1
    fi
    for ns in "${K3S_NAMESPACES[@]}"; do
      if kubectl get namespace "$ns" >/dev/null 2>&1; then
        kubectl delete namespace "$ns" --wait=true
        echo "[stand-cleanup] ns $ns: удалён"
      else
        echo "[stand-cleanup] ns $ns: не найден — пропуск"
      fi
    done
    echo "[stand-cleanup] итог: неймспейсы проекта удалены, VM и k3s не тронуты"
    ;;

  *)
    echo "[stand-cleanup] ОШИБКА: чужой или пустой контекст: '${current}'" >&2
    echo "[stand-cleanup] разрешены только: k3d-release-board, k3s-release-board" >&2
    echo "[stand-cleanup] переключение вручную: kubectl config use-context <name>" >&2
    exit 1
    ;;
esac