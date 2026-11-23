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
  - title: "Patch management v1 done: installed versions collected from routers, hypervisors, VMs and network devices, in a dated report against the catalog"
    milestone: true
    status: done
    date: "2026-11-23"
  - title: "Patch management v2 done: the operator is emailed when any substrate system has an update waiting, such as a new OPNsense patch"
    milestone: true
    status: planned
  - title: "Patch management v3 done: new releases, advisories and end of life for software that can't report its own updates are emailed too"
    milestone: true
    status: planned
  - title: "Patch management v4 done: substrate hosts patched on a monthly cycle, in a fixed order, each with a way back"
    milestone: true
    status: planned
  - title: "Patch management v5 done: security updates applied unattended on the substrate service VMs, with what is never unattended written down"
    milestone: true
    status: planned
  - title: "Patch management v6 done: the take-home Pi and VM images rebuilt on a cadence, each stating how current it is"
    milestone: true
    status: planned
---

# Patch Management

Keeping what the substrate runs up to date, systematically. Discovery knows what is running and
compares it with the [Software Catalog](/docs/platforms/software-catalog/); the operator is emailed
when an update is waiting, as each system reports it and as release and advisory sources show it; patches go in on a monthly cycle, unattended where
that is safe; and the take-home images tenants carry away are rebuilt so they don't go stale. This
is the [Discovery](/docs/policies/lifecycle-management/discovery/) and Patch stages of Lifecycle
Management, built. What a tenant runs is the tenant's to keep current.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Patch Management](/docs/roadmap/infrastructure/substrate/patch-management/plan/)
