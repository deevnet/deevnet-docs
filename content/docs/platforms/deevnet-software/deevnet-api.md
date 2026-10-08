---
title: "Deevnet API"
weight: 1
---

# Deevnet API

Fills the **provisioning API** role at the
[substrate–tenant boundary](/docs/architecture/tenant/boundary/): the one interface a tenant uses,
which builds on the substrate what the tenant declares
([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/),
[ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)). It is
provisioning-only: nothing at runtime depends on it being up.

| | |
|---|---|
| **Repository** | `deevnet-provisioning-api`, Go ([version](/docs/platforms/software-catalog/#deevnets-own-software)) |
| **Runs on** | `dv02prv001v01`, 10.20.25.20, as two podman containers under systemd: `deevnet-api` (port 8080, TLS from the site CA, `api.mobile.deevnet.net`) and `deevnet-api-db` (PostgreSQL, on a private podman network, no published port) |
| **Deployed by** | `deevnet.mgmt` role `deevnet_api`: `ansible-playbook playbooks/site.yml --limit deevnet_api`. The image is built and staged on the Builder (`make stage`) and pushed to the host, never pulled. The role ends by checking `/readyz` and that `/version` is the pinned version |
| **Contract** | `api/openapi.yaml` in the repository (OpenAPI 3.1), published as the [API reference](https://deevnet.github.io/deevnet-provisioning-api/docs/reference/) |
| **Documentation** | [deevnet.github.io/deevnet-provisioning-api](https://deevnet.github.io/deevnet-provisioning-api/) |

---

## What it exposes

**The API has its own documentation site, [Deevnet API](https://deevnet.github.io/deevnet-provisioning-api/).** Its
[reference](https://deevnet.github.io/deevnet-provisioning-api/docs/reference/) lists every route, request and response, and is rendered from the
OpenAPI specification in the repository, which a test holds to the code.

| Routes | Who calls them |
|---|---|
| `/healthz`, `/readyz`, `/version` | Anyone; no token |
| Admissions, the tenant list, reconcile | The operator only |
| A tenant, and its workloads, names, devices, addresses, Wi-Fi keys and broker accounts | The tenant, with its own token, or the operator |
| `GET /v1/fabric/egress` | The operator, or the [egress agent](/docs/platforms/deevnet-software/egress-agent/)'s own token |

Log tokens and the dashboards login have no routes of their own. They are steps of creating,
restoring and reconciling a tenant, and come back in those responses.

---

## What it holds

**Backend credentials**, in OpenBao (KV mount `deevnet-api`, path `backends`), read at start with the
API's own AppRole. Each comes from the inventory vault, and rotating one is a vault edit and a role
run:

| Backend | Credential |
|---|---|
| Proxmox (tenant hypervisor) | Its own token, `deevnet-api@pve!tenants`, under the role `DeevnetTenantBuilder`, with `Sys.Audit` on `/nodes` through `DeevnetNodeAudit` |
| OPNsense | The router's API key (shared with the `deevnet.net` collection). The API uses it for the resolver's tenant zone forwards and the DHCP server's reservations for tenants' devices |
| PowerDNS | The HTTP API key, which the server accepts only from this host |
| MinIO | An admin user, `deevnet-api` |
| Omada controller | Its own Open API client, separate from the one Ansible uses |
| Broker accounts, log users | An SSH key each, to the `deevnet-broker-account` and `deevnet-log-user` forced commands |
| Grafana | The server admin password |

**Its Proxmox access is declared in inventory** (`proxmox_node_access` in
`host_vars/dv02hyp002p02/vars.yml`) and recreated by `deevnet.builder`'s `proxmox_node_access` role;
only the token is issued by hand
([Build a Hypervisor → Step 7](/docs/runbook/substrate/building-recovery/build-hypervisor/#step-7-proxmox-access-token-manual)).

| Role | Privileges | Granted at |
|---|---|---|
| `DeevnetTenantBuilder` | Datastore.AllocateSpace, Datastore.AllocateTemplate, Datastore.Audit, SDN.Allocate, SDN.Audit, SDN.Use, VM.Allocate, VM.Audit, VM.Clone, VM.Config.CPU, VM.Config.Cloudinit, VM.Config.Disk, VM.Config.Memory, VM.Config.Network, VM.Config.Options, VM.Migrate, VM.PowerMgmt | `/` |
| `DeevnetNodeAudit` | Sys.Audit | `/nodes` |

Both are granted to the user `deevnet-api@pve` and to its token.

**Tenant secrets** it issues are sealed with the OpenBao Transit key `tenant-secrets`, and enrollment
tokens use response wrapping. Tenant tokens are HMACs of a key in the vault, so they verify
without the registry, as long as that key is unchanged.

**The registry**: PostgreSQL, at `/srv/deevnet-api/pgdata` on the VM's own disk: tenants, their
workloads, records, keys, devices and broker accounts, each step's outcome, and an audit log.
**Nothing copies it off the host**
([ADR-0014](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/), Proposed).

---

## How it behaves on repair

- **Create, restore, resume.** A tenant applied with its three secrets from its own state is a
  *restore*: the same index, the same keys. A create that was interrupted resumes and issues a new
  API token.
- **Reconcile** re-ensures every backend for a registered tenant, in order: DNS, resolver
  forwarding, state store, the fabric network, then the log store and dashboards. It stops at the
  first failure and records it; calling again resumes. It returns the tenant's log tokens and
  dashboard password, and nothing else: not its DNS or state secrets, and not its API token.
- **Workloads are not part of a reconcile.** Applying a workload always ensures its VM, rebuilding a
  missing one with the same VMID, MAC and address. But a tenant's plain `terraform apply` does not
  re-apply a workload the registry already lists
  ([Tenant Platform roadmap](/docs/roadmap/infrastructure/mobile/tenant-platform/)).
- **Losing the registry is recoverable.** A tenant's next apply restores it from the secrets in the
  tenant's state.
- **Delete** refuses while a tenant has workloads, then removes dashboards, log tokens, Wi-Fi keys,
  network, resolver forwarding, DNS and state access, in that order.
