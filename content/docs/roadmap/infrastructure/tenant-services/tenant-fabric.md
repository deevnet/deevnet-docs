---
title: "Tenant Fabric"
weight: 1
milestones:
  - title: "Design tenant network architecture"
    status: done
    date: "2026-08-30"
  - title: "Tenant DNS publication"
    status: done
    date: "2026-09-03"
  - title: "The tenant fabric: single-member, egress at the perimeter"
    status: done
    date: "2026-09-17"
  - title: "The core router reduced to the perimeter"
    status: planned
  - title: "Tenants' workloads isolated from each other"
    status: planned
---

# Tenant Fabric

The network every tenant gets: an EVPN/VXLAN fabric on the tenant hypervisor, egress at the perimeter,
DNS each tenant publishes for itself, and tenants kept apart from each other.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Tenant Platform](/projects/tenant-platform/), its network architecture, fabric and DNS phases
