---
title: "Tenant Platform Services"
bookCollapseSection: true
weight: 3
value: [product-not-plumbing]
waypoints:
  - title: "The first services for tenants: Wi-Fi keys, device registry, MQTT broker, logs, a dev network, dashboards, downloads"
    added: "2026-09-24"
    status: done
    date: "2026-09-24"
  - title: "Fixed addresses for tenants' devices (CHG-0044)"
    added: "2026-10-07"
    status: done
    date: "2026-10-07"
  - title: "Services for tenants reachable on port 443, by name (CHG-0046)"
    added: "2026-10-10"
    status: done
    date: "2026-10-10"
  - title: "Tenants keep their runtime secrets in an OpenBao namespace of their own (CHG-0067)"
    added: "2026-11-14"
    status: done
    date: "2026-11-14"
  - title: "Object storage for tenants: Terraform state on a VM of its own, and S3 buckets with quotas and keys (CHG-0068, CHG-0069)"
    added: "2026-11-14"
    status: done
    date: "2026-11-14"
  - title: "Resource quotas, so one tenant's workloads cannot use up a tenant hypervisor"
    added: "2026-11-15"
    status: active
  - title: "Tenants can work from Windows laptops (CHG-0058)"
    added: "2026-11-07"
    status: done
    date: "2026-11-07"
---

# Tenant Platform Services

What the site offers each tenant once it exists: Wi-Fi keys, a device registry, MQTT, logs,
dashboards, downloads, fixed addresses and services by name, and what is still to come. Metrics,
alerts and each workload's resource use are
[Tenant Observability](/docs/roadmap/infrastructure/tenant-services/observability/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/plan/)
