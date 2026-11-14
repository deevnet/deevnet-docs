---
title: "CHG-0070: Tenant Metrics Store"
weight: -70
---

# CHG-0070: Tenant Metrics Store

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Planned.** Step A of [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) |
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

- [ ] ADR-0023 revised (tenants only, step A defined)
- [ ] The store's current release, flags and paths checked against the vendor documentation

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

- [ ] Step 1: the vendor claims checked and recorded
- [ ] Step 2: proven off site, refusals included
- [ ] Step 3: the inventory changes merged
- [ ] Step 4: the store role merged
- [ ] Step 5: the API released
- [ ] Step 6: the provider released and staged
- [ ] Step 7: deployed; tdemo, eds and mabell reconciled
- [ ] Step 8: the Metrics page, Coming Soon updated, the tdemo example
- [ ] Verification passes from `DVNTM-TD` and a tdemo workload

## Outcome

*Not yet executed.*
