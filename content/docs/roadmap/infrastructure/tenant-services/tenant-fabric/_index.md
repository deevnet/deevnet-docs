---
title: "Tenant Fabric"
bookCollapseSection: true
weight: 1
value: [fast-delivery]
waypoints:
  - title: "Tenant network architecture designed"
    status: done
    date: "2026-08-30"
  - title: "Tenants publish their own DNS names"
    status: done
    date: "2026-09-03"
  - title: "The EVPN/VXLAN tenant network running on one hypervisor, with internet access through the perimeter"
    status: done
    date: "2026-09-17"
  - title: "The core router confined to the tenant perimeter: one transit network and one route into the tenant overlay, nothing per tenant"
    value: [contained-failure]
    status: done
    date: "2026-11-12"
  - title: "Network isolation between two tenants' workloads tested"
    value: [contained-failure]
    status: planned
---

# Tenant Fabric

The network every tenant gets: an EVPN/VXLAN fabric on the tenant hypervisor, egress at the perimeter,
DNS each tenant publishes for itself, and tenants kept apart from each other.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/plan/)
