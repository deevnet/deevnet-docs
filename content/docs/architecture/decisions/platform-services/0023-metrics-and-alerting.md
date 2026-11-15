---
title: "ADR-0023: Metrics and Alerting"
weight: -23
aliases:
  - /docs/architecture/decisions/0023-metrics-and-alerting/
---

# ADR-0023: Tenants Push Metrics Into a Prometheus-Compatible Store Beside Their Logs, and Alert on Their Own Data

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21; revised 2026-11-14 (tenants only, as ADR-0027 made the logs; the store on `obs`, which keeps its 4 GB; the log tokens reused; rules over logs as well as metrics; ntfy on site only; 90-day retention; built in three steps) |
| **Scope** | How tenants' metrics are stored and read, how each tenant's alert rules are declared and evaluated, and where its notifications go. How the substrate publishes each workload's resource use to its tenant. Not the substrate's own metrics or alerts to the operator. |
| **Extends** | [ADR-0022: Central Logging](/docs/architecture/decisions/platform-services/0022-central-logging/), as narrowed by [ADR-0027: Tenant Log Store](/docs/architecture/decisions/platform-services/0027-tenant-log-store/). Metrics use the log store's host, its authenticating proxy, its partition scheme and its tenant tokens. |
| **Extended by** | [ADR-0024: Dashboards](/docs/architecture/decisions/platform-services/0024-dashboards/): saved dashboards in Grafana, one organization per tenant *(Accepted)* |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/), [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/) §5, [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/tenant-networking/0018-operator-access-to-tenants/), [ADR-0036: A Service Proxy on Each Service VM](/docs/architecture/decisions/platform-services/0036-service-proxy/) |

---

## Context

### What tenants have, and what they were promised

- **Logs are the only telemetry the site stores for a tenant.** VictoriaLogs behind vmauth on
  `dv02obs001v01` holds three partitions per tenant (ADR-0027). Each tenant holds one ingest token and
  one read token, issued by the Deevnet API.
- **Each tenant has a Grafana organization** with three log data sources (ADR-0024). A numeric
  field in a log line can be graphed, but there is no metrics store behind it.
- **Nothing alerts.** A tenant learns that its workload or device has stopped by looking.
- **The tenant pages promise more:** *"VM resource utilization"*, *"Per-tenant thresholds"* and
  *"Tenant-specific notification channels"*. None of it exists.

### What is wanted

1. **Tenant metrics:** what a tenant's workloads emit, in a store a tenant reads and graphs.
2. **Each workload's resource use** as the hypervisor sees it, without the tenant instrumenting
   anything.
3. **Tenant alerts:** a tenant declares its own rules and where they notify, and nobody edits
   substrate code for it.
4. **The same partitioning as the logs.** A tenant reads and alerts on its own data only.

### The substrate is not in scope

This record was first written, on 2026-09-21, to cover the substrate as well: `dv02col001v01` on
management would scrape every substrate host, hypervisor and network device, and one vmalert would
alert the operator. On 2026-11-14 the operator scoped it to tenants, as ADR-0027 did the logs.
Metrics for the substrate and alerts to the operator stay on the
[Observability](/docs/roadmap/infrastructure/substrate/observability/) roadmap item, undecided. Only
one substrate collection stays here: the hypervisor's view of each tenant's workloads (§4), which is
published to the tenant.

---

## Options considered

### Store

Vendor documentation was checked on 2026-09-21.

| | VictoriaMetrics single-node | VictoriaMetrics cluster | Grafana Mimir monolithic | Prometheus |
|---|---|---|---|---|
| **License** | Apache 2.0 | Apache 2.0 | AGPLv3 | Apache 2.0 |
| **Tenancy** | none | `/insert/<accountID>:<projectID>/` | `X-Scope-OrgID` | none |
| **Operator reads across tenants** | — | `/select/multitenant/` | tenant federation | — |
| **Authenticates callers** | — | no, needs vmauth | no, needs a proxy | — |

- **Tenancy is a cluster feature.** VictoriaMetrics lists *"Supports multiple independent namespaces
  for time series data (aka multi-tenancy)"* for the cluster version. Its minimal cluster is *"a
  single `vmstorage` node … a single `vminsert` node … a single `vmselect` node"*, and all three can
  run on one small VM.
- **It is Prometheus-compatible.** Tenants write with Prometheus remote write and query with PromQL
  on the Prometheus HTTP API, and Grafana reads it through its built-in Prometheus data source
  (ADR-0024 §2). No tenant needs to know the engine.
- **Its URLs match the log store's partitions.** `accountID:projectID` in a path is the same pair
  VictoriaLogs uses, so vmauth maps one token to both.
- **Mimir** would work, but it needs its own proxy and object storage, and it is heavier. Its one
  unique feature is a multi-tenant Alertmanager (§5 addresses that).
- **Prometheus has no tenancy.** Sharing one between tenants means separating them by a label and
  rewriting every query in a proxy, which makes the boundary a query rewrite rather than a partition.
  One Prometheus per tenant is heavier and is built to scrape, while tenants push (§2).

### Where it runs

| Option | Verdict |
|---|---|
| **On `obs`, beside the logs, with the VM resized** | **Chosen.** vmauth, the tenant tokens and Grafana are already there, and the API already writes vmauth's users on that host |
| A VM of its own, as object storage got (ADR-0026) | Rejected: a second vmauth and a second copy of every tenant's tokens, for isolation the partitions already give. Object storage moved to protect Terraform state, which has no counterpart here |

### Alert evaluation

- **vmalert** evaluates MetricsQL, and *"integrates with VictoriaLogs and allows configuring alerting
  and recording rules using LogsQL"*. One evaluator therefore covers both signals.
- **Its multi-tenant mode is Enterprise:** the per-group `tenant` parameter works only *"when
  `-clusterMode` is enabled"*. The open-source alternatives the docs give are *"a separate `vmalert`
  instance per each tenant"*, or the multitenant endpoints with an `extra_label` per group.
- **Alertmanager is single-tenant** and has no ntfy receiver. It sends to ntfy through a
  `webhook_configs` entry, and ntfy formats the payload with its *"'alertmanager'"* template.

---

## Decision

**A VictoriaMetrics cluster on `obs`, behind the log store's vmauth, partitioned as the logs are.
Tenants push into it with their log tokens. Each tenant's rules run in its own vmalert under its own
read token, and one Alertmanager delivers through ntfy on site.** It is built in three steps (§7).

### 1. The store: a VictoriaMetrics cluster on `obs`

- **vminsert, vmselect and vmstorage run as containers on `dv02obs001v01`**, bound to loopback.
  vmauth is the only listener, and data goes on the same data disk as the logs.
- **Tenants reach it by name on 443**, at `metrics`, through the host's service proxy (ADR-0036).
  The API hands each tenant this address as its metrics endpoint.
- **`obs` keeps its 4 GB**, with each component's memory capped. Measured on 2026-11-14, the
  cluster held 20,000 series in about 120 MB, and `obs` had 3 GB available
  ([CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/) Step 2). A resize is the remedy if
  measurement later says so.
- **One retention period, 90 days.** Per-tenant retention is an Enterprise feature.

### 2. Partitions and tokens are the logs'

- **The partitions are ADR-0027's:**
  - `(index, 0)` is what the tenant ships
  - `(index, 1)` is what the substrate publishes about the tenant (§4)
- **No new tenant credentials.** The tenant's ingest token gains write on the metrics paths for
  `(index, 0)`, and its read token gains read on `(index, 0)` and `(index, 1)`. A tenant still
  holds two tokens, and they now cover both signals. The provider's attributes keep their names,
  `log_ingest_token` and `log_read_token`.
- **A tenant never names a partition.** It writes to the plain Prometheus paths, and vmauth maps
  the token to `/insert/<index>:0/`. That is the rule the log contract already follows: partitions
  are derived from the tenant, never accepted from it.
- **Tenants push, and the substrate never scrapes a tenant workload.**
  - ADR-0018's route would let it, but that route is operator access, and ADR-0018 says it is not a
    delivery path.
  - Scraping would also make substrate configuration track tenant workloads, which ADR-0010 forbids.
  - A tenant ships with any Prometheus remote-write client, such as vmagent or Prometheus's agent
    mode, through vmauth.

### 3. Reading: Grafana and the Prometheus API

- **Each tenant's Grafana organization gains metrics data sources**, built by the API like the log
  ones, using the built-in Prometheus data source and the tenant's read token (ADR-0024 §2):
  - `deevnet-metrics-workloads` for `(index, 0)`, in step A
  - `deevnet-metrics-platform` for `(index, 1)`, in step C
- **A tenant can also query the Prometheus API directly** at its metrics endpoint with its read
  token, for its own tools.

### 4. The substrate publishes each workload's resource use

- **Requirement 2's hypervisor view is published, not shared,** the same way ADR-0022 publishes
  events.
  - Proxmox reports each guest's CPU, memory, disk and network against its VMID.
  - The API knows which tenant owns each VMID (ADR-0015).
  - The substrate relabels each guest's series with the tenant's workload name and writes it to that
    tenant's `(index, 1)`.
- **A tenant sees its own workloads' resource use and nothing else of the hypervisor's.** It can't
  see the node, the other tenants, or how full the storage is.
- **`dv02col001v01` collects it.** It sits on management, which reaches the hypervisors over rules
  that already exist, and writes to `obs` over the existing `management -> platform` rule.
- **How the VMID-to-tenant map reaches the collector is open** (Open question 1). What is decided is
  that it comes from the API, never from inventory, since a tenant must not need a substrate commit.

### 5. Alerting: vmalert per tenant, one Alertmanager, ntfy on site

**Declaration.**
- **Each tenant declares its rules through the Deevnet API**, as a new provider resource holding
  rule groups. The API writes them to `obs` over the same forced-command path it uses for vmauth's
  users.
- **A rule is over metrics or over logs.** vmalert evaluates MetricsQL against the metrics store and
  LogsQL against the log store, so a tenant with devices and no workload can alert on its device
  logs.
- **Rules alert only.** Recording rules, which write results back into the store, are not offered:
  a tenant's vmalert holds the read token only.

**Evaluation.**
- **Each tenant's rules are evaluated by that tenant's own vmalert instance, using the tenant's own
  read token.** This is the central choice. What a tenant's rule can read is limited by vmauth, not
  by the rule's text. A rule that tries another tenant's data gets the tenant's own partition or a
  refusal, never the other tenant's data. That is why the open-source *"separate `vmalert` instance
  per each tenant"* is chosen over one instance with `extra_label` per group: the label is text the
  rule sits beside, while the token is a boundary.
- **Each tenant's vmalert stamps a `tenant` label** that the substrate sets on the command line.
  Alertmanager routes on that label.

**Routing and delivery.**
- **One Alertmanager on `obs`.** Its routes are generated by the substrate, and each tenant's
  alerts go to that tenant's receivers only.
- **ntfy runs on `obs` as the notification service**, at `ntfy` on 443 through the service proxy,
  with `auth-default-access: deny-all`.
  - Each tenant gets an ntfy user that can read its own topic prefix only. ntfy supports that
    directly: *"a wildcard pattern that matches any number of topics (e.g. alerts_\* or ben-\*)"*.
  - The API issues that user with the tenant's other credentials.
  - Only Alertmanager publishes.
- **Tenant receivers are ntfy topics only.** A webhook to a URL the tenant chooses would make the
  substrate send HTTP requests to arbitrary destinations of the tenant's choosing, from a host on
  Platform. Email needs an outbound relay the site doesn't have.
- **Notifications reach phones on site only.** A phone subscribes from a network that reaches
  Platform. Off site, nothing reaches it (Open question 2).
- **A substrate fault that concerns a tenant reaches it as data, not as an alert.** The tenant sees
  its workloads' resource use (§4) and the API's events about it (ADR-0022 §4), and writes its own
  rules on them. The substrate doesn't decide what a tenant should be woken up for.

### 6. Limits are the logs'

- **A store-wide cap**, not per-tenant quotas, which are an Enterprise feature.
- **vmauth's concurrency limit per token**, as for the logs.
- **The accepted risk is the logs':** a noisy tenant can shorten everyone's history.

### 7. Built in three steps

| Step | What a tenant gets | Change |
|---|---|---|
| **A** | The store: push metrics, read them in Grafana and through the Prometheus API (§1 to §3) | [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/) |
| **B** | Alerting: rules over metrics and logs, delivered through ntfy (§5) | not yet opened |
| **C** | Each workload's resource use, published to `(index, 1)` (§4) | not yet opened |

---

## Consequences

**Tenants can be told, not just shown.** A device that goes quiet or a workload that fills its disk
becomes a notification on a phone.

**`obs` carries more than any other service VM on the management hypervisor:**
- vmauth
- VictoriaLogs
- vminsert, vmselect and vmstorage
- Grafana and the downloads site
- Alertmanager
- ntfy
- one vmalert per tenant

**Tenant alerting shares `obs`'s fate.** If `obs` is down, no rule is evaluated and no notification
is sent, and nothing says so. A tenant's workloads keep their unsent samples only if their own
client buffers them. Watching `obs` belongs to alerting for the operator, which is outside this
record.

**A tenant's alerting costs the substrate a process.** One vmalert per tenant is cheap at today's
three tenants and would need revisiting near the 62-tenant ceiling.

**One token reaches both signals.** Revoking a tenant's read token cuts off its logs, metrics,
dashboards and alerts together, and a leaked ingest token can write junk into both stores.

**The API grows again.** It gains a metrics endpoint, the metrics data sources, an alert-rule
resource, an ntfy user per tenant, the VMID map for §4, and more that it writes on `obs`.

**Off site, nobody is told.** A tenant away from the site gets its notifications when it is back.

---

## To accept

**This record is accepted when every item below is done.**

- [x] Step A built and proven by [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/): a tenant
  workload pushes metrics and graphs them in its own Grafana organization, and each of two tenants
  is refused the other's metrics, on writes and on reads, through Grafana and directly
- [ ] Step B built and proven by its change record: a tenant's rule over metrics and a rule over
  logs each fire and reach a phone on site, a rule cannot read or label its way into another
  tenant's data, and a tenant's ntfy user is refused another tenant's topic

Step C and the open questions don't hold up acceptance. Step C is decided here and built by its own
change.

## Open questions

1. **Delivering the VMID map to the collector (step C).** Options:
   - `col` polls an operator endpoint on the API and regenerates relabel rules
   - the API writes the map to `col` over a forced command, as it does to `obs`
   - the collector reads Proxmox's `/cluster/resources` and a separate job joins it to the map

   It must not be inventory.
2. **Off-site notifications.** ntfy's `upstream-base-url` sends ntfy.sh *"only the message ID (in the
   X-Poll-ID header), and the SHA256 checksum of the topic URL"*. That wakes an iOS app, but the
   phone still has to fetch the message from the site's server, and Android connects directly. With
   no inbound path, an off-site phone needs a VPN back to the site or an outbound relay. The other
   choice is to publish to a hosted service, which sends alert content off site.

## What would reopen this

- **The tenant count nearing the per-tenant vmalert cost**, which is the case for vmalert
  Enterprise's `-clusterMode` or Mimir.
- **A noisy tenant shortening everyone's history**, which is the case for per-tenant limits.
- **Substrate metrics wanted in the same store**, which reopens the scope.

## To confirm when building

- That vmauth maps a tenant's plain Prometheus paths to its own `/insert/<index>:0/` and
  `/select/<index>:<project>/`, and refuses a tenant token on another tenant's paths and on
  `/select/multitenant/`.
- That the store answers on the current vendor documentation's flags and paths, checked then, not
  from this record.
- That vmalert evaluates LogsQL rules through vmauth, in the same instance as metrics rules, with
  the tenant's read token. If not, rules over logs move to a later version and step B ships metrics
  rules only.
- That a tenant rule cannot override the `tenant` label vmalert stamps.
- What the Proxmox External Metric Server, or `/cluster/resources`, actually gives for a guest, and
  with which tags. The API's `/cluster/resources` documents per-guest `vmid`, `cpu`, `mem`,
  `diskread`, `diskwrite`, `netin` and `netout`.

---

## Current state

*Updated 2026-11-14.* Nothing this record decides is built. `dv02obs001v01` runs the log store,
vmauth, Grafana and the downloads site
([ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/),
[ADR-0024](/docs/architecture/decisions/platform-services/0024-dashboards/)). `dv02col001v01` is
built and runs only sshd.

- **Proposed.** Step A is planned in [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/).
- No metrics store, alert rule or notification service exists.
