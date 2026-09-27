---
title: "Shared Storage"
weight: 9
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 5
---

# Shared Storage

Give the site storage that outlives any single hypervisor.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Today every VM disk lives on the local storage of the hypervisor that runs it
([Substrate Storage](/docs/architecture/substrate/storage/)). A data disk outlives its VM but not
its host, so losing a hypervisor's data disk loses every disk on it. Anything that must survive
that — the tenant state store ([ADR-0014](/docs/architecture/decisions/0014-tenant-state-durability/)),
object storage for tenants ([ADR-0026](/docs/architecture/decisions/0026-object-storage/)), and data
disks that should move between hosts — has nowhere to live yet.

**In Scope**
- Deciding which consumers need storage independent of a host, and what losing it may cost
- Choosing the approach, recorded as an ADR
- Selecting and evaluating the hardware
- Building it on the storage segment, and moving the first consumer onto it

**Out of Scope**
- Each hypervisor's local layout: the [Hypervisor Storage](/docs/roadmap/infrastructure/mobile/hypervisor-storage/) project
- Clustering the hypervisors

---

## Decide ⏳

- ⏳ List the consumers that need host-independent storage, and what each may lose
- ⏳ Choose the approach (a storage host on the storage segment, or storage distributed across the
  hypervisors) and record it as an ADR

## Build ⏳

- ⏳ Select and evaluate the hardware, per [Evaluation](/docs/policies/lifecycle-management/evaluation/)
- ⏳ Build it on the storage segment, under a change record
- ⏳ Move the first consumer onto it, and prove a restore after losing the hypervisor it came from
