---
title: "Metrics"
weight: 5
---

# Metrics

{{< status-badge "active" "Available" >}}

## What you get

A Prometheus-compatible metrics store of your own, written and read with the log tokens you already
hold ([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)). Your
workloads push to it, and you query it with the Prometheus API or in Grafana. The platform never
scrapes a workload of yours.

| Partition | What lands there | How it gets there |
|---|---|---|
| `(index, 0)` | your **workloads'** metrics | you push them, with your ingest token |
| `(index, 1)` | what the **platform** measures about your tenant | the platform; empty today |

`index` is your tenant's index (`deevnet_tenant.this.index`). The endpoint is an attribute of your
tenant, `metrics_endpoint` (`https://metrics.mobile.deevnet.net`), and needs provider 0.12 or later.
The tokens are the ones from [Logs](/docs/runbook/tenant/services/logs/): `log_ingest_token` writes,
`log_read_token` reads, and `log_select_header` chooses a partition.

No other tenant's token can read your metrics, and yours cannot read theirs. The partition comes
from your token, never from the request: a request that names another tenant's partition reads
your own `(index, 0)`, or is refused.

## Pushing

**Push with Prometheus remote write, to `/api/v1/write`.** Any agent that remote-writes works:
vmagent, Prometheus in agent mode, Grafana Alloy, or an OpenTelemetry Collector with its Prometheus
remote write exporter. Run it on your workload, scraping your own app, and give it the endpoint, the
ingest token as a bearer token, and the Deevnet Root CA:

```yaml
# prometheus.yml, Prometheus in agent mode
remote_write:
  - url: https://metrics.mobile.deevnet.net/api/v1/write
    authorization:
      credentials_file: /etc/prometheus/ingest-token
    tls_config:
      ca_file: /etc/prometheus/deevnet-root-ca.pem
```

**Or push in the Prometheus text format, to `/api/v1/import/prometheus`.** One line a sample, so a
script or a cron job can push with `curl`:

```bash
curl -sS --cacert deevnet-root-ca.pem \
  -H "Authorization: Bearer $LOG_INGEST_TOKEN" \
  --data-binary 'backend_queue_depth{app="backend"} 17' \
  "$METRICS_ENDPOINT/api/v1/import/prometheus"
```

A sample without a timestamp takes the time it arrives. The ingest token writes only to
`(index, 0)`, and only to these two paths.

## Querying

**Query with the Prometheus HTTP API and PromQL**, with your read token:

```bash
# your workloads' metrics (partition 0, the default)
curl -sS --cacert deevnet-root-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  "$METRICS_ENDPOINT/api/v1/query" --data-urlencode 'query=backend_queue_depth'

# what the platform measures about your tenant: partition 1, with the select header
curl -sS --cacert deevnet-root-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  -H "X-Deevnet-Partition: ${INDEX}-1" \
  "$METRICS_ENDPOINT/api/v1/query" --data-urlencode 'query=up'
```

The read token may use `query`, `query_range`, `query_exemplars`, `series`, `labels`, a label's
`values`, `metadata` and `status/buildinfo`, all under `/api/v1/`. The store is VictoriaMetrics, so
its MetricsQL works as well as PromQL.

**Or query in Grafana:** your organization has a `deevnet-metrics-workloads` data source that reads
`(index, 0)` ([Dashboards](/docs/runbook/tenant/services/dashboards/)).

## Timing

- **A sample is queryable about 30 seconds after it arrives.** The store holds back its newest 30
  seconds so a query does not see a half-written moment.
- **An instant query looks back 5 minutes.** A series pushed less often than that drops out of
  `query` between pushes; `query_range`, or `last_over_time(metric[1h])`, still finds it.
- **Metrics are kept 90 days**, then deleted. Removing your tenant deletes all of them, as it does
  your logs, before its index is given to another tenant.

## Keeping it small

**Keep label values few.** The store limits how many new series the whole site takes in an hour and
in a day, and every distinct set of label values is a series. A label holding a request ID, a user,
or a timestamp makes a new series each time and uses up that limit for every tenant. Labels such as
`app`, `host` or `status` are the right size.

## Alerts

**Rules over your metrics can send alerts to your phone:** see
[Alerting](/docs/runbook/tenant/services/alerting/).

## What it does not do yet

- **The platform's partition is empty:** your workloads' CPU, memory, disk and network will appear
  in `(index, 1)` later.
