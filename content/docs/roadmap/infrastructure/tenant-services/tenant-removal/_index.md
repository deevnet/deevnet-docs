---
title: "Tenant Removal"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/tenant-removal/
weight: 5
value: [contained-failure]
waypoints:
  - title: "Removing a tenant also deletes its Terraform state and dashboards (CHG-0065)"
    status: done
    date: "2026-11-12"
  - title: "Removing a tenant also deletes its log lines (CHG-0065)"
    status: active
  - title: "Removing a tenant revokes its API token (CHG-0065)"
    status: done
    date: "2026-11-12"
---

# Tenant Removal

A tenant delete removes what the tenant can use, its state and its dashboards, and revokes its
token and name. Its log lines are what remain, until the retention runs out. The operator's
procedure is [Tenant Removal](/docs/runbook/substrate/tenant-removal/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Tenant Removal](/docs/roadmap/infrastructure/tenant-services/tenant-removal/plan/)
