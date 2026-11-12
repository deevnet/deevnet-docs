---
title: "Tenant Removal: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/tenant-removal/
  - /projects/tenant-removal/
weight: 13
tasks_completed: 3
tasks_in_progress: 1
tasks_planned: 0
---

# Tenant Removal: Project Plan

A tenant delete removes what the tenant can use, its state and its dashboards, and revokes its
token and name. Its log lines are what remain. The work is carried out by
[CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/). The operator's procedure is
[Tenant Removal](/docs/runbook/substrate/tenant-removal/).

**Roadmap item:** [Tenant Removal](/docs/roadmap/infrastructure/tenant-services/tenant-removal/)

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

## Leftovers 🔄

- ✅ **State.** The delete removes every version of every object under `tenants/<name>/`, after the
  tenant's store user. The API's store user may only list and delete there (API v0.20.0).
- 🔄 **Logs.** The delete purges the index's three partitions through VictoriaLogs' own delete API,
  after the tenant's log users and before the index is freed. Built and tested against v1.52.0;
  in review, then the `victorialogs` role turns on `-delete.enable` and API v0.21.0 is deployed.
- ✅ **Dashboards.** The delete empties the organization (folders, dashboards, library panels,
  snapshots, annotations) before it is renamed `deleted-<name>-<id>` (API v0.20.1).

## Tokens ✅

- ✅ **Revoke the API token.** The delete records the token's hash and the tenant's name in the same
  transaction that removes its row. Any token for a deleted name is refused until the name is
  admitted again, and the names were seeded from the audit log, so tenants deleted earlier are
  covered too (API v0.20.0, v0.20.2).
