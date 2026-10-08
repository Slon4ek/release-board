# Runbook: диагностика Kubernetes

Назначение: порядок проверки, когда «что-то не работает в кластере» —
сервис не отвечает, Pod не встаёт, данные пропали. Не заменяет
документацию k8s, а фиксирует порядок действий и команд, принятых в
проекте. У каждой команды указан вопрос, который она закрывает.

Стек: k3d (k3s v1.35.5-k3s1), kubectl v1.35.9, контекст
`k3d-release-board`, неймспейс `release-board-raw`.

Принцип: идём сверху вниз — «не тот кластер? → что сказал кластер? →
какой объект сломан → почему именно он → что говорит приложение → видит
ли Service поды → резолвятся ли имена → доходит ли трафик → хватает ли
ресурсов → живы ли тома». Сначала смотри events, потом лезь в детали:
кластер сам чаще всего называет причину.

## 1. Сводная таблица: симптом → первая секция

| Симптом | Секция |
| --- | --- |
| «Всё пропало, объектов нет» / команды ведут себя странно | 2. Context |
| Pod `Pending` / `ImagePullBackOff` / `CrashLoopBackOff` / `OOMKilled` | 3. Events → 5. Describe |
| Rollout завис, реплики не обновляются | 4. Workload → 5. Describe |
| Приложение отвечает 503 / «зависло» | 6. Logs → 7. Endpoints |
| `curl http://service/...` не проходит из пода | 8. DNS → 9. Сеть |
| OOMKill, таймауты под нагрузкой, медленные ответы | 10. Ресурсы |
| Под не встаёт после переноса на другую ноду, БД пуста | 11. Storage |

## 2. Context — «я вообще с тем кластером разговариваю?»

Самая частая причина «всё пропало»: другой контекст, выключенный
кластер, забытый namespace.

```bash
kubectl config current-context
# вопрос: контекст = k3d-release-board? Если нет — не трогать кластер,
# пока не выяснено, куда ты подключился

kubectl cluster-info
# вопрос: отвечает ли control-plane (выключен k3d? — docker restart
# k3d-release-board-server-0 вернёт API после выключения хоста)

kubectl get nodes
# вопрос: все ли ноды Ready (1 server + 2 agent)? NotReady = проблема
# уровня узла/контейнера, дальше в неймспейс не лезем
```

## 3. Events — «что кластер сам сказал о проблеме?»

Первый взгляд на любой инцидент: события контроллеров — они же
регистрируют причины `FailedScheduling`, `FailedMount`,
`Unhealthy` (пробы), `Killing`.

```bash
kubectl get events -n release-board-raw --sort-by=.lastTimestamp
# вопрос: какие события произошли в неймспейсе и в каком порядке;
# читаем снизу (последние). Строки Warning — кандидаты в причину

kubectl get events -A --sort-by=.lastTimestamp | tail -20
# вопрос: событие не в нашем неймспейсе (проблема в CoreDNS или на
# ноде)?

kubectl describe node k3d-release-board-agent-0 | tail -40
# вопрос: были ли события на самой ноде (исчерпаны ресурсы,
# диск, pressure)?
```

**Ограничение:** события живут ~1 час — для старых инцидентов их уже
не будет, остаётся `describe` (секция 5) и логи (секция 6).

## 4. Workload — «где именно сломано?»

Общая картина состояния наших объектов.

```bash
kubectl get deploy,statefulset,svc,pdb,networkpolicy,pvc -n release-board-raw
# вопрос: какие объекты существуют и в каком статусе;
# deploy: REPLICAS READY? sts: READY? pvc: Bound?

kubectl get pod -n release-board-raw -o wide
# вопрос: в каком статусе каждый Pod (Running/Pending/ImagePull/
# CrashLoop/OOMKilled), на какой ноде, сколько рестартов (RESTARTS)?

kubectl rollout status deploy/release-board-api -n release-board-raw --timeout=120s
# вопрос: завершается ли обновление Deployment в ограниченное время;
# «дожидание не завершилось» = новые поды не проходят пробы или не встают

kubectl scale deployment/release-board-api -n release-board-raw --replicas=2
# вопрос: готов ли Deployment вернуть нужное число реплик, если их
# удалили руками (ручное восстановление, не штатный откат)
```

## 5. Describe — «почему именно этот Pod такой?»

`describe` = конфигурация + история состояний + события объекта.
Читать хвост (Events) и блок Last State.

```bash
POD=имя-пода   # подставить своё имя: kubectl get pod -n release-board-raw

kubectl describe pod -n release-board-raw "$POD" | tail -30
# вопрос: что в Events (Reason/Message) и в Last State (Exit Code)?

kubectl describe pod -n release-board-raw "$POD" | sed -n '/Containers/,/Events/p'
# вопрос: какие пробы падают (Last Probe Result), какая причина
# неготовности прямо сейчас?
```

**Как читать код выхода (Last State → Exit Code):**

| Код | Значение | Что делать |
| --- | --- | --- |
| `137` | SIGKILL — почти всегда OOMKill (лимит памяти) | секция 10, поднять `limits.memory` |
| `143` | SIGTERM — штатная остановка (проба/грейс) | норма, если не частые |
| `1` | приложение само упало | секция 6, логи приложения |
| `127` | команда не найдена (битый CMD в Dockerfile) | править образ |

## 6. Logs — «что приложение само говорит?»

```bash
POD=имя-пода   # подставить своё имя: kubectl get pod -n release-board-raw

kubectl logs -n release-board-raw "$POD" --tail=100
# вопрос: что пишет приложение сейчас (traceback, ошибки БД в
# /ready, таймауты)

kubectl logs -n release-board-raw "$POD" --previous --tail=50
# вопрос: почему умер ПРЕДЫДУЩИЙ контейнер (после рестарта основной
# лог уже новый, история — в --previous)

kubectl logs -n release-board-raw deploy/release-board-api --tail=50
# вопрос: что происходит на одной из реплик, не зная имени Pod
```

Если приложение молчит — проблема скорее в сетевом слое или пробы
давят: секции 7–9.

## 7. Endpoints (EndpointSlice) — «видит ли Service свои Pod'ы?»

Классика: сервис создан, поды бегают, а `curl` по имени сервиса не
проходит — почти всегда не совпали `selector` Service и метки Pod'ов.

```bash
kubectl get endpointslice -n release-board-raw \
  -l kubernetes.io/service-name=release-board-api
# вопрос: есть ли адреса (колонка ENDPOINTS) у сервиса; пусто =
# selector Service не совпал с метками Pod'ов

kubectl get endpointslice -n release-board-raw \
  -l kubernetes.io/service-name=release-board-api \
  -o jsonpath='{.items[0].endpoints[*].conditions.ready}{"\n"}'
# вопрос: готовы ли адреса (true/false); неготовый Pod остаётся в
# slice с ready=false — kube-proxy трафик на него не программирует

kubectl get endpointslice -n release-board-raw \
  -l kubernetes.io/service-name=release-board-api -o yaml | grep -A6 'endpoints:'
# вопрос: связка «адрес + conditions у каждой записи» (ready,
# terminating) — кто именно сейчас в списке и в каком состоянии
```

**Ограничение:** `kubectl get endpoints` (v1) в kubectl 1.35 —
deprecated, в скриптах и отчётах используем только EndpointSlice.

## 8. DNS — «разрешаются ли имена внутри кластера?»

Если имя не резолвится — не проверяй порты и политики, всё упрётся в
CoreDNS.

```bash
kubectl run dns-check --rm -i --restart=Never -n release-board-raw \
  --image=busybox:1.37.0 -- nslookup release-board-api
# вопрос: отдаёт ли CoreDNS ClusterIP сервиса (имя из своего
# неймспейса)

kubectl run dns-check-fqdn --rm -i --restart=Never -n release-board-raw \
  --image=busybox:1.37.0 -- nslookup postgres.release-board-raw.svc.cluster.local
# вопрос: работает ли полное FQDN-имя — как его видит приложение;
# короткое имя ищется через search-домены неймспейса

kubectl run dns-check-base --rm -i --restart=Never -n release-board-raw \
  --image=busybox:1.37.0 -- nslookup kubernetes.default
# вопрос: работает ли DNS вообще (базовый сервис API); если падает и
# это — виноваты CoreDNS/его поды (вернуться в секцию 3)
```

**Ограничение:** `kubectl run --rm -i` создаёт одноразовый Pod и ждёт
вывод; образ `busybox:1.37.0` уже на нодах (наш init-контейнер),
повторный pull не нужен.

## 9. Сеть — «доходит ли трафик?»

Последовательность: DNS резолвится → проверяем соединение → если не
проходит — смотрим политики.

```bash
kubectl run net-check --rm -i --restart=Never -n release-board-raw \
  --image=curlimages/curl:8.9.1 -- \
  curl -sS -m 3 http://release-board-api/live
# вопрос: доходит ли HTTP-запрос из ПОДА через ClusterIP Service;
# port-forward здесь не годится — он прибит к одному Pod'у и
# балансировку не проверяет

kubectl run net-denied --rm -i --restart=Never -n default \
  --image=busybox:1.37.0 -- \
  wget -qO- -T 3 http://release-board-api.release-board-raw.svc.cluster.local/live
# вопрос: режет ли NetworkPolicy чужой трафик (ожидаем отказ;
# k3s применяет iptables REJECT — «Connection refused», а не таймаут)

kubectl get networkpolicy -n release-board-raw
# вопрос: какие политики вообще действуют; если нужного разрешения
# нет — разобраться с default-deny-ingress, не отключая его «просто
# так»
```

## 10. Ресурсы — «хватает ли CPU/памяти?»

```bash
kubectl top pod -n release-board-raw
# вопрос: не сидит ли Pod у лимита (CPU у limit = дрослинг, RSS у
# limits.memory = близко к OOMKill/Exit Code 137 из секции 5)

kubectl top node
# вопрос: хватает ли ресурсов ноде (иначе Pending-под не запланируется
# ни на одной)

kubectl get pod -n release-board-raw \
  -o jsonpath='{range .items[*]}{.metadata.name}{"  req="}{.spec.containers[0].resources.requests}{"  lim="}{.spec.containers[0].resources.limits}{"\n"}{end}'
# вопрос: что ЗАЯВЛЕНО в спеке — единственный источник про квоты,
# если metrics-server недоступен
```

**Ограничение:** `kubectl top` требует metrics-server (в k3s входит по
умолчанию). Ответ `metrics not available` — используйте jsonpath выше.

## 11. Storage — «живы ли тома и данные?»

```bash
kubectl get pvc -n release-board-raw
# вопрос: PVC в Bound? Pending = никто не взял том (не та нода,
# нет storage-class)

kubectl get pod postgres-0 -n release-board-raw \
  -o jsonpath='{range .spec.volumes[*]}{.name}{": "}{.persistentVolumeClaim.claimName}{"\n"}{end}'
# вопрос: смонтирован ли нужный том (pg-data-postgres-0) в под

kubectl exec -n release-board-raw postgres-0 -- df -h /var/lib/postgresql/data
# вопрос: не кончилось ли место на томе (Use% у 100% = рост данных)

kubectl exec -n release-board-raw postgres-0 -- \
  psql -U release_board -d release_board -c "select count(*) from pg_stat_activity;"
# вопрос: живёт ли сама БД внутри тома (базовая доступность)

kubectl get pv
# вопрос: к каким нодам привязаны тома; local-path привязан к ноде:
# после переезда Pod'а на другую ноду он останется Pending, пока не
# вернётся «свой» узел — свойство стенда, не поломка данных
```

## 12. Порядок в одном предложении

Context → Events → Workload → Describe → Logs → Endpoints → DNS →
Сеть → Ресурсы → Storage: на каждом шаге команда отвечает на один
вопрос, и только после ответа переходим к следующему. Не начинай с
`delete pod` — сначала зафиксируй причину (events/describe/логи),
иначе след инцидента исчезнет вместе с подом.
