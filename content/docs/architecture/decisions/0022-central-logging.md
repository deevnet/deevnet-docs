---
title: "ADR-0022: Central Logging"
weight: 22
---

# ADR-0022: One Central Log Store on Platform, Partitioned by Tenant

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21 |
| **Scope** | Where substrate and tenant logs are sent and kept, how they are partitioned, who may read which partition, and which substrate events a tenant sees. Logs only: metrics and alerting are left for their own records. |
| **Supersedes, in part** | [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/) §5, **for logs only**. That section splits observability into a substrate store on management and a tenant store on Platform. For logs there is now one store, on Platform. Everything else in ADR-0013 stands, including both VMs. |
| **Extended by** | [ADR-0023: Metrics and Alerting](/docs/architecture/decisions/0023-metrics-and-alerting/): metrics use the same store host, proxy, partitions and tenant tokens *(Proposed)*. [ADR-0024: Dashboards](/docs/architecture/decisions/0024-dashboards/): tenants read their logs in Grafana, one organisation per tenant *(Proposed)* |
| **Built by** | [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/) (the store and substrate shipping, *Planned*); tenant tokens follow in a later record |
| **Related** | [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/), [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/), [ADR-0021: Tenant Secrets](/docs/architecture/decisions/0021-tenant-secrets/) |

---

## Context

### Nothing collects logs today

- **CHG-0008 built both observability VMs empty.** `dv02sob001v01`, on management, is for the
  substrate. `dv02tob001v01`, on Platform, is for tenants. Each runs only sshd, and CHG-0008's
  follow-up *"Observability tooling for `dv02sob001v01` and `dv02tob001v01`"* is still open.
- **Every host keeps its own journal.** Reading across the site means an SSH session per host, and
  the core router's log buffer holds about fifty seconds.
- **Tenants have nothing at all.** The tenant pages promise logs *"Tagged with tenant identifier"*,
  *"Queryable by tenant scope"* and *"Retained per tenant policy"*, and the shared-services table
  lists tenant observability as *"To be defined"*.

### What is wanted

1. **One place for all logs.** Tenants ship their workloads' logs there, and so do substrate
   hosts and services.
2. **Partitioned by tenant.** Each tenant reads its own logs and never another tenant's.
3. **A tenant also sees the substrate events that concern it.** Examples: the API creating its
   workload, a DNS update to its zone, a broker refusing one of its accounts. It should not have to
   ask the operator.
4. **The operator reads everything.**

### What the zone policy allows

ADR-0013 §5 put substrate observability on management. That followed from the zone policy: IoT
Backend and Platform can't reach management, so a store there has to *pull*. That is still true.
What ADR-0013 didn't weigh is the reverse.

**Platform is reachable from every zone that has something to log:**

| Source | Rule, already declared |
|---|---|
| Management hosts, including the hypervisors and `sob` | `management -> platform` |
| The operator, from trusted | `trusted -> platform` |
| Tenant workloads | `tenant_transit -> platform` |
| The broker on IoT Backend | `iot_backend -> platform` |
| The API, OpenBao, tenant DNS | already on Platform |

**Management is reachable only from trusted.**

So one store on Platform receives from everything by push, with no new zone rule. A store on
management can reach tenants only if tenants gain a path toward management, which the segmentation
standard forbids.

### The precedent for tenant-reachable substrate data

OpenBao sits on Platform and is *"Reachable from tenant transit. The control is its authentication
and policies, not the network"* (ADR-0016 §1). It holds every substrate runtime credential. Substrate
logs are less sensitive than that, so a log store on the same terms is no new exposure in kind.

---

## Options considered

### Where

#### A — Two stores, as ADR-0013 §5 has it

- **For:** substrate logs never sit on a segment tenants can reach.
- **Against:**
  - Two stacks to run.
  - The store on management has to pull from Platform and IoT Backend.
  - Requirement 3 can't be met without a path from management's store to Platform's. That path is
    either a relay or a copy, which is a third mechanism.
- **Verdict:** Rejected.

#### B — One store on management, a relay on Platform

- **For:** substrate logs stay on management.
- **Against:**
  - Tenants can write through the relay but have no way to read their own logs back, unless a
    second read path is built through it.
  - It relocates A's cost rather than removing it.
- **Verdict:** Rejected.

#### C — One store on Platform *(chosen)*

- **For:**
  - Everything reaches it with the rules that exist today.
  - One stack, one retention policy, one query surface.
  - The same stance OpenBao already takes.
- **Against:**
  - Substrate logs sit on a segment tenants can reach, so protecting them is up to authentication
    and the store's partitioning. See Consequences.

### What

Vendor documentation was checked on 2026-09-21. Quotes are from the vendor's own pages.

| | OpenSearch + Logstash | Elasticsearch + Kibana + Logstash | Loki + Grafana + Alloy | VictoriaLogs + vmauth |
|---|---|---|---|---|
| **License** | Apache 2.0 | ELv2, SSPL or AGPLv3 | AGPL-3.0-only | Apache 2.0 |
| **Tenant partition** | index permissions, document-level security | index permissions; document-level security is paid | `X-Scope-OrgID` | `(AccountID, ProjectID)` |
| **Authenticates callers itself** | yes | yes | no | no |
| **Receives syslog or journald with no collector** | no | no | no | **yes, both** |
| **Fits the 2 GB VM** | no | no | probably | yes |

- **OpenSearch and Logstash don't fit.** Logstash's own guidance: *"The recommended heap size for
  typical ingestion scenarios should be no less than 4GB and no more than 8GB."* OpenSearch
  recommends *"half of system RAM"* for its own heap. It is the only free candidate with
  **document-level security**, which could show a tenant a filtered view of a shared substrate index.
  Its Logstash output plugin officially lists compatibility with Logstash 7.13.2 only.
- **Elasticsearch** puts document-level security behind a paid subscription. Without it, a tenant
  can be scoped only per index.
- **Loki** fits and is well known. However:
  - *"Grafana Loki does not come with any included authentication layer. You must run an
    authenticating reverse proxy in front of your services."*
  - It can't receive syslog or journald itself, so every host needs Alloy or another collector.
  - Free Grafana has no data-source permissions: *"data sources in an organization can be queried by
    any user in that organization"*. Isolating tenants in the UI therefore means one Grafana
    organisation per tenant.
- **VictoriaLogs** fits and takes RFC 5424 syslog over TLS and `systemd-journal-upload` natively. A
  substrate host therefore needs no new agent: rsyslog and journal-upload are distribution packages.
  However:
  - *"VictoriaLogs doesn't perform per-tenant authorization. Use vmauth or similar tools"*. That is
    the same shape as Loki.
  - mTLS on vmauth and on the syslog listener is Enterprise-only.
  - Its documentation does not say whether one query can span tenants.

**Logstash specifically was considered.** It can authenticate ingest, using basic auth per input or
TLS client certificates on the beats input, and route by certificate subject. But it is a JVM that
wants 4 GB on its own, it is an ingest tier only, and every backend it pairs with is also too large
for this hardware.

---

## Decision

**Option C, with VictoriaLogs behind vmauth, on `dv02tob001v01`.**

### 1. One store, on Platform

- **VictoriaLogs and vmauth run as containers on `dv02tob001v01`**, in the pattern ADR-0013 set.
- **vmauth is the only listener tenants can reach.** VictoriaLogs' own HTTP port is bound to the
  loopback interface.
- **Logs live on a data disk, not the OS disk**, as the provisioning VM's data needs (ADR-0014).
- **`dv02sob001v01` keeps its place for pull-based collection** such as metrics, which a later record
  decides. It stores no logs.

### 2. Partitions follow the tenant index

VictoriaLogs partitions by `(AccountID, ProjectID)`. The numbering comes from the one number every
tenant identifier already derives from (ADR-0002):

| AccountID | ProjectID | Holds | Written by | Read by |
|---|---|---|---|---|
| `0` | `0` | substrate logs: hosts, services, network devices | substrate hosts | operator |
| *tenant index* | `0` | what the tenant ships from its workloads | the tenant | the tenant, operator |
| *tenant index* | `1` | substrate events **about** the tenant (§4) | the substrate only | the tenant, operator |

- **Index 0 is never a tenant.** The API allocates tenant indexes from 1 to 62 (ADR-0015); 63 is the drill index, which gets a partition like any other.
- **The ProjectID split is what makes the substrate's slice trustworthy.** A tenant's ingest
  credential is pinned to ProjectID `0`, so a tenant can't write into its own ProjectID `1`. What
  it reads there came from the substrate.

### 3. Credentials: vmauth sets the partition, never the caller

- **Every request is authenticated by vmauth with a bearer token.** vmauth then sets `AccountID`
  and `ProjectID` itself. A header the caller sends is never trusted.
- **Every vmauth user sets both headers, always.** VictoriaLogs' own default is the substrate
  partition: *"By default the (AccountID=0, ProjectID=0) tenant is queried."* A user entry that
  forgets the headers therefore fails **open, into substrate logs**, not closed. vmauth replaces a
  caller's header of the same name rather than adding to it (`dst.Set` in `app/vmauth/main.go`,
  `updateHeadersByConfig`), so a configured user cannot pick another partition.
- **Each tenant has two tokens:**
  - an ingest token, which may write only to `(index, 0)`
  - a read token, which may read `(index, 0)` and `(index, 1)` and nothing else
- **One read token reaches two partitions through `url_map`.** vmauth can set headers per
  `url_map` entry, not only per user. The read user has exactly two entries, one per ProjectID, and
  no `default_url`, so a request that matches neither is refused. The tenant's Grafana organisation
  (ADR-0024) holds two datasources with the same token: one for its own logs, one for the substrate's
  events about it.
- **The API issues both when it creates the tenant**, like every other tenant credential
  (ADR-0015). They are returned in the create response, kept in tenant state, and restorable from it
  (ADR-0012 §4). A workload receives its ingest token through ADR-0021 once that exists.
- **The API writes vmauth's configuration.** The path is the one CHG-0016 used for broker accounts:
  a forced SSH command on `tob`, reached by one narrow rule from the provisioning VM. No substrate
  commit per tenant, as ADR-0010 requires.
- **Each substrate host has its own ingest token**, which writes only `(0, 0)`. One host's token
  can be revoked without touching the others, and a forged line traces to the token that sent it.
  An operator read token covers every partition. All of them are kept in the inventory vault, as
  the broker's service credentials are (CHG-0015).

### 4. The substrate publishes to tenants; nothing filters substrate logs

**Requirement 3 is met by writing, not by filtering.** When a substrate service has an event that
concerns a tenant, it writes the event twice:
- once to `(0, 0)`, like any substrate log
- once to that tenant's `(index, 1)`, as a curated event: what happened, when, and to which of the
  tenant's objects

The alternative is to filter a shared substrate partition at query time, which is document-level
security. It was not chosen, for two reasons:
- **A filter is a leak waiting for one bad query.** A tenant's view would be the substrate's whole
  log minus whatever the filter caught. Publishing makes it *nothing, plus what was deliberately
  written*.
- **Publishing is the platform-service pattern the site already uses.** The substrate writes a
  tenant's zone delegation and its broker account, and it writes the tenant's log events the same
  way.

**v1 publishes only what the Deevnet API emits.** The API already knows which tenant every request
concerns: creates, deletes, resupplies, backend failures. Services the site doesn't write, such as
PowerDNS and VerneMQ, log only to `(0, 0)` until something maps their events to a tenant. That is
a collector's job, and it is left open (Open question 3).

### 5. How each source ships

| Source | Mechanism | Credential |
|---|---|---|
| Substrate hosts: Fedora domain VMs | `systemd-journal-upload` over HTTPS to vmauth; `Header=` needs systemd 258+, and the domain VMs run 259 (Fedora 44, checked 2026-09-21) | that host's own ingest token |
| Substrate hosts: hypervisors | syslog over TLS to the listener fixed to `(0, 0)`. `dv02hyp001p01` runs Debian 12 with systemd 252, which has no `Header=`, so journal-upload cannot carry a token | none; the same host firewall rule as the network devices |
| The Builder | **ships nowhere.** It roams, belongs to no site, and keeps its own journal | — |
| Core router, switch, access point | RFC 5424 syslog to a dedicated VictoriaLogs listener fixed to `(0, 0)` | none, so the listener is limited by a host firewall rule to those devices' addresses |
| The Deevnet API | its own logs through the journal; tenant events as JSON lines through vmauth (§4) | its host's ingest token |
| Tenant workloads | the tenant's choice: journal-upload, syslog via a collector, or any JSON or OTLP shipper, through vmauth | the tenant's ingest token |

**The syslog listener is the one unauthenticated path.** A tenant can reach Platform, so it can
reach that port. Zone policy can't narrow this, because zone policy admits segments, not services
(standards, *Reachability and Permission*). The host firewall on `tob` admits only the network
devices' and hypervisors' addresses. That is the same split between zone policy and host policy that
the broker's SSH port already relies on.

**So the listener must be a host listener, not a published container port.**
[CHG-0016](/docs/changes/2026/0016-broker-accounts/) measured that a firewalld rule does not filter a
published podman port: publishing is DNAT plus forward, and the packet never reaches the INPUT chain
the rule sits on. VictoriaLogs and vmauth therefore run with **host networking**. That makes the syslog
port a host listener that firewalld does filter, and it binds VictoriaLogs' HTTP port to `127.0.0.1`
literally.

### 6. Retention

- **One retention period for the whole store.** VictoriaLogs' retention is per store: *"The
  retention can be configured with -retentionPeriod command-line flag."* Per-tenant quotas appear
  only on the vendor's roadmap, as Enterprise.
- **A disk cap as well as a time cap.** `-retention.maxDiskUsagePercent` drops the oldest data when
  the disk passes the threshold, so a full disk shortens history instead of stopping ingest.
- **A concurrency cap per tenant ingest token.** vmauth's `max_concurrent_requests` is set on each
  tenant's ingest user; *"vmauth responds with 429 Too Many Requests HTTP error when the number of
  concurrent requests exceeds the configured limits"*. This limits concurrency, not bytes: it slows
  a noisy tenant down, it doesn't stop one.
- **Logs are kept data but not authoritative data.** Nothing is re-derived from them, and losing
  them loses history, not state. They get a data disk and no off-host copy. Revisit if a log ever
  becomes evidence something depends on, such as the API's audit trail (ADR-0014).

---

## Consequences

**The site has central logs, and tenants have logs at all.** One place to look during an incident,
instead of an SSH session per host and a fifty-second router buffer.

**Substrate logs sit on a segment tenants can reach.** Their protection is vmauth's token check and
the partition it assigns. A defect in vmauth's configuration, or in how the API writes it, can expose
substrate logs to a tenant or one tenant's logs to another. This is accepted on the same terms as
OpenBao, and it puts a rule on the substrate: **a secret never goes into a log**, because the store
is not a secret store.

**The API writes one more backend**, and gains the tenant's log tokens as issued secrets, with the
same resupply behaviour as the others.

**A noisy tenant can shorten everyone's history.** The store's limits are one disk cap and one
retention period, shared by all. A tenant that ships heavily, within its concurrency cap, pushes
the oldest data of every partition out sooner. This is accepted for v1 and revisited when
VictoriaLogs has per-tenant quotas, or if it happens.

**The operator reads one partition at a time.** VictoriaLogs has no query that spans tenants: its
roadmap lists *"Multitenant querying: an endpoint that reads across tenants and returns per-row
tenant fields"*, not yet released. The operator's Grafana organisation has a datasource per
partition. The API's tenant events land in `(0, 0)` as well, so the substrate's own view is complete
without crossing tenants.

**A tenant sees what the API did to it, and nothing else of the substrate's.** That is less than
document-level security could show. It is deliberately less, and it grows only by publishing more.

**Every substrate host needs one package and one config file.** The package is
`systemd-journal-remote`, which carries journal-upload on Fedora. It is not installed on the Builder
today.

**The segmentation reasoning in ADR-0013 §5 is narrowed.** Substrate logs are pushed to Platform,
not pulled to management. For whatever `sob` collects later, the pull model still holds.

**VictoriaLogs is a smaller project than Loki or OpenSearch.** It is swappable: every ingest path
here is a standard protocol, and only the partition headers are specific to it.

---

## Open questions

None remain open. The six this record was proposed with were answered on 2026-09-21. Two of them are
deliberate deferrals, not settled designs.

Vendor documentation was re-checked the same day, against VictoriaLogs v1.52.0.

| # | Question | Answer |
|---|---|---|
| 1 | Can the operator query across tenants? | **No: one partition at a time.** VictoriaLogs has no cross-tenant query; it is on the vendor's roadmap, unreleased. The API's tenant events already land in `(0, 0)`, so the substrate view needs no copy. Revisit when multi-tenant querying ships. See Consequences. |
| 2 | Tenant UI | **Grafana, one organisation per tenant**, as [ADR-0024](/docs/architecture/decisions/0024-dashboards/) decides. The `victoriametrics-logs-datasource` plugin sets `AccountID` and `ProjectID` per datasource, and vmauth overwrites them from the token regardless. No UI is built with the store. |
| 3 | Third-party services' tenant events | **Deferred.** v1 publishes only the API's events. A collector that maps PowerDNS and VerneMQ lines to a tenant gets its own record, and only once those lines are shown to identify the tenant reliably. |
| 4 | Per-tenant retention and quotas | **A disk cap and a concurrency cap; no per-tenant quota.** VictoriaLogs has none: per-tenant quotas are on its roadmap as Enterprise. §6 sets the store's disk cap and a `max_concurrent_requests` per tenant ingest token. The residual risk is accepted; see Consequences. |
| 5 | Workload identity | **Deferred: one ingest token per tenant in v1.** Per-workload tokens, allowing per-workload revocation, wait for ADR-0021's delivery path. |
| 6 | The Builder | **Ships nowhere.** It roams and belongs to no site (§5). |

## What would reopen this

- **A need to show tenants a filtered view** of logs the substrate doesn't write itself, at a scale
  publishing can't keep up with. That is the case for document-level security, and a larger host.
- **An incident where substrate logs reached a tenant.** Option A's separation would then be worth
  its cost.

## To confirm when building

- That vmauth overwrites a caller-supplied `AccountID` and `ProjectID` once `headers` sets them.
  **Confirmed in the source** (`dst.Set`, above). It still needs a live negative test, from a tenant
  segment, before anything depends on it.
- That a `url_map` entry with no match, and no `default_url`, is refused rather than routed to
  `(0, 0)`.
- That `systemd-journal-upload` with `Header=` on Fedora 44 (systemd 259) delivers into the right
  partition through vmauth.
- That a VictoriaLogs syslog listener can be fixed to `(0, 0)` with `-syslog.tenantID.tcp`, and that
  the core router, switch, AP and hypervisors can send to it. Check each device's syslog options
  against its current manual, not from memory.
- That the syslog port under host networking is filtered by firewalld, measured from a source that
  is not allowed, as CHG-0016 measured it.
- The systemd version on `dv02hyp002p02`. Only `dv02hyp001p01` was checked.
- That VictoriaLogs and vmauth run in the memory `tob` is given, at a realistic ingest rate. `tob` was
  built with 2 GB before logging had requirements, and resizing it is approved.

---

## Current state

- **Proposed. Nothing is built.** The stack and partition scheme were reviewed and accepted as
  written on 2026-09-21, and every open question was answered. This record becomes Accepted when
  [CHG-0018](/docs/changes/2026/0018-central-log-store/) completes.
- `dv02tob001v01` and `dv02sob001v01` run only sshd.
- No host ships its logs anywhere.
