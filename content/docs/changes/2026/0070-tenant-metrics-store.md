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
| **Status** | **Complete** (2026-11-14). The store is live on `obs`, written and read with the tenants' log tokens, and the verification passes from `DVNTM-TD` (34 of 34) and from an eds workload (11 of 11). Step A of [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) |
| **Window** | None needed: `obs` keeps its memory (Step 2), and vmauth reloads in place. The API redeploy is a restart of a few seconds |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (the store, vmauth, Grafana), `dv02prv001v01` (the Deevnet API), `deevnet-tenant-tdemo` |
| **Automation** | `deevnet.mgmt` `site.yml --tags metrics-store,log-store,dashboards,deevnet-api --limit` the host; `deevnet-provisioning-api` and `terraform-provider-deevnet` releases and `make stage`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a vmauth mapping that lets a token reach another tenant's partition, caught by the verification's refusals before any tenant is told |
| **Related changes** | [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) (the tokens this reuses), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) (the Grafana organizations), [CHG-0046](/docs/changes/2026/0046-service-proxy/) (443 by name) |
| **Related runbooks** | [Metrics](/docs/runbook/tenant/services/metrics/), [Coming Soon](/docs/runbook/tenant/services/coming-soon/) |

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
- The store, on `obs`, with each component's memory capped.
- vmauth's tenant users gaining the metrics paths.
- The `metrics` name on the service proxy.
- The API's metrics endpoint and Grafana data source, applied to existing tenants by reconcile.
- The provider's `metrics_endpoint`.
- Tenant removal deleting the tenant's metrics, as it does its logs
  ([CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/)).
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
| The store crowds out the log store | `obs` | Each component's caches capped with `-memory.allowedBytes`; the store-wide series caps |
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

- The `metrics` alias, and a `metrics` entry in `service_proxy_vhosts` for vmauth.
- The store's retention, 90 days, its series caps and each component's memory cap.

### Step 4: The store role

A `deevnet.mgmt` role, tagged `metrics-store`: vminsert, vmselect and vmstorage as containers on
`obs`, on the host network, bound to loopback, with data on the data disk. vminsert and vmselect
run with `-enableMultitenancyViaHeaders=false`, vmselect with a `-deleteAuthKey` only the writer
holds, and each with `-memory.allowedBytes`. The images are mirrored on the artifact server like
vmauth's.

### Step 5: The API

- The vmauth users the writer renders gain the metrics paths: write on `(index, 0)` for the ingest
  token, and read on `(index, 0)` and `(index, 1)` for the read token. The log contract's wire format
  doesn't change: the partitions are still derived from the index.
- The writer's purge also deletes the tenant's metrics.
- The tenant's response gains a `metrics_endpoint`.
- Grafana's data-source contract gains `deevnet-metrics-workloads`, the built-in Prometheus type,
  with the read token.
- Reconcile applies both to existing tenants.
- Release, with the CHANGELOG.

### Step 6: The provider

`deevnet_tenant` exports `metrics_endpoint`. Release, with the CHANGELOG and the provider's docs
site, and stage it in tenant downloads.

### Step 7: Deploy

1. The store role.
2. The log store role: the new writer first, then its base file and config naming the store.
3. The dashboards role, then the API.
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
- [x] Step 2: proven off site, refusals included
- [x] Step 3: the inventory changes merged
- [x] Step 4: the store role merged
- [x] Step 5: the API released
- [x] Step 6: the provider released and staged
- [x] Step 7: deployed; tdemo, eds and mabell reconciled
- [x] Step 8: the Metrics page, Coming Soon updated, the tdemo example
- [x] Verification passes from `DVNTM-TD` and a tenant workload (eds's; tdemo's state is not on the computer that ran it)

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

### Step 2: proven on the Builder (2026-11-14)

VictoriaMetrics `v1.156.0-cluster`, vmauth `v1.152.0`, VictoriaLogs `v1.52.0` and Grafana 13.2.2 in
containers on the Builder. Two tenants, eds (index 2) and tdemo (index 1), with vmauth's
configuration rendered by the writer's own code. The code is
[deevnet-provisioning-api#74](https://github.com/deevnet/deevnet-provisioning-api/pull/74).

**Routing and isolation: 28 of 28 checks pass.**
- Each tenant writes and reads its own metrics, and reads none of the other's.
- The ingest token is refused a read, and the read token a write.
- None of these reaches another tenant's metrics:
  - writing to `/insert/1:0/…` or `/insert/multitenant/…`, or by `..` in the path (400)
  - reading `/select/multitenant/…` or `/select/1:0/…`, by `..` in the path, or naming tdemo's
    partition in `X-Deevnet-Partition` (eds reads its own)
  - an `AccountID` header, or a `vm_account_id` label on a sample, which stay in the writer's own
    partition as an ordinary header or label
- `delete_series` is unreachable, and the series survive.
- The operator reads a tenant's metrics only by selecting it.
- Logs are unaffected: each tenant still writes and reads its own, and not the other's.

**A real remote-write client works.** vmagent, writing as eds with its ingest token, put 890 series
in eds's partition, and tdemo saw none.

**Grafana works.** Organizations built by the API's own Grafana code, with the new
`deevnet-metrics-workloads` data source: each tenant's login queries its own metric and not the
other's. The API's integration suite passes.

**Tenant removal now deletes metrics too.** Removing eds deleted its series, through vmselect's
delete API and a key only the writer holds, and left tdemo's 20,001 untouched. The scope gained
this: without it, a removed tenant's metrics would outlive it, against CHG-0065.

**Memory: `obs` keeps 4 GB.**
- The cluster used about 120 MB holding 20,000 series (vmstorage 54 MB, vmselect 37 MB, vminsert
  25 MB). Today's tenants would be far below that.
- `obs` uses 817 MB of its 3.9 GB, with 3 GB available.
- Each component sizes its caches from the whole VM's memory unless told otherwise
  (`-memory.allowedPercent`, 60% by default), so each is capped with `-memory.allowedBytes`.
- The operator chose no resize on 2026-11-14. A resize stays the remedy if measurement later says
  so.

**Found for the tenant docs:**
- A sample is queryable about 30 seconds after it is written. vmselect leaves out the most recent
  30 seconds by default (`-search.latencyOffset`).
- An instant query looks back five minutes, so a series not written for longer reads as absent;
  `last_over_time(...[1h])` finds it.
- `/api/v1/import/prometheus` takes the Prometheus text format, so `curl` can push a metric with no
  client library.

### Steps 3 to 7: released and deployed (2026-11-14)

- **Merged and released:** the inventory
  ([ansible-inventory-deevnet#113](https://github.com/deevnet/ansible-inventory-deevnet/pull/113)),
  the store role ([ansible-collection-deevnet.mgmt#132](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/132)),
  the API and writer `v0.24.0`
  ([deevnet-provisioning-api#75](https://github.com/deevnet/deevnet-provisioning-api/pull/75)) and
  the provider `v0.12.0`
  ([terraform-provider-deevnet#37](https://github.com/deevnet/terraform-provider-deevnet/pull/37)),
  staged to the tenant downloads.
- **The store's three images were staged by hand.** The Builder's container image run pulls every
  listed image each time, and stops at the retired MinIO image, which its registry now refuses. The
  tarballs carry the same names and `-latest` links that run makes.
- **DNS:** `metrics.mobile.deevnet.net` resolves to `obs`, and the router's configuration was backed
  up after.
- **`obs`:** the first run failed before the store started: the store role's default for the delete
  key named a variable of the log store role, which its own play does not load. The writer, its
  configuration and the key were already in place. Fixed in
  [ansible-collection-deevnet.mgmt#133](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/133),
  and the second run finished with no failure: the three containers run, vmauth carries the new
  routes, and the proxy's certificate names `metrics`.
- **Checked on `obs`:**
  - each component answers its health check;
  - `vmstorage` runs with `-retentionPeriod=90d` and both series caps;
  - vmauth gives each tenant one write route, to its own `(index, 0)`, and read routes to its own
    `(index, 0)` and `(index, 1)` only, with none to `multitenant` or `/delete/`;
  - an unauthenticated query through `metrics.mobile.deevnet.net` is refused (401);
  - `obs` uses 892 MB of its 3.9 GB.
- **`prv`:** the API runs `v0.24.0`. Reconciling tdemo, eds and mabell succeeded for all three.
- **Step 8:** the tenant Metrics page and Coming Soon
  ([deevnet-docs#437](https://github.com/deevnet/deevnet-docs/pull/437)), and the tdemo example,
  `METRICS_ENDPOINT` in `kit.env` and `scripts/metrics-check.sh`
  ([deevnet-tenant-tdemo#20](https://github.com/deevnet/deevnet-tenant-tdemo/pull/20)).

### Verification from `DVNTM-TD` (2026-11-14)

**34 of 34 checks pass**, run from a Mac on `DVNTM-TD` as eds (index 2) and mabell (index 3), with
each tenant's tokens and Grafana login read from its own state:
- `metrics.mobile.deevnet.net` resolves to `obs`, and its certificate chains to the Deevnet Root CA.
  A request with no token is refused.
- The API names the store as each tenant's `metrics_endpoint`.
- Each tenant pushes with its ingest token and reads its sample back with its read token. It also
  reads its platform partition, `(index, 1)`.
- These are refused (400) for each tenant:
  - the read token writing, and the ingest token querying;
  - the other tenant's `/insert/<index>:0/` and `/select/<index>:0/`;
  - `/select/multitenant/`.
- Each tenant's read token sees none of the other's samples. Naming the other's partition in
  `X-Deevnet-Partition` reads only its own.
- Each tenant still writes and reads back its logs.
- Each tenant's Grafana organization has `deevnet-metrics-workloads` and shows its own sample
  through it, and none of the other's.

**Retention** reads back as 90 days on `vmstorage` (Steps 3 to 7).

### Verification from a workload (2026-11-14)

**11 of 11 checks pass on eds's workload, `eds-services`**, over the tenant fabric's path to `obs`.
The tokens came from eds's state on the Mac, through the SSH session's input, and were never written
to the workload. eds stood in for tdemo, whose state is not on that Mac; the path is the same for
every tenant.
- `metrics.mobile.deevnet.net` resolves on the workload, and the store answers with a certificate it
  trusts. A request with no token is refused.
- The workload pushes with the ingest token and reads its sample back with the read token.
- These are refused: the read token writing, the ingest token querying, mabell's `/insert/3:0/`,
  and `/select/multitenant/`.
- Naming mabell's partition reads only eds's own.
- The workload still writes and reads back its logs.
