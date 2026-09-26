---
title: "Logs"
weight: 5
---

# Logs {{< status-badge "active" "Available" >}}

## What you get

Three log **partitions** of your own in the platform log store, and two tokens
([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/)):

| Partition | What lands there | How it gets there |
|---|---|---|
| `(index, 0)` | your **workloads'** logs | you ship them, with your ingest token |
| `(index, 1)` | what the **platform** says about your tenant | the platform |
| `(index, 2)` | your **devices'** logs | devices publish to MQTT; a bridge carries them |

`index` is your tenant's index (`deevnet_tenant.this.index`). The tokens and endpoint are attributes
of your tenant: `log_endpoint`, `log_ingest_token`, `log_read_token`, `log_select_header`.

No other tenant's token can read your partitions, and yours cannot read theirs.

## Device logs: publish to `log/<device>`

A device logs by publishing to **`<tenant>/log/<device name>`** — its broker account may publish
there and nowhere else under `log/` ([Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/)).
The payload can be plain text or JSON; without a time field, the broker's receive time is used.

```text
topic:   bench1/log/pico-1
payload: {"level":"info","msg":"boot ok, rssi -61"}
```

**Numbers in a JSON payload are fields you can graph.** A device that logs
`{"msg":"reading","temp_c":21.5}` can have its temperature charted on your
[dashboards](/docs/runbook/tenant/services/dashboards/) with
`temp_c:* | stats by (device) avg(temp_c) temp_c` — no metrics service needed.

The tenant is taken from the topic's first level and the device from its last — never from the
payload, so a device cannot write into another tenant's logs by claiming to be one.

## Workload logs: ship with the ingest token

The store is VictoriaLogs behind an authenticating proxy. From a workload:

```bash
curl -sS --cacert site-ca.pem \
  -H "Authorization: Bearer $LOG_INGEST_TOKEN" \
  -H "Content-Type: application/stream+json" \
  --data-binary '{"_msg":"backend started","app":"backend"}' \
  "$LOG_ENDPOINT/insert/jsonline"
```

The ingest token writes only to `(index, 0)`.

{{< hint warning >}}
**Send the `Content-Type` header.** Without it the store answers `200` and **keeps nothing**: curl's
`--data-binary` defaults to `application/x-www-form-urlencoded`, and VictoriaLogs v1.52.0 does not
read that body as JSON lines. Checked against the version the site runs: the same line with the
header is stored, without it it is not. Every client library that posts here needs the header too.
{{< /hint >}}

## Reading back

```bash
# your workloads' logs (partition 0, the default)
curl -sS --cacert site-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  "$LOG_ENDPOINT/select/logsql/query" --data-urlencode 'query=*'

# your devices' logs: select partition 2 with the select header
curl -sS --cacert site-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  -H "X-Deevnet-Partition: ${INDEX}-2" \
  "$LOG_ENDPOINT/select/logsql/query" --data-urlencode 'query=*'
```

**Or read them in Grafana:** your organization has all three partitions wired in as data sources
([Dashboards](/docs/runbook/tenant/services/dashboards/)).

## What it does not do yet

- **Device logging is proven end to end with a real tenant's credentials, but no shipped firmware
  logs this way yet.** The store is built and deployed; ADR-0027 stays Proposed until a device's
  firmware ships using it. You may be the first
- **Destroying the tenant does not delete logs** already written; they age out with retention
