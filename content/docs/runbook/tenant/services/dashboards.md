---
title: "Dashboards"
weight: 6
---

# Dashboards {{< status-badge "active" "Available" >}}

## What you get

A **Grafana organisation of your own**, with your logs already wired in
([ADR-0024](/docs/architecture/decisions/0024-dashboards/)). Your login is an **Editor** there, and
a member of no other organisation. You build folders and dashboards. The platform owns the data
sources.

| Data source UID | Reads | |
|---|---|---|
| `deevnet-logs-workloads` | `(index, 0)`, your workloads' logs | |
| `deevnet-logs-platform` | `(index, 1)`, what the platform says about your tenant | |
| `deevnet-logs-devices` | `(index, 2)`, your devices' logs from MQTT | the default |

Each one reads with your tenant's own log read token, so it sees exactly what your token sees and
nothing more ([Logs](/docs/runbook/tenant/services/logs/)).

**The UIDs are the same in every tenant's organisation, on every site, and on the
[take-home Pi](/docs/runbook/tenant/take-it-home/).** A dashboard that names them moves between
those places unchanged. Name data sources by these UIDs, never by the numeric id Grafana shows.

The login comes back as attributes of your tenant:

| Attribute | |
|---|---|
| `dashboard_url` | where Grafana is |
| `dashboard_org_id` | your organisation |
| `dashboard_username` | your tenant's name |
| `dashboard_password` | sensitive; in your state, like your log tokens |

A tenant created before dashboards existed gets its login when the operator reconciles it. Ask
the operator for the password. After that, your state keeps it.

## Logging in

Open `dashboard_url` in a browser on `DVNTM-TD`, the trusted network, or from a workload, and sign
in with `dashboard_username` and `dashboard_password`. The certificate is the site CA's, the same
one as the broker's and the log store's.

## Dashboards as code

Declare dashboards with the [`grafana/grafana`](https://registry.terraform.io/providers/grafana/grafana/latest/docs)
Terraform provider. It reads its connection from the environment, so the same code runs against
Deevnet and against your Pi:

```bash
export GRAFANA_URL="$(terraform output -raw dashboard_url)"
export GRAFANA_AUTH="<dashboard_username>:<dashboard_password>"
export GRAFANA_CA_CERT=site-ca.pem
export TF_VAR_grafana_org_id=<dashboard_org_id>
```

The [`kit_env` output](/docs/runbook/tenant/take-it-home/#the-one-rule-configure-from-the-environment)
writes all four for you.

```hcl
terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 4.46"
    }
  }
}

provider "grafana" {}   # GRAFANA_URL, GRAFANA_AUTH, GRAFANA_CA_CERT

variable "grafana_org_id" {
  type = string
}

resource "grafana_folder" "app" {
  org_id = var.grafana_org_id
  title  = "My app"
}

resource "grafana_dashboard" "devices" {
  org_id      = var.grafana_org_id
  folder      = grafana_folder.app.uid
  config_json = file("${path.module}/devices.json")
}
```

{{< hint warning >}}
**Put `org_id` on every resource.** Under a username and password, the provider ignores its own
`org_id` setting and `GRAFANA_ORG_ID`, and sends organisation 1, which you are not a member of. Every
create then fails with `403 ... folders:create`. Tested with provider v4.46.0 against Grafana 13.2.2.
{{< /hint >}}

### A starter dashboard

`devices.json`: a temperature graph taken from your device logs, your device log lines, and your
workload log lines.

```json
{
  "uid": "my-devices",
  "title": "My devices",
  "time": { "from": "now-6h", "to": "now" },
  "refresh": "30s",
  "panels": [
    {
      "type": "timeseries",
      "title": "Temperature (from device logs)",
      "gridPos": { "x": 0, "y": 0, "w": 24, "h": 8 },
      "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-devices" },
      "fieldConfig": { "defaults": { "unit": "celsius" }, "overrides": [] },
      "targets": [
        {
          "refId": "A",
          "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-devices" },
          "queryType": "statsRange",
          "expr": "temp_c:* | stats by (device) avg(temp_c) temp_c",
          "legendFormat": "{{device}}"
        }
      ]
    },
    {
      "type": "logs",
      "title": "Device logs",
      "gridPos": { "x": 0, "y": 8, "w": 24, "h": 10 },
      "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-devices" },
      "targets": [
        {
          "refId": "A",
          "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-devices" },
          "queryType": "instant",
          "expr": "*"
        }
      ]
    },
    {
      "type": "logs",
      "title": "Workload logs",
      "gridPos": { "x": 0, "y": 18, "w": 24, "h": 10 },
      "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-workloads" },
      "targets": [
        {
          "refId": "A",
          "datasource": { "type": "victoriametrics-logs-datasource", "uid": "deevnet-logs-workloads" },
          "queryType": "instant",
          "expr": "*"
        }
      ]
    }
  ]
}
```

**The temperature panel needs no metrics service.** A device that logs a JSON payload such as
`{"msg":"reading","temp_c":21.5}` to `<tenant>/log/<device>` stores `temp_c` as a field, and
`stats by (device) avg(temp_c)` turns it into one line per device. Any numeric field works the same
way.

## Keep dashboards in code

**A dashboard built only by clicking is not kept.** The platform treats Grafana's own database as
rebuildable: after a rebuild your organisation, login and data sources come back, and your
dashboards come back on your next `terraform apply`. A dashboard you built in the UI does not
come back. Export it (*Share → Export → Save to file*) into your repository and declare it as
above.

## What you can't do

- **Add or change a data source.** An Editor can't. A data source is a URL Grafana's server
  requests on your behalf, so only the platform sets them.
- **Grafana alerting.** It is off. Alerting is a
  [coming](/docs/runbook/tenant/services/coming-soon/#metrics-and-alerting) platform service.
- **Metrics.** There is no metrics store yet. Graph numbers from your logs, as above.
- **Share a dashboard with another tenant.** Organisations don't share. Copy it through code.
