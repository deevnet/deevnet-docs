---
title: "Tenant Removal"
weight: 0
---

# Tenant Removal

{{< status-badge "complete" "Complete" >}}

**A tenant delete leaves nothing of the tenant behind that a later tenant could read or use.** The
Deevnet API's delete tears down what it built for the tenant, then removes what the tenant left:
every version of its Terraform state, everything it saved in its dashboards organization, and every
log line in its three partitions, before its index can be given to another tenant. It revokes the
tenant's API token and name in the same transaction that removes its row, so no token for that name
works again until the name is admitted again. Only the audit log, and the emptied Grafana
organization, which Grafana cannot delete, remain.

It was delivered by [CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/) against its
[plan](/projects/archive/tenant-removal/).

## How it is built

- The Deevnet API's tenant delete, in `deevnet-provisioning-api`
  ([Deevnet API](/docs/platforms/deevnet-software/deevnet-api/)).
- `deevnet-log-user` on the log store, which purges a freed index's partitions through the store's
  own delete API, reachable only on the store's loopback.
- The `minio` and `victorialogs` roles in `deevnet.mgmt`, which give the API's state-store user
  list and delete rights under `tenants/*` only, and turn on the log store's delete API.

## How it is checked

- The API's integration tests run each purge against the real state store, Grafana and
  VictoriaLogs, with a neighbor tenant that must be left untouched.
- Live, a throwaway tenant writes state, dashboards and log lines in all three partitions, then
  deletes itself with its own token; its state, organization and partitions must be empty, its token
  refused, and the name admitted again must start clean.

The operator's procedure is [Tenant Removal](/docs/runbook/substrate/tenant-removal/).
