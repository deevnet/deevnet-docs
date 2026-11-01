---
title: "Observability: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 6
tasks_in_progress: 2
tasks_planned: 12
---

# Observability: Project Plan

Logging, metrics and alerting for the mobile site, one of three plans with the [Extended Management Plane](/docs/roadmap/infrastructure/substrate/management-plane/plan/) and [Secrets and Identity](/docs/roadmap/infrastructure/substrate/secrets-identity/plan/).

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

**Roadmap item:** [Observability](/docs/roadmap/infrastructure/substrate/observability/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

**In Scope**
- Centralized logging aggregation and search
- Metrics collection and telemetry
- Alerting and notification

**Out of Scope**
- Application-specific monitoring (handled per-tenant)

---

## Centralized Logging 🔄

One log store on Platform: VictoriaLogs behind vmauth on `dv02obs001v01`, partitioned by tenant
index. [ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/) narrowed it to **tenants
only**: the substrate's own logs are not centralized.

- ✅ Evaluate logging stack: VictoriaLogs, over Loki and Logstash with OpenSearch
  ([ADR-0022](/docs/architecture/decisions/platform-services/0022-central-logging/))
- ✅ Deploy log aggregation service ([CHG-0018](/docs/changes/2026/0018-central-log-store/)), cut to
  tenant scope ([CHG-0019](/docs/changes/2026/0019-log-store-tenant-scope/))
- ✅ Tenant ingest and read tokens, issued by the Deevnet API
  ([CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/))
- ✅ Edge-device logs over MQTT into `(index, 2)`, through the MQTT log bridge
  ([CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/))
- ✅ Deploy log visualization: Grafana OSS, one organization per tenant
  ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/))
- ✅ Define log retention and rotation ([ADR-0022](/docs/architecture/decisions/platform-services/0022-central-logging/) §6)
- Not pursued: shipping the substrate hosts' logs. CHG-0018 started it and CHG-0019 removed it
  under ADR-0027. Not counted

**Deferred from ADR-0022's v1.** Each waits on something named, rather than being unplanned:

- ⏳ Tenant events from services the site doesn't write. v1 publishes only the Deevnet API's events
  into a tenant's `(index, 1)`. A collector that maps PowerDNS and VerneMQ lines to a tenant gets its
  own record, once those lines are shown to identify the tenant reliably (Open question 3)
- ⏳ Per-workload ingest tokens, so one workload can be revoked alone. v1 issues one per tenant.
  Waits on [ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/)'s delivery path (Open
  question 5)
- ⏳ Per-tenant quotas. v1 has one disk cap and one retention period, so a noisy tenant shortens
  everyone's history. Revisit when VictoriaLogs has per-tenant quotas, or if it happens (Open
  question 4)
- ⏳ Operator queries across tenants. v1 reads one partition at a time. Revisit when VictoriaLogs
  ships multi-tenant querying (Open question 1)
- ⏳ Re-measure `obs`'s memory and disk at site volume. Measured so far at one host's volume, before
  tenants shipped

---

## Telemetry 🔄

- 🔄 Evaluate metrics stack: VictoriaMetrics cluster beside the logs, fed by vmagent, proposed in
  [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)
- ⏳ Deploy metrics collection service
- ⏳ Configure exporters on substrate hosts
- ⏳ Deploy metrics dashboards. Grafana itself is up since
  [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/); it has no metrics data sources yet
- ⏳ Define metrics retention

---

## Alerting 🔄

- 🔄 Evaluate alerting solutions: vmalert per tenant, one Alertmanager, ntfy, proposed in
  [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/). Grafana's own alerting is off
  ([ADR-0024](/docs/architecture/decisions/platform-services/0024-dashboards/))
- ⏳ Deploy alerting service
- ⏳ Define alert rules for infrastructure
- ⏳ Configure notification channels (email, webhook, etc.)
