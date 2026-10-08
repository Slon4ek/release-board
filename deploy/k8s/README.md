# Манифесты Kubernetes

Базовый набор объектов (`base/`) для стенда k3d `k3d-release-board`,
неймспейс `release-board-raw`. Манифесты рукописные, с построчными
комментариями «что и зачем»; Helm-шаблоны живут отдельно в
`deploy/helm/release-board/` (этап 5) и здесь не используются.

## Состав

| Файл | Объекты | Порядок применения |
| --- | --- | --- |
| `namespace.yaml` | Namespace `release-board-raw` | 1 |
| `configmap.yaml` | ConfigMap `release-board-config` | 2 |
| `secret.example.yaml` | шаблон Secret (коммитится, не применяется) | — |
| `postgres.yaml` | Service + StatefulSet PostgreSQL; PVC создаётся из `volumeClaimTemplates` | 3 |
| `serviceaccount.yaml` | ServiceAccount `release-board-api` без токена | 4 |
| `api.yaml` | Deployment (2 реплики, образ по digest локального registry) + ClusterIP Service | 5 |
| `pdb.yaml` | PodDisruptionBudget `minAvailable: 1` | 6 |
| `networkpolicy.yaml` | default-deny-ingress + allow-api-from-raw + allow-postgres-from-api | 6 |

`secret.yaml` в Git не входит (`.gitignore`). Реальный Secret создаётся
локально из шаблона:

```bash
kubectl create secret generic release-board-db \
  --from-literal=DB_USER=release_board \
  --from-literal=DB_PASSWORD='<пароль>' \
  --from-literal=DB_NAME=release_board \
  --dry-run=client -o yaml > deploy/k8s/base/secret.yaml
```

## Применение

Кластер создаётся из декларативного файла (один `server`, два `agent`,
локальный registry):

```bash
k3d cluster create --config deploy/k3d/cluster.yaml
```

Дальше — строго в порядке таблицы:

```bash
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl apply -f deploy/k8s/base/configmap.yaml -f deploy/k8s/base/secret.yaml
kubectl apply -f deploy/k8s/base/postgres.yaml
kubectl apply -f deploy/k8s/base/serviceaccount.yaml
kubectl apply -f deploy/k8s/base/api.yaml
kubectl apply -f deploy/k8s/base/pdb.yaml -f deploy/k8s/base/networkpolicy.yaml
```

`kubectl apply -f deploy/k8s/base/` одним махом применять нельзя:
`kubectl` обрабатывает файлы каталога в алфавитном порядке, и
`api.yaml` попытается создаться раньше `namespace.yaml`.

Каждый файл проходит один цикл проверки перед коммитом:

```text
kubeconform -strict -summary -kubernetes-version 1.35.5 <файл>
→ kubectl apply --dry-run=client -f <файл>
→ kubectl apply -f <файл>
→ kubectl get / rollout status
```

## Проверка после применения

```bash
kubectl get nodes,ns,pod,svc -n release-board-raw
kubectl rollout status deployment/release-board-api -n release-board-raw --timeout=120s
kubectl port-forward -n release-board-raw svc/release-board-api 8080:80
curl localhost:8080/ready
```

## Связанные документы

- `scripts/k8s-load-test.sh` — нагрузочный тест из отдельного Pod
  через ClusterIP (п. 7 доказательств этапа 4).
- `docs/runbooks/kubernetes-diagnostics.md` — порядок диагностики
  неполадок: context → events → workload → describe → logs →
  endpoints → DNS → сеть → ресурсы → storage.
- `docs/report.md`, раздел «Этап 4» — как проверялось и что
  подтверждено (восемь доказательств ТЗ).
- `docs/environment.md` — версии инструментов стенда.
