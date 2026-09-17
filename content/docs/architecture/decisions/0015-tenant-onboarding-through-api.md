---
title: "ADR-0015: Tenant Onboarding Through the Deevnet API"
weight: 15
---

# ADR-0015: Tenants Are Onboarded Through the Deevnet API

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-17 |
| **Scope** | Who allocates a tenant's index, who creates what a tenant is issued at onboarding, and where the record of tenants lives |
| **Extends** | [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/), whose API and provider become the way every tenant is created, not only the way it registers devices |
| **Supersedes, in part** | [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/), where it says allocation is recorded in `TENANTS.md` (the numbering itself stands); [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/) §2 (the attachment rendered into the repository) and §3 (the reference implementation that cannot be applied) |
| **Related** | [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0005: Tenant Zone Apex Ownership](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/), [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/) |

---

## Context

### Onboarding today is a substrate commit and five automation runs

A tenant is created in two halves. The substrate half runs once:

| Step | What does it | What it reads |
|---|---|---|
| Allocate an index | a hand-edited row in `deevnet-tenant-factory/TENANTS.md` | nothing |
| Register the tenant | a hand-edited row `{name, index}` in inventory `deevnet_tenants` | nothing |
| Forward and reverse zone, TSIG key, update ACL, apex SOA and NS | `deevnet.mgmt` `powerdns` role | `deevnet_tenants`, `vault_tenant_tsig_keys` |
| Delegate both zones from the core router's resolver | `deevnet.net` `opnsense_dns` role | `deevnet_tenants` |
| State-store user and prefix policy | `deevnet.mgmt` `minio` role | `deevnet_tenants`, `vault_tenant_state_keys` |
| A default route inside the tenant VRF on the exit node | `deevnet.net` `proxmox_node_network` egress tasks | `deevnet_tenants` |
| Fabric attachment `controller_id`, `node` | `make tenant-attachment` in the factory | `deevnet_tenant_fabric` |

The tenant half is the tenant's own repository, which then applies.

### The index is written in two registries and in every tenant repository

- **ADR-0002** says *"Allocation is recorded in `TENANTS.md` in the tenant factory."*
- **ADR-0004's onboarding** added `deevnet_tenants`, which every role in the table reads.
- **Each tenant repository hardcodes the number:** `tenant_index = 1` in `main.tf`.
- **ADR-0006 §2** made `controller_id` and `node` *issued* rather than authored, but left the index
  authored.

Three copies of one allocation drifted. On 2026-09-16:
- `TENANTS.md` showed index 1 as free.
- Inventory gave index 1 to eds.
- `deevnet-tenant-tdemo`, the first tenant and the pattern new tenants follow, still said
  `tenant_index = 1`. Applying it would have built a second tenant on eds's VNIs, subnet and reverse
  zone.

The only way to keep tdemo safe was to retire it. That is backwards: the tenant that shows how
tenants are built is the one that should always be applicable.

### The recurring test passes, and the result is still wrong

ADR-0010's test is *"does a recurring tenant action need a substrate commit?"* Onboarding happens
once, so today's model passes it. What fails is everything around it:
- **A repository tied to a number** can't be copied, moved to another site, or kept as a reference.
- **Three registries** have to be kept in agreement by hand.
- **Credentials reach the tenant** by the tenant operator reading the substrate vault (ADR-0012
  Context).

### The API that would fix this already exists

ADR-0012 put a Deevnet API on Platform. It holds privileged credentials for services that can't
confine a tenant themselves, and it returns what it generates into the tenant's own state. Tenant
onboarding is the same shape:
- a privileged act against several services
- on behalf of one tenant
- producing secrets the tenant needs

---

## Options considered

### A — The substrate issues the index, from inventory

`deevnet_tenants` becomes the only registry. `make tenant-attachment` renders `tenant_index` beside
`controller_id` and `node`, and `TENANTS.md` stops being a registry.

- **Pros:** small. The repository stops carrying a number. Nothing waits on the API.
- **Cons:**
  - Onboarding stays a substrate commit and five automation runs.
  - The tenant still reads the substrate vault for its keys.
  - The registry can't answer *"is this index really free"*: it doesn't look at the fabric.
- **Verdict:** Rejected. It fixes the collision, but it leaves the onboarding a tenant can't do for
  itself.

### B — The Deevnet API creates tenants

The API holds the registry in its database. A single `create tenant` call does every step in the
table. The provider exposes it as a resource, and the index, keys and attachment come back into the
tenant's state.

- **Pros:**
  - One registry, which checks the live fabric before it allocates.
  - A repository carries no number, so tdemo can stay a reference.
  - Keys reach the tenant through its own state, not the substrate vault.
  - The same provider already carries the IoT resources.
- **Cons:**
  - The API gains credentials for PowerDNS, the core router's resolver, the state store and read
    access to the fabric. A compromised API reaches all of them.
  - The API's database becomes the record of which tenants exist. ADR-0014's durability matters more.
  - Egress is node-local configuration that no API models (§7).
- **Verdict: Chosen.**

### C — Derive the index from the tenant name

A hash of the name, reduced to 1–62.

- **Cons:** 62 slots collide quickly by the birthday bound, and a collision is only discovered at
  apply. It trades a registry for a probability.
- **Verdict:** Rejected.

---

## Decision

**Option B.**

### 1. The API's database is the registry of tenants

- **One registry per site.** The Deevnet API's database is the only record of which tenants exist,
  their index and their status.
- **Retired at cutover:** `deevnet_tenants`, `TENANTS.md` and `make tenant-attachment`. The roles
  that loop over `deevnet_tenants` keep the service and lose the per-tenant work.
- **The numbering doesn't change.** ADR-0002's derivation from one index stands: VRF VNI `10000+n`,
  VNet VNI `20000+10n+i`, subnet `10.{site}.{128+n}.0/24`, reverse zone `{128+n}.{site}.10.in-addr.arpa`.
  Only where the allocation is recorded changes.

### 2. `create tenant` does all of onboarding, idempotently

One call creates everything the table in Context lists, except egress (§7).
- **Each backend step is an ensure.** A step that finds its object already correct changes nothing.
  So a failed create is resumed by calling again, and an existing object is adopted rather than
  duplicated.
- **The API records each step's outcome**, so a partial tenant is visible rather than inferred.
- **It returns what the tenant needs**, all of it into the tenant's own state:
  - index, VRF VNI, subnet and gateway
  - `controller_id` and `node`
  - forward and reverse zone, the update server, the TSIG key name and secret
  - the state endpoint, bucket, prefix, access key and secret key
  - the tenant's own API token
- **Deleting a tenant is refused while the fabric still holds its zone.** The tenant destroys its own
  resources first. Removing the zones, keys and resolver delegation under a live tenant would leave it
  running and unreachable.

### 3. Allocation checks the database and the fabric

- **The API allocates the lowest free index in 1–62.** 63 stays reserved for drills (ADR-0006 §3).
- **"Free" means free in both places:**
  - no tenant row holds it
  - no SDN zone on the fabric carries its VRF VNI, and no VNet carries a tag in its VNet range
- **Why the fabric too:** the database is the registry, but the fabric is where a collision does
  damage. After the database is lost, zones built from the old allocations are still there. An
  allocator that only asked its own database would hand those numbers out again.
- **Allocation is serialised** in the database, so two concurrent creates can't take the same index.

### 4. The API generates secrets; the tenant's state holds the authoritative copy

This is ADR-0012 §4 applied to onboarding.
- **The API generates** the TSIG secret, the state-store secret and the tenant's API token on first
  create.
- **The provider stores them** as sensitive values in the tenant's state.
- **The substrate vault no longer holds tenant keys.** `vault_tenant_tsig_keys` and
  `vault_tenant_state_keys` are retired at cutover. The API stores only the hash of a tenant's token.

### 5. Recovery restores the index, or issues a new one

After a substrate rebuild that loses the API's database, each tenant re-applies (ADR-0012 §5):
- **The provider sends back what its state holds**: the index and the secrets.
- **If the index is still free** (§3), the API keeps it. The tenant's plan is empty, and its VMs,
  subnet and zones are untouched.
- **If a tenant's own zone is what holds the index**, it is the same tenant coming back, not a
  collision. The API keeps it.
- **If another tenant took the index**, the API issues a new one. The tenant's next plan replaces
  its fabric resources and workloads on the new numbering. That is a rebuild of that tenant, and it
  is accepted: it can only happen when the database was lost *and* another tenant was created before
  this one re-applied.
- **Secrets are restored, not regenerated**, so the tenant's DNS updates and state access keep
  working with the keys it already holds.

### 6. The credentials the API holds, and what each can do

| Service | Credential | What it can do | Checked |
|---|---|---|---|
| PowerDNS | the HTTP API key | every zone and key on the server | 4.9.17, 2026-09-17 |
| Core router resolver | an OPNsense API key | the resolver's forwarding entries, and whatever else the key's user is granted | endpoints the `opnsense_dns` role already uses |
| State store | a dedicated MinIO admin user with a scoped policy | create users and policies and attach them | RELEASE.2025-09-07T16-13-09Z, 2026-09-17 |
| Fabric | a Proxmox token with read access to SDN | read zones and VNets | hv02, 2026-09-17 |

**PowerDNS's HTTP API is enabled, which reverses a recorded choice.** Its configuration says:
*"The HTTP API is deliberately NOT enabled. Its key is global to the server, so exposing it would
hand any holder write access to every tenant's zone."*
- **That reason still holds**, and it is why tenants never get the key. They keep writing records over
  RFC 2136 with a TSIG key bound to their zones (ADR-0004).
- **The API holds the key**, as it holds the Omada and broker credentials (ADR-0012 §2).
- **The listener is limited** to the provisioning VM's address.

**The state-store admin policy is narrow in name only.** A user that can create users, create
policies and attach them can grant itself anything. It is a separate, rotatable credential, not a
confinement.

**What was checked against the running versions:**
- **PowerDNS 4.9.17 over its HTTP API:**
  - creating a zone with `nameservers` sets the apex NS, and `default-soa-content` sets the SOA
  - a second create answers `409`
  - a TSIG key is created with a supplied secret, and `PUT` replaces the secret
  - `TSIG-ALLOW-DNSUPDATE` and `ALLOW-DNSUPDATE-FROM` are set with `PUT .../metadata/<kind>`
  - an update signed with the API-created key was accepted, and the same update with a different
    key was refused
- **MinIO RELEASE.2025-09-07T16-13-09Z through its admin API:**
  - adding an existing user replaces its secret, so restore is an ensure
  - re-attaching an attached policy answers `XMinioAdminPolicyChangeAlreadyApplied`, which the API
    treats as success
  - a user holding a policy with only `admin:CreateUser`, `admin:DeleteUser`, `admin:GetUser`,
    `admin:ListUsers`, `admin:CreatePolicy`, `admin:DeletePolicy`, `admin:GetPolicy`,
    `admin:AttachUserOrGroupPolicy` and `admin:ListUserPolicies` could do every tenant operation
- **Proxmox SDN:** `GET /cluster/sdn/zones` answers with `zone` and `vrf-vxlan` per zone (the field
  names in `bpg/terraform-provider-proxmox`'s zone types). On hv02 it returned no zones on
  2026-09-17: tdemo is destroyed and eds has never applied.

### 7. Egress is pulled by the exit node

A default route inside each tenant VRF is FRR configuration on the exit node, which *"the PVE network
API models interfaces and nothing else"* can't carry (`proxmox_node_network` egress tasks).
- **The API publishes the list of tenant VRFs.**
- **An agent on the exit node reads the list** and renders the same `frr.conf.local` the role renders
  today.
- **Why pull:** the API would otherwise need root on a hypervisor. The exit node already reaches
  Platform over `management -> platform`.
- **Until the agent exists**, egress stays with the `proxmox_node_network` role, and a tenant's name
  has to be in its list. That is the one onboarding step still done by hand in the first slice.

### 8. One API per site

Each site runs its own API, with its own registry and backends. ADR-0002's index is per site, and
so are its DNS, state store and fabric. A tenant that moves between sites is created at the other
site's API and gets whatever index is free there.

### 9. The reference tenant is tdemo

- **`deevnet-tenant-tdemo` is the reference tenant.** It holds no index and no attachment. It creates
  itself through the provider like any tenant.
- **`examples/tenant/` in the factory is removed.** Its guard, an index the module rejects, only
  existed because a copied repository carried a number.
- **The rebuild-from-scratch drill applies tdemo** and destroys it again.

### 10. Authentication, first slice

- **Creating, listing and deleting tenants takes the operator token**, the API's existing bearer token.
- **`create tenant` returns a token for the tenant**, stored as a hash. Tenant-scoped calls (ADR-0012
  §2) will take it.
- **Deciding who may create a tenant** separately from what a tenant may do afterwards is left for a
  later record (Open questions).

---

## Consequences

**Onboarding becomes an apply.** A new tenant is a repository copied from tdemo and a `terraform
apply`, with no substrate commit and no automation run, apart from egress until §7's agent exists.

**The substrate vault stops being on the tenant's path.** ADR-0012 §9's credentials file shrinks to
the one value a tenant needs before it can reach the API. Every other key comes back from `create
tenant` into state.

**The API's database is now the record of which tenants exist.**
- **What losing it costs:** each tenant re-applies (§5), and an index can move if another tenant was
  created in between.
- **Why it matters more:** it sits in the same VM as the state store it would be restored from.
  ADR-0014 now covers the registry too, not only device secrets.

**The API holds more.** Its key rewrites any tenant zone, its router key edits the resolver, and its
state-store user is effectively an IAM administrator. A compromised API compromises tenant DNS,
tenant state and tenant IoT together.

**PowerDNS runs its HTTP API**, bound to the provisioning VM, and reverses the comment that kept it
off.

**Two narrow rules join ADR-0012's:**
- `platform -> management`: the API to the tenant hypervisor's Proxmox API port, for reading SDN
- the API to the core router's API. The router answers on each segment's gateway, so this is a rule
  to the router on Platform.

PowerDNS and the state store are on Platform with the API, so they need no rule.

**tdemo comes back.** Its retirement is reversed.

**The factory loses its registry and its example.** It keeps the fabric and the module.

---

## Open questions

1. **Admission.** Who may create a tenant? The first slice uses the operator token, so creating a
   tenant is still an operator act, just not a commit. A tenant self-registering needs an admission
   credential, and a record of its own.
2. **Registry recovery without tenants.** Should the API be able to rebuild its registry from the
   fabric alone (zone ID = name, VRF VNI = index) when the database is lost, before any tenant
   re-applies? That would keep indexes stable even if a new tenant is created first. The first slice
   doesn't do it.
3. **The router key's scope.** Can an OPNsense API user be limited to the resolver's forwarding
   endpoints and reconfigure, rather than sharing the automation user's key?
4. **Encrypting secrets in the database.** The API stores TSIG and state secrets so it can re-ensure
   the services after they are rebuilt. The first slice stores them in the clear in a database that
   publishes no port.

## To confirm when building

- **A resolver delegation added through the API resolves** tenant names through the core router,
  and the reconfigure it needs doesn't disturb other resolution.
- **A restore with the same secrets gives an empty tenant plan**, and a clash gives a plan that
  replaces only fabric-derived resources.
- **The egress agent renders exactly what the role renders today** for the same tenant list.
- **Adopting eds** (zones and key from CHG-0008, never applied) through `create tenant`, with the
  vault's existing secrets supplied, changes nothing on PowerDNS or the state store.

---

## Current state

- **Proposed.**
- The API has a tenant slice on a branch: the registry, allocation, the PowerDNS, resolver, state
  store and fabric backends, and the create, read and delete calls.
- Nothing is deployed. `deevnet_tenants` still drives onboarding.
