---
title: "Tenant Lifecycle"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/mobile/tenant-platform/
  - /docs/roadmap/infrastructure/tenant-services/tenant-platform/
weight: 2
value: [fast-delivery]
milestones:
  - title: "The Deevnet API and its Terraform provider deployed; tenants built through them (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "The first tenant built end to end from its own repository: code, internet access and DNS"
    status: done
    date: "2026-09-03"
  - title: "A reference tenant a newcomer can copy"
    status: done
    date: "2026-09-27"
  - title: "Tenants log in to their own servers and deploy their app (CHG-0028)"
    status: done
    date: "2026-09-27"
  - title: "Tenants admitted and removed, and their Wi-Fi keys rotated, by make targets on the build server"
    value: [fast-delivery, one-operator]
    status: done
    date: "2026-09-29"
  - title: "A drill for recovering tenant credentials, and provisioning cleanup"
    value: [rebuild-from-code]
    status: active
  - title: "A tenant rebuilt from its own code in a drill"
    value: [rebuild-from-code]
    status: planned
  - title: "The boundary between tenants and the site's infrastructure written as one specification"
    status: done
    date: "2026-11-01"
---

# Tenant Lifecycle

A tenant declared, built, admitted, operated and removed as code: through the Deevnet API and its
Terraform provider, from the tenant's own repository. Each tenant supplies its own IaC/CaC and can be
rebuilt from scratch against the substrate.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/plan/)
