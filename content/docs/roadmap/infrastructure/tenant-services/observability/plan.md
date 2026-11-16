---
title: "Tenant Observability: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 4
tasks_in_progress: 0
tasks_planned: 2
---

# Tenant Observability: Project Plan

Metrics, alerts and workload resource use for tenants, built in the three steps of
[ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/). One of four
plans for the tenant platform, with
[Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/plan/),
[Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/plan/) and
[Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/plan/).

**Roadmap item:** [Tenant Observability](/docs/roadmap/infrastructure/tenant-services/observability/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Metrics, alerts and resource use 🔄

- ✅ Metrics, step A: a Prometheus-compatible store beside the logs, written and read with the
  tenant's log tokens, with a metrics data source in each Grafana organization
  ([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/),
  [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/))
- ✅ Alerting, step B: alert rules over metrics or logs, each tenant's in its own vmalert, delivered
  through ntfy to Android phones on site ([CHG-0071](/docs/changes/2026/0071-tenant-alerting/))
- ✅ The take-home Pi keeps the same metrics and alerting: the metrics store behind its vmauth,
  vmalert, Alertmanager and ntfy on the card, and rules imported from the tenant's Terraform
  ([CHG-0072](/docs/changes/2026/0072-pi-metrics-and-alerting/))
- ✅ Buckets on the take-home Pi, on silo
  ([CHG-0073](/docs/changes/2026/0073-pi-buckets/))
- ⏳ Workload resource use, step C: each workload's CPU, memory, disk and network as the hypervisor
  sees it, published to the tenant
- ⏳ Alerts that reach a phone away from the site, and on iOS (ADR-0023's open question 2): an
  ADR of its own, for where a tenant runs for real, on a take-home Pi or at the home site. The
  mobile site is for development, where alerts on site prove the rules
