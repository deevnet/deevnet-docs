---
title: "Tenant Removal"
weight: 9
---

# Tenant Removal

Taking a tenant out of service. The API tears down everything it built for the tenant and
everything the tenant left behind, then revokes the tenant's token and name. This page covers what
a delete removes and the little it leaves. Creating a tenant is
[Tenant Admission](/docs/runbook/substrate/tenant-admission/).

---

## Who deletes

Either the tenant or the operator can delete a tenant. Both end in `DELETE /v1/tenants/{name}`.

| | |
|---|---|
| The tenant | `terraform destroy` in its own repository, with its own API token. The workloads go first, then the tenant |
| The operator | `make remove-tenant` from `ansible-collection-deevnet.mgmt` on the Builder |

**Either way, OpenBao must be open: delete in a [work session](/docs/runbook/substrate/building-recovery/openbao-keys/#a-work-session).** While it is sealed the API
answers 503, *OpenBao is sealed or unreachable; tenant work waits until it is opened*, and nothing is removed.

```bash
make remove-tenant NAME=<name>
```

```
Removing tenant trm (index 5):
  workloads:  w1
  then its network, DNS zones, broker accounts, Wi-Fi keys, log tokens, Grafana login and dashboards,
  and its Terraform state in tf-state/tenants/trm/, every version.
This cannot be undone. Type 'trm' to go ahead: trm
deleted workload w1
deleted tenant trm
state purged: tf-state/tenants/trm/ is empty
```

It deletes the tenant's workloads, then the tenant, and stops at the first step that fails. Then it
checks that the tenant's state is gone. It reads the operator token from the API container, as
`make admit` does. `CONFIRM=<name>` answers the question in advance.

The API refuses to delete a tenant (`409`) while its registry holds any workloads, which is why the
target deletes them first. It checks only the registry: a VM made outside the API is not seen, and
would also keep the tenant's VNet from being deleted.

---

## What a delete removes

**The steps run in this order, and each one treats "already gone" as done.** A delete that
stopped part way resumes when it is run again.

| Order | Backend | Removed |
|---|---|---|
| 1 | Dashboards | everything the tenant saved in its organization (folders, dashboards, library panels, snapshots, annotations), its Grafana login and its three log data sources; the emptied organization is renamed, not deleted (see below) |
| 2 | Log store | the tenant's vmauth users, so its ingest and read tokens stop working; then every log line in its partitions `(index, 0..2)`, waiting until the store has finished |
| 3 | Broker | every MQTT account the tenant holds |
| 4 | Wi-Fi | every PPSK key the tenant holds, on the Omada controller |
| 5 | Addresses | the tenant's devices' DHCP reservations on the core router |
| 6 | Network | the tenant's subnets, VNets and EVPN zone, then an SDN apply |
| 7 | Resolver | the Unbound forwards for the tenant's forward and reverse zones |
| 8 | DNS | both zones, with every record in them, and the tenant's TSIG key |
| 9 | State | the tenant's state-store user and its policy, then every version of every object under `tf-state/tenants/<name>/`, its lock included |
| 10 | Registry | the tenant's row, and with it its workloads, records, keys, devices, broker accounts and secrets. In the same transaction, the tenant's token and name are recorded as revoked |

**A deleted tenant's token is refused everywhere.** That includes creating the tenant again: `401`
as a bearer, `400` inside an operator's restore. The same holds for any other token issued for that
name, including tenants deleted before revocation existed. The name comes back only through
[admission](/docs/runbook/substrate/tenant-admission/), which issues a new token.

**The index is free again as soon as the row is gone.** The next tenant created gets the lowest
free index.

---

## What a delete leaves

**Two things outlive a delete, both by design.**

| Leftover | Where | What to do |
|---|---|---|
| The Grafana organization, empty | renamed `deleted-<name>-<id>` | nothing: Grafana 13 cannot delete an organization. `GET /api/orgs` as the Grafana admin lists them |
| Audit entries | the API's `audit_log` | none; the audit log is kept on purpose |

---

## Older leftover state

**State left by a delete on an API older than v0.20.0 is still in the bucket.** Those deletes
removed the state-store user but not the objects. Remove them with:

```bash
make purge-tenant-state NAME=<name>
```

It refuses while `<name>` is still a tenant, since that tenant would still be writing there. It
removes every version under `tf-state/tenants/<name>/`, not just the current objects: the bucket is
versioned, so a plain delete only adds delete markers. Every earlier state, credentials and all,
would stay stored underneath them. It runs `mc` inside the state store's MinIO container, whose
root credentials never leave it, and finishes only when no versions are left.

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| The tenant's `terraform destroy` ends in `Failed to save state` / `InvalidAccessKeyId`, and a lock it cannot release | expected: the delete removed the state-store user the backend was writing with, then the state itself. `errored.tfstate` should hold no resources; delete it |
| `409` "destroy them first" | the registry still holds workloads. `make remove-tenant` deletes them first; called by hand, delete them, then the tenant |
| `502` part-way through | a backend step failed. The tenant stays in `deleting` with the failing step recorded, and running `make remove-tenant` again picks up from there |
| `409` creating a tenant under a deleted name | the delete has not finished; the row is still there in `deleting` |
| `401` from a tenant's token after its delete | expected: the token was revoked with the tenant. Admit the name again for a new one |
