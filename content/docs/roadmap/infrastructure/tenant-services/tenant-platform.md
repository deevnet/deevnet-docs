---
title: "Tenant Platform"
aliases:
  - /docs/roadmap/infrastructure/mobile/tenant-platform/
weight: 1
milestones:
  - title: "Design tenant network architecture"
    status: done
    date: "2026-08-30"
  - title: "The Deevnet API and its provider deployed; tenants built through them (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "The tenant–substrate boundary written as one specification"
    status: planned
  - title: "The tenant fabric: single-member, egress at the perimeter"
    status: done
    date: "2026-09-17"
  - title: "The core router reduced to the perimeter"
    status: planned
  - title: "Tenant DNS publication"
    status: done
    date: "2026-09-03"
  - title: "A reference tenant a newcomer can copy"
    status: done
    date: "2026-09-27"
  - title: "Tenants admitted, removed and rotated by Builder make target"
    status: done
    date: "2026-09-29"
  - title: "Tenant provisioning: the credential-recovery drill and cleanup"
    status: active
  - title: "The first tenant end to end: code, egress, DNS, its own repository"
    status: done
    date: "2026-09-03"
  - title: "Tenants log in to their own workloads and deploy their app (CHG-0028)"
    status: done
    date: "2026-09-27"
  - title: "Tenants' workloads isolated from each other, and a rebuild drill"
    status: planned
  - title: "The first platform services: Wi-Fi keys, device registry, VerneMQ, logs, a dev network, dashboards, downloads"
    status: done
    date: "2026-09-24"
  - title: "Fixed addresses for tenants' devices (CHG-0044)"
    status: done
    date: "2026-10-07"
  - title: "Tenant-facing services on 443, by name (CHG-0046)"
    status: done
    date: "2026-10-10"
  - title: "Platform services: secrets, metrics, identity, object storage, quotas"
    status: active
  - title: "Windows tenant laptops"
    status: planned
---

# Tenant Platform

Deliver the capability to run **tenants** on the mobile substrate — from network architecture
through a repeatable, code-defined tenant lifecycle. Each tenant is an isolated workload that
supplies its own IaC/CaC to rebuild from scratch against the substrate.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Tenant Platform](/projects/tenant-platform/)
