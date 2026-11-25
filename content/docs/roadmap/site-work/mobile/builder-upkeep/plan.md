---
title: "Builder Upkeep: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/builder-upkeep/
  - /projects/builder-upkeep/
weight: 20
tasks_completed: 0
tasks_in_progress: 1
tasks_planned: 3
---

# Builder Upkeep: Project Plan

The Builder's own disks and links, as it is used: space where the work happens, and a way onto the
home network when the factory is parked there.

**Roadmap item:** [Builder Upkeep](/docs/roadmap/site-work/mobile/builder-upkeep/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Space 🔄

`/home` is a 20 GB volume and was 96% full on 2026-11-01, mostly Podman's image store, the Go
module cache and build caches, while `/srv` had 774 GB free.

- 🔄 Rebuild or reconfigure the Builder with more space for `/home`: the builder kickstart gives it
  60 GB ([CHG-0091](/docs/changes/2026/0091-temporary-builder-f44/)), which the Builder takes when
  it is repaved
- ⏳ Keep Podman's storage and `GOPATH` under `/srv`, so build caches stop filling `/home`

---

## Wi-Fi onto the home network ⏳

The Builder has a Wi-Fi radio it does not use (`wlp3s0`, a Realtek RTL8821CE). Its upstream leg is
meant to join whatever network is there.

- ⏳ Join the home network over Wi-Fi when the factory is parked there, during a maintenance window:
  a Mac at home reaches the Builder, and the Builder reaches the home Pis (EdS ADR-0053)
- ⏳ A record deciding how the upstream leg joins the house, and what it is called there
