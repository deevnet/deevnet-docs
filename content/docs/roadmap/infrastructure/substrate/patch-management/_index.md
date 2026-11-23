---
title: "Patch Management"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/software-discovery/
  - /docs/roadmap/infrastructure/substrate/software-discovery/
  - /docs/roadmap/infrastructure/substrate/patch-awareness/
  - /docs/roadmap/infrastructure/mobile/patch-automation/
weight: 11
value: [no-surprises]
waypoints:
  - title: "The Software Catalog's rows moved into a data file that reports can compare against"
    status: done
    date: "2026-11-03"
  - title: "Deevnet's own software pinned to exact versions and licensed"
    status: done
    date: "2026-11-03"
  - title: "Installed versions collected from routers, hypervisors, VMs, network devices and Pis"
    status: planned
  - title: "Patch management v1 done: a dated report of installed versus cataloged versions, run as part of build verification"
    milestone: true
    status: planned
  - title: "Patch management v2 done: every cataloged product's releases and advisories watched, and one feed of what needs attention delivered to the operator"
    milestone: true
    status: planned
  - title: "Patch management v3 done: substrate hosts patched on a monthly cycle, in a fixed order, each with a way back"
    milestone: true
    status: planned
  - title: "Patch management v4 done: security updates applied unattended on the substrate service VMs, with what is never unattended written down"
    milestone: true
    status: planned
  - title: "Patch management v5 done: the take-home Pi and VM images rebuilt on a cadence, each stating how current it is"
    milestone: true
    status: planned
---

# Patch Management

Keeping what the substrate runs up to date, systematically. Discovery knows what is running and
compares it with the [Software Catalog](/docs/platforms/software-catalog/); watched release and
advisory sources say when it needs attention; patches go in on a monthly cycle, unattended where
that is safe; and the take-home images tenants carry away are rebuilt so they don't go stale. This
is the [Discovery](/docs/policies/lifecycle-management/discovery/) and Patch stages of Lifecycle
Management, built. What a tenant runs is the tenant's to keep current.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Patch Management](/docs/roadmap/infrastructure/substrate/patch-management/plan/)
