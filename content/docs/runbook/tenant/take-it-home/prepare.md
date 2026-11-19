---
title: "Prepare Your Tenant"
weight: 1
---

# Prepare Your Tenant

**The move takes one file, as long as your app never hard-codes a Deevnet name.** Read every
endpoint from the environment, under the names below, and have Terraform write that environment
while your tenant is still on Deevnet. The backend writes the same file with its own values.

## The one rule: configure from the environment

| Variable | On Deevnet | On your backend |
|---|---|---|
| `DEEVNET_TENANT` | your tenant | the same |
| `MQTT_HOST` | `mqtt.mobile.deevnet.net` | `<hostname>.local` |
| `MQTT_PORT` | `8883` | `8883` |
| `MQTT_CA_FILE` | `deevnet-root-ca.pem` (Deevnet's root) | `backend-ca.pem` (the backend's) |
| `MQTT_USERNAME`, `MQTT_PASSWORD` | your app's broker account | the same: you re-create it with the same password |
| `LOG_ENDPOINT` | `log_endpoint` | `https://<hostname>.local:8427` |
| `LOG_INGEST_TOKEN`, `LOG_READ_TOKEN` | `log_ingest_token`, `log_read_token` | the backend's |
| `LOG_SELECT_HEADER` | `X-Deevnet-Partition` | the same |
| `LOG_DEVICE_PARTITION` | `<index>-2` | the same, if you keep the index |
| `METRICS_ENDPOINT` | `metrics_endpoint` | `https://<hostname>.local:8427` |
| `GRAFANA_URL` | `dashboard_url` | `https://<hostname>.local:3000` |
| `GRAFANA_AUTH` | `dashboard_username:dashboard_password` | the backend's |
| `GRAFANA_ORG_ID`, `TF_VAR_grafana_org_id` | `dashboard_org_id` | the backend's |
| `GRAFANA_CA_CERT` | `deevnet-root-ca.pem` (Deevnet's root) | `backend-ca.pem` (the backend's) |
| `NOTIFY_URL` | `notify_endpoint` | `https://<hostname>.local` |
| `NOTIFY_USERNAME`, `NOTIFY_PASSWORD` | `notify_username`, `notify_password` | your tenant's name, and the backend's |
| `S3_ENDPOINT` | a bucket's `endpoint` | `https://<hostname>.local:9000` |
| `S3_CA_FILE` | `deevnet-root-ca.pem` (Deevnet's root) | `backend-ca.pem` (the backend's) |
| `BUCKET_<NAME>`, `_ACCESS_KEY`, `_SECRET_KEY` | a bucket's `bucket`, and a key's `access_key` and `secret_key` | the same, if you bring the key |

The `GRAFANA_*` names are the ones the Terraform `grafana` provider reads by itself, and
`TF_VAR_grafana_org_id` feeds the `org_id` every resource must carry
([Dashboards](/docs/runbook/tenant/services/dashboards/#dashboards-as-code)). The dashboards' data
sources have the same UIDs on both, so **the same dashboard code applies to both**.

## Have Terraform write the file

**A `kit_env` output gives your app its Deevnet environment in one file.**

```hcl
output "kit_env" {
  sensitive = true
  value     = <<-EOT
    DEEVNET_TENANT=${deevnet_tenant.this.name}
    MQTT_HOST=mqtt.mobile.deevnet.net
    MQTT_PORT=8883
    MQTT_CA_FILE=deevnet-root-ca.pem
    MQTT_USERNAME=${deevnet_iot_broker_account.backend.username}
    MQTT_PASSWORD=${deevnet_iot_broker_account.backend.password}
    LOG_ENDPOINT=${deevnet_tenant.this.log_endpoint}
    LOG_INGEST_TOKEN=${deevnet_tenant.this.log_ingest_token}
    LOG_READ_TOKEN=${deevnet_tenant.this.log_read_token}
    LOG_SELECT_HEADER=${deevnet_tenant.this.log_select_header}
    LOG_DEVICE_PARTITION=${deevnet_tenant.this.index}-2
    METRICS_ENDPOINT=${deevnet_tenant.this.metrics_endpoint}
    GRAFANA_URL=${deevnet_tenant.this.dashboard_url}
    GRAFANA_AUTH=${deevnet_tenant.this.dashboard_username}:${deevnet_tenant.this.dashboard_password}
    GRAFANA_ORG_ID=${deevnet_tenant.this.dashboard_org_id}
    TF_VAR_grafana_org_id=${deevnet_tenant.this.dashboard_org_id}
    GRAFANA_CA_CERT=deevnet-root-ca.pem
    NOTIFY_URL=${deevnet_tenant.this.notify_endpoint}
    NOTIFY_USERNAME=${deevnet_tenant.this.notify_username}
    NOTIFY_PASSWORD=${deevnet_tenant.this.notify_password}
    S3_ENDPOINT=${deevnet_bucket.files.endpoint}
    S3_CA_FILE=deevnet-root-ca.pem
    BUCKET_FILES=${deevnet_bucket.files.bucket}
    BUCKET_FILES_ACCESS_KEY=${deevnet_bucket.files.access_key}
    BUCKET_FILES_SECRET_KEY=${deevnet_bucket.files.secret_key}
  EOT
}
```

```bash
terraform output -raw kit_env > kit.env
```

`deevnet_iot_broker_account.backend` is your app's own broker account (the walkthrough's
`backend`), a workload account with no `device`
([Devices and MQTT](/docs/runbook/tenant/services/devices-and-mqtt/)). Your app logs in with it on
Deevnet, and on the backend you re-create it with the same password
([Move your tenant](/docs/runbook/tenant/take-it-home/move-your-tenant/#recreate-your-broker-accounts)),
so those two lines are the same on both.

If the app runs with that file on Deevnet, the backend's `kit.env` runs it on the backend.

## Before you move

**Save `terraform output -json flash`: it holds your devices' broker passwords.** Keep those
passwords on the backend, and nothing on a device needs reflashing but the broker's address and the
CA.

**Note your tenant's name and index** (`terraform output`, or `deevnet_tenant.this.index`). The
backend asks for both at its first boot; with the same index, `LOG_DEVICE_PARTITION` doesn't
change either.
