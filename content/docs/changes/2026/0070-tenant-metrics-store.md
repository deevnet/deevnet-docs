---
title: "CHG-0070: Tenant Metrics Store"
weight: -70
---

# CHG-0070: Tenant Metrics Store

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **In progress.** Step 1 done: the vendor claims hold, with three findings that shape Steps 2 to 5. Step A of [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) |
| **Window** | One restart of `dv02obs001v01` for its memory. The log store, Grafana and downloads are unavailable for that minute; tenant log clients that buffer lose nothing |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (the store, vmauth, Grafana), `dv02prv001v01` (the Deevnet API), `deevnet-tenant-tdemo` |
| **Automation** | `deevnet.mgmt` `site.yml --tags vms,metrics-store,log-store,dashboards,deevnet-api --limit` the host; `deevnet-provisioning-api` and `terraform-provider-deevnet` releases and `make stage`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a vmauth mapping that lets a token reach another tenant's partition, caught by the verification's refusals before any tenant is told |
| **Related changes** | [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) (the tokens this reuses), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) (the Grafana organizations), [CHG-0046](/docs/changes/2026/0046-service-proxy/) (443 by name) |
| **Related runbooks** | [Coming Soon](/docs/runbook/tenant/services/coming-soon/) |

---

## Summary

Tenants have a log store and Grafana but nowhere to keep metrics.
[ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) adds a
Prometheus-compatible store, a VictoriaMetrics cluster, on `dv02obs001v01` behind the log store's
vmauth. This change builds it and opens it to tenants:
- Tenants push with Prometheus remote write to `metrics` on 443, with the ingest token they already
  hold.
- Each Grafana organization gains a `deevnet-metrics-workloads` data source.
- Alerting (step B) and each workload's resource use (step C) are later changes.

## Goal

- A tenant pushes metrics to its metrics endpoint with its ingest token, and they land in its own
  `(index, 0)` only.
- A tenant reads them through the Prometheus API with its read token, and in Grafana through
  `deevnet-metrics-workloads`.
- Each tenant is refused the other tenants' metrics, writing and reading, directly and through
  Grafana.
- Metrics are kept 90 days.
- The tenant runbook has a Metrics page, and Coming Soon keeps only alerting.

## Scope

**In scope:**
- The store, on `obs`, and `obs`'s resize.
- vmauth's tenant users gaining the metrics paths.
- The `metrics` name on the service proxy.
- The API's metrics endpoint and Grafana data source, applied to existing tenants by reconcile.
- The provider's `metrics_endpoint`.
- The tenant docs and a tdemo example.

**Out of scope:**
- Alert rules and notifications (ADR-0023 step B).
- Each workload's resource use, `(index, 1)` (step C).
- Metrics for the substrate.
- The take-home Pi's own Grafana.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A token reaches another tenant's metrics, or the multitenant endpoint | vmauth | Verification refuses each, both ways, writing and reading |
| A tenant names its own partition and writes another's | vmauth | Partitions are derived from the token, never read from the request; verification tries it |
| The store crowds out the log store | `obs` | Memory measured before the size is set; the store-wide caps |
| A metrics change breaks the logs | vmauth | Verification reads and writes logs as each tenant after the change |

## Prerequisites

- [x] ADR-0023 revised (tenants only, step A defined)
- [x] The store's current release, flags and paths checked against the vendor documentation (Step 1)

## Procedure

### Step 1: Check the vendor claims

- The VictoriaMetrics cluster's current release, its retention flag and its store-wide series
  limits.
- vmauth's mapping of plain Prometheus paths to `/insert/<index>:0/` and
  `/select/<index>:<project>/`, beside the log paths, for one token.
- Record what holds and what doesn't in this record before Step 2.

### Step 2: Prove it off site

The cluster, vmauth and Grafana in containers on the Builder, with two tenants' users rendered by
`deevnet-log-user`. Run the verification's refusals there first.

### Step 3: The inventory

- `obs`'s memory, from 4 GB to the measured figure.
- The `metrics` alias, and a `metrics` entry in `service_proxy_vhosts` for vmauth.
- The store's retention, 90 days, and caps.

### Step 4: The store role

A `deevnet.mgmt` role, tagged `metrics-store`: vminsert, vmselect and vmstorage as containers on
`obs`, on the host network, bound to loopback, with data on the data disk.

### Step 5: The API

- The vmauth users the writer renders gain the metrics paths: write on `(index, 0)` for the ingest
  token, and read on `(index, 0)` and `(index, 1)` for the read token. The log contract's wire format
  doesn't change: the partitions are still derived from the index.
- The tenant's response gains a `metrics_endpoint`.
- Grafana's data-source contract gains `deevnet-metrics-workloads`, the built-in Prometheus type,
  with the read token.
- Reconcile applies both to existing tenants.
- Release, with the CHANGELOG.

### Step 6: The provider

`deevnet_tenant` exports `metrics_endpoint`. Release, with the CHANGELOG and the provider's docs
site, and stage it in tenant downloads.

### Step 7: Deploy

1. Resize and restart `obs`.
2. The store role, then the log store role (vmauth), then the dashboards role.
3. The API.
4. Reconcile tdemo, eds and mabell.

### Step 8: Docs and the reference tenant

- **The tenant runbook:**
  - A new page, `runbook/tenant/services/metrics.md`: pushing, querying, Grafana and the 90 days.
  - Coming Soon keeps alerting only.
- **`deevnet-tenant-tdemo`** pushes a metric from its workload.
- **Platform docs:** the Deevnet API's and the provider's pages, and the Software Catalog.

## Verification

From `DVNTM-TD`, and from a tdemo workload:
- tdemo's workload pushes by remote write, and the series reads back through the Prometheus API.
- It shows in tdemo's Grafana through `deevnet-metrics-workloads`.
- eds's read token reads none of tdemo's series, and tdemo's none of eds's.
- An ingest token is refused a read, and a read token a write.
- A request naming another tenant's `/insert/<index>:0/` or `/select/<index>:0/` writes or reads
  only the caller's own partition, or is refused.
- `/select/multitenant/` is refused to every tenant token.
- Each tenant still writes and reads its logs.
- The store's retention reads back as 90 days.

## Undo

### Undo Step 7

Redeploy the previous API release and the previous vmauth configuration; stop the store's
containers. Grafana's metrics data sources are removed by the previous release's reconcile. Metrics
already stored stay on the data disk until removed by hand.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the vendor claims checked and recorded
- [ ] Step 2: proven off site, refusals included
- [ ] Step 3: the inventory changes merged
- [ ] Step 4: the store role merged
- [ ] Step 5: the API released
- [ ] Step 6: the provider released and staged
- [ ] Step 7: deployed; tdemo, eds and mabell reconciled
- [ ] Step 8: the Metrics page, Coming Soon updated, the tdemo example
- [ ] Verification passes from `DVNTM-TD` and a tdemo workload

## Outcome

### Step 1: the vendor claims (2026-11-14)

Checked against VictoriaMetrics' documentation at the `v1.156.0` tag, and Docker Hub.

| Claim | Found | Holds |
|---|---|---|
| A current release of the cluster | `v1.156.0`, released 2026-11-09; images `victoriametrics/vminsert`, `vmselect` and `vmstorage` tagged `v1.156.0-cluster` | Yes. The store is pinned there. vmauth stays on the log store's pin, `v1.152.0` |
| A minimal cluster on one host | *"A minimal cluster setup consists of"* one `vmstorage`, one `vminsert` and one `vmselect` | Yes |
| Tenants need no setup | *"Tenants are automatically created when the first data point is written into the given tenant."* | Yes. The API creates nothing in the store |
| Retention is one flag | `-retentionPeriod`, on `vmstorage`. Per-tenant retention (`-retentionFilter`) is Enterprise | Yes. The value's format is confirmed by `-help` in Step 2 |
| A store-wide series cap | `-storage.maxHourlySeries` and `-storage.maxDailySeries` on `vmstorage`: *"limits on the number of unique time series across all the tenants"*, set per `vmstorage` node. `vminsert`'s `-maxLabelsPerTimeseries` defaults to 40 | Yes. No per-tenant cap exists in the open-source cluster, as ADR-0023 §6 assumed |
| vmauth maps a plain Prometheus path to a tenant | The vendor's own example: `src_paths: ["/api/v1/write"]` to `url_prefix: "http://vminsert-backend:8480/insert/1/prometheus/"`. *"By default, `vmauth` doesn't strip the path prefix"*, so the request path is appended | Yes |
| `src_paths` can't be escaped by a longer path | *"the whole requested path matches at least one `src_paths` entry"* | Yes |

**Finding 1: the multitenant endpoints are always on, and only vmauth keeps tenants from them.**
- `/insert/multitenant/` takes each sample's tenant from its `vm_account_id` label, and
  `/select/multitenant/` reads any tenant. No flag turns them off. The vendor: *"It is recommended
  restricting access to `multitenant` endpoints only to trusted sources"*.
- **They are out of a tenant's reach by construction.** A tenant's metrics routes are fixed paths
  whose `url_prefix` names its own `<index>:<project>`. A request to `/insert/...` or `/select/...`
  matches the log routes, whose backend is VictoriaLogs, not the metrics store. The verification
  tries both.

**Finding 2: since `v1.150.0`, the store also takes the tenant from `AccountID` and `ProjectID`
headers.**
- The vendor: *"If tenant IDs are specified in URL, then headers are ignored."* A tenant's route
  always names the tenant in the URL, and vmauth already overwrites both headers on every route for
  the logs, so either way the tenant is the caller's own.
- **The store runs with `-enableMultitenancyViaHeaders=false`** all the same, so no path without a
  tenant exists. One mechanism, not two.

**Finding 3, for step B: vmalert *"deliberately allows configuring only one `datasource.url`"*.**
- The vendor recommends *"separate instances of vmalert for each datasource type"*.
- vmalert queries `<datasource.url>/api/v1/query` for metrics rules and
  `<datasource.url>/select/logsql/stats_query` for log rules. With vmauth as the one URL, a tenant's
  read user routes both. Whether one instance holds both rule types is to prove in step B; if not,
  step B runs two per tenant.
- A rule group's `headers` can carry `X-Deevnet-Partition`, so a log rule can read the tenant's
  device partition. vmauth still overwrites `AccountID` and `ProjectID`.

**What this sets for Steps 2 to 5:**
- **A tenant's metrics routes are an allowlist**, ahead of its log routes:
  - ingest token: `/api/v1/write` to `/insert/<index>:0/prometheus/`
  - read token: `/api/v1/query`, `query_range`, `series`, `labels`, `label/<name>/values`,
    `metadata`, `query_exemplars` and `status/buildinfo` to `/select/<index>:<project>/prometheus/`,
    with the partition chosen by `X-Deevnet-Partition` as for the logs, `(index, 0)` by default
- **Deletion is not reachable.** The store deletes under `/delete/<accountID>/`, which no route
  names.
- **The vendor gives no memory figure for a small cluster.** `obs`'s size is set from Step 2's
  measurement.
