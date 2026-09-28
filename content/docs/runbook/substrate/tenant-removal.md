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

Either the tenant or the operator can delete a tenant. Both send `DELETE /v1/tenants/{name}`.

| | |
|---|---|
| The tenant | `terraform destroy` in its own repository, with its own API token. The workloads go first, then the tenant |
| The operator | the call below, with the operator token. Delete the tenant's workloads first |

```bash
curl -sS --cacert site-ca.pem -X DELETE \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  https://api.mobile.deevnet.net:8080/v1/tenants/<name>
```

A delete answers `409` while the registry still holds any of the tenant's workloads. It checks only
the registry: a VM made outside the API is not seen, and would also keep the tenant's VNet from being
deleted.

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
| The tenant's Terraform state, every version of it, and its lock | `tf-state/tenants/<name>/` in the state store | [remove it](#removing-the-tenants-state) |
| Log lines | partitions `(index, 0..2)` in VictoriaLogs | nothing today: they age out after the 30-day retention |
| The Grafana organization | renamed `deleted-<name>-<id>`, with any dashboards the tenant saved in it | nothing today: Grafana 13 cannot delete an organization |
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

The state store's MinIO container carries `mc`, and its root credentials are already in the
container's environment. Run this from the Builder:

```bash
ssh a_autoprov@dv02prv001v01.mobile.deevnet.net 'sudo podman exec minio sh -c '\''
  export MC_CONFIG_DIR=/tmp/mc-cleanup
  mc alias set local https://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" --insecure >/dev/null
  mc ls --insecure --recursive --versions local/tf-state/tenants/<name>/
  mc rm --insecure --recursive --force --versions local/tf-state/tenants/<name>/
  echo "versions left: $(mc ls --insecure --recursive --versions local/tf-state/tenants/<name>/ | wc -l)"
  rm -rf /tmp/mc-cleanup
'\'''
```

`--versions` matters. The bucket is versioned, so a plain `mc rm` only adds delete markers, and
every earlier state, credentials and all, stays stored underneath them. Done right, it ends with
`versions left: 0`.

Remove the state before admitting the name again. Otherwise the new tenant's
`make state-backend` finds the old state and a lock nobody holds.

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| The tenant's `terraform destroy` ends in `Failed to save state` / `InvalidAccessKeyId`, and a lock it cannot release | expected: the delete removed the state-store user the backend was writing with. `errored.tfstate` should hold no resources; delete it, then [remove the state](#removing-the-tenants-state) |
| `409` "destroy them first" | the registry still holds workloads. Delete them, then the tenant |
| `502` part-way through | a backend step failed. The tenant stays in `deleting` with the failing step recorded, and repeating the `DELETE` picks up from there |
| `409` creating a tenant under a deleted name | the delete has not finished; the row is still there in `deleting` |
