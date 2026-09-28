---
title: "Tenant Removal"
weight: 8
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 4
---

# Tenant Removal

A tenant delete removes what the tenant can use, but not everything the tenant leaves behind. The
operator's procedure today is [Tenant Removal](/docs/runbook/substrate/tenant-removal/).

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

## Leftovers ⏳

- ⏳ **State.** Delete the objects under `tenants/<name>/`, every version of them, with the
  tenant. Today the delete removes only the store user, and the objects stay on purpose; that
  decision needs revisiting, since a tenant later created under the same name is given the same prefix.
- ⏳ **Logs.** Keep a freed index out of use until the log retention has passed, or delete the
  index's partitions with the tenant. Today the next tenant created gets the freed index, and its
  partitions still hold the previous tenant's lines.
- ⏳ **Dashboards.** Delete the tenant's dashboards before the organization is renamed
  `deleted-<name>-<id>`, since Grafana 13 cannot delete the organization itself.

## Tokens ⏳

- ⏳ **Revoke the API token.** A deleted tenant's token is still a valid proof of identity, and the
  API accepts a tenant token to create its own name, so the old token can recreate the tenant.
  The delete should leave a record that refuses it.
