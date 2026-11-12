---
title: "Tenant Removal"
aliases:
  - /docs/projects/tenant-removal/
  - /projects/tenant-removal/
  - /docs/roadmap/infrastructure/tenant-removal/
  - /docs/roadmap/infrastructure/tenant-services/tenant-removal/
  - /docs/roadmap/infrastructure/tenant-services/tenant-removal/plan/
weight: 13
tasks_completed: 4
tasks_in_progress: 0
tasks_planned: 0
area: "Infrastructure Automation"
value: [contained-failure]
waypoints:
  - title: "Removing a tenant also deletes its Terraform state and dashboards (CHG-0065)"
    status: done
    date: "2026-11-12"
  - title: "Removing a tenant also deletes its log lines (CHG-0065)"
    status: done
    date: "2026-11-12"
  - title: "Removing a tenant revokes its API token (CHG-0065)"
    status: done
    date: "2026-11-12"
---

# Tenant Removal

A tenant delete removes what the tenant can use, its state, its dashboards and its log lines, and
revokes its token and name. The work was carried out by
[CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/). The operator's procedure is
[Tenant Removal](/docs/runbook/substrate/tenant-removal/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

When a delete finishes, nothing of the tenant should remain that a later tenant could read or
use, and nothing should need the operator's hands.

**In Scope**
- What the API's tenant delete removes, and what it leaves behind
- Whether a name or an index can be reused, and when

**Out of Scope**
- The audit log, which outlives tenants on purpose

---

## Leftovers ✅

- ✅ **State.** The delete removes every version of every object under `tenants/<name>/`, after the
  tenant's store user. The API's store user may only list and delete there (API v0.20.0).
- ✅ **Logs.** The delete purges the index's three partitions through VictoriaLogs' own delete API,
  after the tenant's log users and before the index is freed (API v0.21.0).
- ✅ **Dashboards.** The delete empties the organization (folders, dashboards, library panels,
  snapshots, annotations) before it is renamed `deleted-<name>-<id>` (API v0.20.1).

## Tokens ✅

- ✅ **Revoke the API token.** The delete records the token's hash and the tenant's name in the same
  transaction that removes its row. Any token for a deleted name is refused until the name is
  admitted again, and the names were seeded from the audit log, so tenants deleted earlier are
  covered too (API v0.20.0, v0.20.2).
