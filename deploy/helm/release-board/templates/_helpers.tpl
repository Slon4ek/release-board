{{/*
Имя chart'а — база для всех имён.
*/}}
{{- define "release-board.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Полное имя release — база имен объектов (Deployment, Service, PVC...).
Имена читаются как <release>-api, <release>-postgres...
*/}}
{{- define "release-board.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Общие лейблы всех объектов chart'а.
*/}}
{{- define "release-board.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ include "release-board.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Лейблы-селекторы: ДОЛЖНЫ совпадать между контроллером и его Service.
Сюда входят только name + instance — менять их нельзя, это «адрес» Pod'а.
Компонент (api/postgres) добавляется точечно в шаблонах.
*/}}
{{- define "release-board.selectorLabels" -}}
app.kubernetes.io/name: {{ include "release-board.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
