---
title: "Tenant Lifecycle"
aliases:
  - /docs/roadmap/infrastructure/mobile/tenant-platform/
  - /docs/roadmap/infrastructure/tenant-services/tenant-platform/
weight: 2
milestones:
  - title: "The Deevnet API and its provider deployed; tenants built through them (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "The first tenant built end to end from its own repository: code, internet access and DNS"
    status: done
    date: "2026-09-03"
  - title: "A reference tenant a newcomer can copy"
    status: done
    date: "2026-09-27"
  - title: "Tenants log in to their own workloads and deploy their app (CHG-0028)"
    status: done
    date: "2026-09-27"
  - title: "Tenants admitted, removed and rotated by Builder make target"
    status: done
    date: "2026-09-29"
  - title: "A drill for recovering tenant credentials, and provisioning cleanup"
    status: active
  - title: "A tenant rebuilt from its own code in a drill"
    status: planned
  - title: "The tenant–substrate boundary written as one specification"
    status: planned
---

# Tenant Lifecycle

A tenant declared, built, admitted, operated and removed as code: through the Deevnet API and its
Terraform provider, from the tenant's own repository. Each tenant supplies its own IaC/CaC and can be
rebuilt from scratch against the substrate.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Tenant Platform](/projects/tenant-platform/), its contracts, provisioning tooling and first-tenant phases
