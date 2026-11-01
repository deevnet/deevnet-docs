---
title: "Tenant Fabric"
weight: 1
milestones:
  - title: "Tenant network architecture designed"
    status: done
    date: "2026-08-30"
  - title: "Tenants publish their own DNS names"
    status: done
    date: "2026-09-03"
  - title: "The EVPN/VXLAN tenant network running on one hypervisor, with internet access through the perimeter"
    status: done
    date: "2026-09-17"
  - title: "The core router reduced to the site's perimeter, no longer routing tenant traffic inside it"
    status: planned
  - title: "Tenants' servers isolated from each other"
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
