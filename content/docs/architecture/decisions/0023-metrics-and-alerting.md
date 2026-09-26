---
title: "ADR-0023: Metrics and Alerting"
weight: 23
---

# ADR-0023: Metrics Are Pulled From Management, Stored Beside the Logs, and Alerted On Per Tenant

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21 |
| **Scope** | How substrate and tenant metrics are collected and stored, who may read them, how alert rules are declared and evaluated for the substrate and for each tenant, and where notifications go. Dashboards only as far as needed to read what is stored. |
| **Extends** | [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/). Metrics use its store host, its authenticating proxy, its partition scheme and its tenant credentials. |
| **Extended by** | [ADR-0024: Dashboards](/docs/architecture/decisions/0024-dashboards/): saved dashboards in Grafana, one organization per tenant *(Proposed)* |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/) §5, [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/0018-operator-access-to-tenants/) |

---

## Context

### Nothing is measured and nothing alerts

- **The substrate has no metrics and no alerts.** The operator learns about a fault when a tenant's
  apply times out or a page stops loading.
- **Both observability VMs are still empty.** `dv02sob001v01` is on management and
  `dv02tob001v01` is on Platform. Both are being replaced: `tob` by the store `dv02obs001v01`, and `sob`
  by the collector `dv02col001v01` ([CHG-0018](/docs/changes/2026/0018-central-log-store/), naming
  §3.4). The rest of this record uses the new names.
- **Tenants were promised more than they have.** The tenant pages promise *"VM resource
  utilization"*, *"Per-tenant thresholds"* and *"Tenant-specific notification channels"*. None of
  it exists.

### What is wanted

1. **Substrate metrics**: every host, hypervisor and service, plus the router, switch and access
   point.
2. **Tenant metrics**: what a tenant's workloads emit, and the resource use of those workloads as
   the hypervisor sees it.
3. **Operator alerts** on the substrate.
4. **Tenant alerts**: a tenant declares its own rules and where they notify, and nobody edits
   substrate code for it.
5. **The same partitioning as the logs.** A tenant reads and alerts on its own data only.

### Where ADR-0022 left collection

ADR-0022 moved log *storage* to Platform because every zone with something to log can push there.
For metrics, pull is the norm: the collector scrapes each target. ADR-0013 §5's reasoning applies
to that directly. **Management reaches every zone, so a scraper on management reaches every
target.** A scraper on Platform would need new rules into management and IoT Backend.

---

## Options considered

### Topology

| Option | Collection | Storage | Verdict |
|---|---|---|---|
| **A — `col` scrapes, `obs` stores** | pull, from management | on Platform, beside the logs | **Chosen** |
| B — Everything pushes to `obs` | every host runs a push agent with a credential | on Platform | Rejected: a credential on every substrate host, and pushing from Platform-reachable hosts only moves the scrape problem into each host |
| C — Two stores, as ADR-0013 §5 has it | pull, from management | substrate on `col`, tenants on `obs` | Rejected for the reasons ADR-0022 gave for logs: two stacks, and no path from the substrate's store to what a tenant should see |

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
- **Its URLs match the log store's partitions.** `accountID:projectID` in a path is the same pair
  VictoriaLogs uses, so vmauth maps one token to both.
- **Operator queries across tenants are supported:** *"`vmselect` can execute queries over multiple
  tenants via special `multitenant` endpoints"*. This closes for metrics what ADR-0022's Open
  question 1 leaves open for logs.
- **Mimir** would work, but it needs its own proxy and object storage, and it is heavier. Its one
  unique feature is a multi-tenant Alertmanager (§4 addresses that).
- **Prometheus alone** has no tenancy.

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

**Option A: `col` scrapes, `obs` stores.** The store is a VictoriaMetrics cluster behind ADR-0022's
vmauth. vmalert runs once per partition owner, Alertmanager routes, and ntfy on Platform delivers.

### 1. Collection: `col` scrapes the substrate

- **vmagent on `dv02col001v01` scrapes every substrate target** and remote-writes to `obs` through
  vmauth, using the substrate's ingest token.
  - Management reaches every zone, so this needs no new zone rule.
  - `col` → `obs` uses the existing `management -> platform` rule.
- **vmagent buffers to disk while `obs` is unreachable:** *"If the remote storage is unavailable, the
  collected metrics are buffered at `-remoteWrite.tmpDataPath`"*. An outage of the store loses no
  samples, up to the buffer's size.
- **Sources:**

  | Source | How |
  |---|---|
  | Fedora VMs, the Builder | `node-exporter` (Fedora package), and `prometheus-podman-exporter` on container hosts |
  | Proxmox hypervisors | the External Metric Server, InfluxDB protocol, sent to vmagent on `col` (both on management) |
  | Core router | `os-node_exporter`, from the official OPNsense plugins |
  | Switch, access point | SNMP, enabled in the Omada controller, scraped through an SNMP exporter on `col` |
  | OpenBao | `/v1/sys/metrics` in Prometheus format |
  | PowerDNS, VerneMQ, MinIO | each service's own Prometheus endpoint |
  | The Deevnet API, PostgreSQL | an instrumented `/metrics`, and `postgres_exporter` |

- **Every exporter on a Platform or IoT Backend host admits only `col`.** Tenants can reach Platform,
  and zone policy admits segments, not services. So each exporter listens on its host's address
  behind a host firewall rule for `col`'s address alone. This is the same host-policy control as
  ADR-0022's syslog listener.
  - Several services bind their metrics to localhost by default (VerneMQ, PowerDNS). Each role
    changes that deliberately.

### 2. Storage: a VictoriaMetrics cluster on `obs`, partitioned as the logs are

- **vminsert, vmselect and vmstorage run as containers on `dv02obs001v01`**, bound to loopback, with
  vmauth as the only listener. Data goes on the same data disk as the logs.
- **The partitions are ADR-0022's:**
  - `(0, 0)` is the substrate
  - `(index, 0)` is what the tenant ships
  - `(index, 1)` is what the substrate publishes about the tenant
- **Tenants push, and `col` never scrapes a tenant workload.**
  - ADR-0018's route would let it, but that route is operator access, and ADR-0018 says it is not a
    delivery path.
  - Scraping would also make substrate configuration track tenant workloads, which ADR-0010 forbids.
  - A tenant ships with any Prometheus remote-write, OTLP or InfluxDB client through vmauth.
- **No new tenant credentials.** ADR-0022's ingest token gains write on the metrics paths for
  `(index, 0)`, and its read token gains read on `(index, 0)` and `(index, 1)`. A tenant still has
  two tokens, and they now cover both signals.

### 3. The substrate publishes each workload's resource use

- **Requirement 2's hypervisor view is published, not shared,** the same way ADR-0022 publishes
  events.
  - Proxmox reports each guest's CPU, memory, disk and network against its VMID.
  - The API knows which tenant owns each VMID (ADR-0015).
  - The substrate relabels each guest's series with the tenant's workload name and writes it to that
    tenant's `(index, 1)`.
- **A tenant sees its own workloads' resource use and nothing else of the hypervisor's.** It can't
  see the node, the other tenants, or how full the storage is.
- **How the VMID-to-tenant map reaches vmagent is open** (Open question 2). What is decided is that
  it comes from the API, never from inventory, since a tenant must not need a substrate commit.

### 4. Alerting: vmalert per partition owner, one Alertmanager, ntfy on Platform

**Evaluation.**
- **The substrate's rules live in substrate code** and are evaluated by one vmalert with the
  operator's read token. They cover `(0, 0)`, and span tenants through the multitenant endpoint where
  a rule needs to.
- **Each tenant's rules are declared through the Deevnet API**, as a new provider resource. The API
  writes them to `obs` over the same forced-command path ADR-0022 uses for vmauth.
- **Each tenant's rules are evaluated by that tenant's own vmalert instance, using the tenant's own
  read token.** This is the central choice. What a tenant's rule can read is limited by vmauth, not
  by the rule's text. A rule that tries another tenant's data gets the tenant's own partition or a
  refusal, never the other tenant's data. That is why the open-source *"separate `vmalert` instance
  per each tenant"* is chosen over one instance with `extra_label` per group: the label is text the
  rule sits beside, while the token is a boundary.
- **Each tenant's vmalert stamps a `tenant` label** that the substrate sets on the command line.
  Alertmanager routes on that label.

**Routing and delivery.**
- **One Alertmanager on `obs`.** Routes are generated by the substrate: operator alerts go to the
  operator's receivers, and each tenant's alerts go to that tenant's receivers only.
- **ntfy runs on `obs` as the notification service**, with `auth-default-access: deny-all`.
  - The operator subscribes from trusted or management, and tenants from tenant transit. Both reach
    Platform.
  - Each tenant gets an ntfy user limited to its own topic prefix. ntfy supports that directly: *"a
    wildcard pattern that matches any number of topics (e.g. alerts_\* or ben-\*)"*.
  - The API issues that user with the tenant's other credentials.
- **Tenant receivers are ntfy topics only in v1.** A webhook to a URL the tenant chooses would make
  the substrate send HTTP requests to arbitrary destinations of the tenant's choosing, from a host on
  Platform. That is left out until it is scoped.
- **A substrate fault that concerns a tenant reaches it as data, not as an alert.** The tenant
  already sees its workloads' resource use (§3) and the API's events about it (ADR-0022 §4), and
  writes its own rules on them. The substrate doesn't decide what a tenant should be woken up for.

### 5. Retention and dashboards

- **One retention period for the metrics store.** Per-tenant retention is an Enterprise feature.
  Tenant cardinality limits are Open question 4.
- **vmui is the reading surface in v1.** It is served per tenant through vmauth for tenants, and
  across tenants for the operator. Saved dashboards (Grafana, one organization per tenant) are
  deferred.

---

## Consequences

**The site can alert on itself.** Faults become notifications instead of discoveries.

**`obs` becomes the site's busiest management-hypervisor VM.** It carries:
- vmauth
- VictoriaLogs
- vminsert, vmselect and vmstorage
- Alertmanager
- ntfy
- one vmalert per tenant

The 2 GB it was built with is unlikely to be enough, and sizing it is To confirm. `col` stays small:
vmagent and an SNMP exporter.

**Alerting shares the fate of what it watches.** If `obs` is down, there are no evaluations and no
notifications, and nothing says so. vmagent on `col` keeps its samples, but no alert fires about the
outage itself. This is the gap in the design (Open question 1).

**Every exporter is a firewall rule on its host.** A new service with metrics is not finished until
its exporter admits only `col`.

**A tenant's alerting costs the substrate a process.** One vmalert per tenant is cheap at today's two
tenants and would need revisiting near the 62-tenant ceiling.

**The API grows again.** It gains an alert-rule resource, an ntfy user per tenant, the VMID map for
§3, and one more file it writes on `obs`.

**Off-site notifications don't work yet.** ntfy on Platform notifies phones on site. Off-site, the
phone needs a path back to the site, which is Open question 3.

---

## Open questions

1. **Who watches the watcher?** Something outside `obs` has to notice when `obs` stops.
   - The candidate is a heartbeat alert that fires constantly, with its absence detected on `col`.
   - `col` can't send through `obs`'s ntfy, because that is what failed, so the check needs a second
     delivery path. One option is a small operator-only notifier on `col` itself: the operator's phone
     on trusted can reach management, and tenants can't. The other is to send that one heartbeat
     through a hosted service, which reveals only that the site is down.
2. **Delivering the VMID map to vmagent.** Options:
   - `col` polls an operator endpoint on the API and regenerates relabel rules
   - the API writes the map to `col` over a forced command, as it does to `obs`
   - vmagent reads Proxmox's `/cluster/resources` and a separate job joins it to the map

   It must not be inventory.
3. **Off-site notifications.** ntfy's `upstream-base-url` sends ntfy.sh *"only the message ID (in the
   X-Poll-ID header), and the SHA256 checksum of the topic URL"*. That wakes an iOS app, but the
   phone still has to fetch the message from the site's server, and Android connects directly. With
   no inbound path, an off-site phone needs a VPN back to the site or an outbound relay. The other
   choice is to publish to a hosted service, which sends alert content off-site.
4. **Tenant limits.** Series cardinality, samples per second and rule count per tenant. vmauth can
   rate-limit per token; whether that is enough is to be confirmed.
5. **Should vmalert write recording-rule results back to the tenant's `(index, 0)`?** If so, the
   tenant's vmalert needs the ingest token as well.

## What would reopen this

- **The tenant count nearing the per-tenant vmalert cost**, which is the case for vmalert Enterprise's
  `-clusterMode` or Mimir.
- **A tenant needing saved dashboards**, which brings in Grafana and its per-organization model.

## To confirm when building

- That a VictoriaMetrics cluster and VictoriaLogs together fit a resized `obs`, and what it needs.
- That vmauth refuses a tenant token on another tenant's `/select/<accountID>:<projectID>/` and on
  `/select/multitenant/`.
- That a tenant rule cannot override the `tenant` label vmalert stamps.
- What the Proxmox External Metric Server actually sends for a guest, and with which tags. The vendor
  page says only that it reports *"various stats about your hosts, virtual guests and storages"*. The
  API's `/cluster/resources` documents per-guest `vmid`, `cpu`, `mem`, `diskread`, `diskwrite`,
  `netin` and `netout`.
- That the OPNsense `os-node_exporter` plugin and Omada SNMP work on the installed versions. Check
  each against its current documentation, not memory.

---

## Current state

- **Proposed. Nothing is built.** Both observability VMs run only sshd.
- No exporter is installed anywhere.
- No alert exists.
