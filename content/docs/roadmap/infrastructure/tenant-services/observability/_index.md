---
title: "Tenant Observability"
bookCollapseSection: true
weight: 5
value: [product-not-plumbing]
waypoints:
  - title: "Tenants push metrics from their workloads and query them, in Grafana too, with their log tokens (CHG-0070)"
    status: done
    date: "2026-11-14"
  - title: "Tenants get alerts on their phones, on site, from their own rules over their metrics and logs (CHG-0071)"
    status: done
    date: "2026-11-15"
  - title: "Tenants see each workload's CPU, memory, disk and network as the hypervisor measures it"
    status: planned
---

# Tenant Observability

What each tenant sees of its own systems: its metrics, stored beside its logs and read with the same
tokens, and alerts from its own rules, sent to its phone on site
([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)). Still to
come: each workload's resource use, published to the tenant by the site. Logs and dashboards came
first, with [Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Tenant Observability](/docs/roadmap/infrastructure/tenant-services/observability/plan/)
