---
title: "Tenant Removal"
weight: 8
---

# Tenant Removal

Taking a tenant out of service. The API tears down almost everything it built for the tenant; this
page covers what that removes and the leftovers the operator cleans up by hand. Creating a tenant is
[Tenant Admission](/docs/runbook/substrate/tenant-admission/).

---

## Who deletes

Either the tenant or the operator can delete a tenant. Both end in `DELETE /v1/tenants/{name}`.

| | |
|---|---|
| The tenant | `terraform destroy` in its own repository, with its own API token. The workloads go first, then the tenant. The operator then [removes its state](#removing-the-tenants-state) |
| The operator | `make remove-tenant` from `ansible-collection-deevnet.mgmt` on the Builder |

```bash
make remove-tenant NAME=<name>
```

```
Removing tenant trm (index 5):
  workloads:  w1
  then its network, DNS zones, broker accounts, Wi-Fi keys, log tokens and Grafana login,
  and its Terraform state in tf-state/tenants/trm/, every version.
This cannot be undone. Type 'trm' to go ahead: trm
deleted workload w1
deleted tenant trm
state purged: tf-state/tenants/trm/ is empty
```

It deletes the tenant's workloads, then the tenant, then its state, and stops at the first step that
fails. It reads the operator token from the API container, as `make admit` does. `CONFIRM=<name>`
answers the question in advance.

The API refuses to delete a tenant (`409`) while its registry holds any workloads, which is why the
target deletes them first. It checks only the registry: a VM made outside the API is not seen, and
would also keep the tenant's VNet from being deleted.

---

## What a delete removes

The steps run in this order. Each one treats "already gone" as done.

| Order | Backend | Removed |
|---|---|---|
| 1 | Dashboards | the tenant's Grafana login and its three log data sources; the organization is renamed, not deleted (see below) |
| 2 | Log store | the tenant's vmauth users, so its ingest and read tokens stop working |
| 3 | Broker | every MQTT account the tenant holds |
| 4 | Wi-Fi | every PPSK key the tenant holds, on the Omada controller |
| 5 | Network | the tenant's subnets, VNets and EVPN zone, then an SDN apply |
| 6 | Resolver | the Unbound forwards for the tenant's forward and reverse zones |
| 7 | DNS | both zones, with every record in them, and the tenant's TSIG key |
| 8 | State | the tenant's state-store user and its policy |
| 9 | Registry | the tenant's row, and with it its workloads, records, keys, devices, broker accounts and secrets |

The index is free again as soon as the row is gone. The next tenant created gets the lowest free
index.

---

## What a delete leaves

| Leftover | Where | What to do |
|---|---|---|
| The tenant's Terraform state, every version of it, and its lock | `tf-state/tenants/<name>/` in the state store | `make remove-tenant` removes it; after a tenant's own destroy, [remove it](#removing-the-tenants-state) |
| Log lines | partitions `(index, 0..2)` in VictoriaLogs | nothing today: they age out after the 30-day retention. VictoriaLogs can delete (`-delete.enable`), but the flag is off here |
| The Grafana organization | renamed `deleted-<name>-<id>`, with any dashboards the tenant saved in it | nothing today: Grafana 13 cannot delete an organization. `GET /api/orgs` as the Grafana admin lists them |
| The tenant's API token | wherever the tenant kept its state | nothing today: it can still recreate a tenant under that name |
| Audit entries | the API's `audit_log` | none; the audit log is kept on purpose |

**The state holds every credential the tenant was issued.** They are all revoked by the delete, but
the state is still the tenant's data, and any tenant later created under the same name is given
the same prefix.

**Log lines are addressed by index, not by name.** A new tenant is given the freed index straight
away, so until the retention runs out its partitions still hold the previous tenant's lines.

The last three rows are gaps in the delete itself, tracked on the
[Tenant Removal roadmap](/docs/roadmap/infrastructure/tenant-removal/).

---

## Removing the tenant's state

`make remove-tenant` ends with this. After a tenant has run its own `terraform destroy`, run it
alone:

```bash
make purge-tenant-state NAME=<name>
```

It refuses while `<name>` is still a tenant, since that tenant would still be writing there. It
removes every version under `tf-state/tenants/<name>/`, not just the current objects: the bucket is
versioned, so a plain delete only adds delete markers, and every earlier state, credentials and all,
stays stored underneath them. It runs `mc` inside the state store's MinIO container, whose root
credentials never leave it, and finishes only when no versions are left.

Remove the state before admitting the name again. Otherwise the new tenant's
`make state-backend` finds the old state and a lock nobody holds.

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| The tenant's `terraform destroy` ends in `Failed to save state` / `InvalidAccessKeyId`, and a lock it cannot release | expected: the delete removed the state-store user the backend was writing with. `errored.tfstate` should hold no resources; delete it, then [remove the state](#removing-the-tenants-state) |
| `409` "destroy them first" | the registry still holds workloads. `make remove-tenant` deletes them first; called by hand, delete them, then the tenant |
| `502` part-way through | a backend step failed. The tenant stays in `deleting` with the failing step recorded, and running `make remove-tenant` again picks up from there |
| `409` creating a tenant under a deleted name | the delete has not finished; the row is still there in `deleting` |
