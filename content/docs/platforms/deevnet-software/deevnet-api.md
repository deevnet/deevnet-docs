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
| **Runs on** | `dv02prv001v01`, 10.20.25.20, as two podman containers under systemd: `deevnet-api` (on the host's loopback address; tenants reach it at `https://api.mobile.deevnet.net` through the host's [service proxy](/docs/platforms/management-plane/substrate-service-vms/#the-service-proxy)) and `deevnet-api-db` (PostgreSQL, on a private podman network, no published port) |
| **Deployed by** | `deevnet.mgmt` role `deevnet_api`: `ansible-playbook playbooks/site.yml --limit deevnet_api`. The image is built and staged on the Builder (`make stage`) and pushed to the host, never pulled. The role ends by checking `/readyz` and that `/version` is the pinned version |
| **Contract** | `api/openapi.yaml` in the repository (OpenAPI 3.1), published as the [API reference](https://deevnet.github.io/deevnet-provisioning-api/docs/reference/) |
| **Documentation** | [deevnet.github.io/deevnet-provisioning-api](https://deevnet.github.io/deevnet-provisioning-api/), with [release notes](https://deevnet.github.io/deevnet-provisioning-api/docs/release-notes/) for every version |

---

## What it exposes

**The API has its own documentation site, [Deevnet API](https://deevnet.github.io/deevnet-provisioning-api/).** Its
[reference](https://deevnet.github.io/deevnet-provisioning-api/docs/reference/) lists every route, request and response, and is rendered from the
OpenAPI specification in the repository, which a test holds to the code.

| Routes | Who calls them |
|---|---|
| `/healthz`, `/readyz`, `/version` | Anyone; no token |
| Admissions, the tenant list, reconcile, a state-secret reissue | The operator only |
| A tenant, and its workloads, names, devices, addresses, Wi-Fi keys, broker accounts, service certificates, runtime secrets and their readers | The tenant, with its own token, or the operator |
| `GET /v1/fabric/egress` | The operator, or the [egress agent](/docs/platforms/deevnet-software/egress-agent/)'s own token |

**A service certificate is signed in the secret store, not by the API.** A tenant sends a signing
request with a label, any further labels, and the sites to name; the API builds every name, asks the
Tenant Service CA to sign on the one role its policy allows, and checks what comes back before
returning it ([ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/)).
The tenant's key never reaches it.

**A certificate names its service without a site first, then at each site asked for**
([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) §3). Its
common name and first name are `<label>.<tenant>.deevnet.net`, each further label follows the same
way, then each label at each site, `<label>.<tenant>.<site>.deevnet.net`. The sites come from the
request (`sites`), among those the API is configured to issue for (`DEEVNET_CERTIFICATE_SITES`,
`mobile` and `home` here); none asked means this site alone. A certificate asked for again with
other names is reissued.

**The API's reserved list is what keeps a tenant's names apart from a site's.** Tenant names that are
a site, a site code, a global alias or `mqtt` are refused at create and admission (`home`, `mobile`,
`mgmt`, `dvnt`, `dvntm`, `device`, `mqtt`, `artifacts`), and `device` is refused as a certificate
label: it holds a tenant's device names. OpenBao refuses the same labels itself: the API signs
through the Tenant Service CA's CEL role (`OPENBAO_TENANT_SERVICE_CEL`), a program Ansible writes
with its own copy of the list, and its policy allows no other path
([CHG-0059](/docs/changes/2026/0059-cel-signing-role/)). A label added to the API's list is added
to that copy.

**A tenant's runtime secrets go to its own OpenBao namespace, and the API never reads one back**
([ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/),
[CHG-0067](/docs/changes/2026/0067-tenant-secrets/)). Each tenant gets `tenants/<name>`
(`DEEVNET_TENANT_SECRETS_NAMESPACE`), with a key-value mount and an AppRole mount. A secret's value
goes there and nowhere else; a `GET` reports only that it is there, and its version. A reader is an
AppRole and a policy naming the paths it may read. It is bound to the tenant fabric's exit node
(`DEEVNET_TENANT_SECRETS_SOURCE_CIDRS`), the only address OpenBao sees a workload come from while the
fabric source-NATs, and deleting it deletes both, which cuts off a token already issued. The API's
own policy reaches below `tenants/` and nothing above it.

Log tokens and the dashboards login have no routes of their own. They are steps of creating,
restoring and reconciling a tenant, and come back in those responses.

---

## What it holds

**Backend credentials**, in OpenBao (KV mount `deevnet-api`, path `backends`), read with the API's
own AppRole once OpenBao is open. Each comes from the inventory vault, and rotating one is a vault
edit and a role run:

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

**Its AppRole logs in only from its own address**, and its secret ID lives a year. The
`deevnet_api` role looks the secret ID up on each deploy, issues a new one when fewer than 60 days
remain, and destroys the old one once the API is up on the new; a year with no deploy leaves the API
unable to log in ([OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/#logging-in)).

**Tenant secrets** it issues are sealed with an OpenBao Transit key, named in the inventory
(`openbao_transit_key`) and imported from the vault, never made inside OpenBao. Enrollment tokens use
response wrapping. **A new Transit key does not strand what the old one sealed:** with
`OPENBAO_TRANSIT_KEY_PREVIOUS` set, the API decrypts with the old key when the new one refuses, and
`deevnet-api reseal`, run in its container, moves every stored value to the new key
([OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/#the-transit-key)). Tenant tokens are HMACs of a key in the vault, so they verify
without the registry, as long as that key is unchanged.

**The registry**: PostgreSQL, at `/srv/deevnet-api/pgdata` on the VM's own disk: tenants, their
workloads, records, keys, devices and broker accounts, each step's outcome, and an audit log.
**Nothing copies it off the host, by design**: a tenant's code is the authoritative copy, and a lost
registry is rebuilt from it ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)).

---

## How it behaves on repair

- **A lost secrets namespace costs each tenant one apply and one push.** The reconcile makes the
  namespace again, empty. The tenant's next apply finds its secrets and readers gone and writes them
  again from its own code; the readers come back with new IDs, which the tenant pushes to its
  workloads. A tenant delete deletes the namespace first.
- **A sealed or unreachable OpenBao is unavailable, never a lost secret.** Tenant work answers `503`
  before anything changes, a tenant token gets `503` rather than `401`, and `/readyz` names the
  state (`ok`, `sealed`, `uninitialized`, `unreachable`). The API starts while OpenBao is sealed and
  reads its backend credentials when it opens. Only a ciphertext OpenBao answers and refuses is a
  lost secret, which the tenant supplies again from its state on its next apply.
- **Create, restore, resume.** A tenant applied with its three secrets from its own state is a
  *restore*: the same index, the same keys. A create that was interrupted resumes and issues a new
  API token.
- **Reconcile** re-ensures every backend for a registered tenant, in order: DNS, resolver
  forwarding, state store, the fabric network, the log store and dashboards, then the tenant's
  secrets namespace. It stops at the
  first failure and records it; calling again resumes. It returns the tenant's log tokens and
  dashboard password, and nothing else: not its DNS or state secrets, and not its API token.
- **A state-secret reissue** mints a new state-store secret for a tenant, records it, sets it on the
  store and returns it, for an operator to hand over. The old one stops working. The registry is
  written first, so a store that refused is put right by the next reconcile. It refuses a tenant
  whose stored secrets the API can't read, which would otherwise be written back empty. The
  registry marks the secret as reissued, and a restore that sends back the tenant's older copy
  keeps the reissued one and returns it, until the tenant supplies it itself.
- **Workloads are not part of a reconcile.** Applying a workload always ensures its VM, rebuilding a
  missing one with the same VMID, MAC and address. But a tenant's plain `terraform apply` does not
  re-apply a workload the registry already lists
  ([Tenant Lifecycle roadmap](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/)).
- **Losing the registry is recoverable.** A tenant's next apply restores it from the secrets in the
  tenant's state.
- **Delete** refuses while a tenant has workloads. It then removes, in order:
  - dashboards, emptying the organization first;
  - log tokens;
  - Wi-Fi keys and the network;
  - resolver forwarding and DNS;
  - state access, then every version of the tenant's state.

  It removes the registry row last, recording the tenant's token and name as revoked in the same
  transaction. From then on any token for that name is refused, until the name is admitted again
  ([CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/)).
