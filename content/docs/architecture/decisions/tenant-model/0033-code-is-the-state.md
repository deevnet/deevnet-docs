---
title: "ADR-0033: Code Is the State"
weight: -33
---

# ADR-0033: Code Is the State, for the Substrate and for Every Tenant

|  |  |
|--|--|
| **Status** | Proposed. Accepted when the change that moves device secrets into tenant code is built, and a tenant has been rebuilt from its repository with no restore |
| **Date** | 2026-10-05 |
| **Scope** | Where the authoritative copy of everything the site runs lives, and how the site and its tenants recover with no backup on the path. Covers tenant state, device secrets, the Deevnet API's database and audit log, and tenant buckets. |
| **Supersedes** | [ADR-0014: Tenant State Durability](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/), whole |
| **Amends** | [ADR-0012: IoT Platform API](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §4 (the authoritative copy of a device secret), §5 (the restore source) and its audit-log paragraph; [ADR-0015: Tenant Onboarding Through the API](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) (the API's database is a working copy of the registry); [ADR-0026: Object Storage](/docs/architecture/decisions/platform-services/0026-object-storage/) §3 and §4 (no replica) |
| **In conflict with** | [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) (OpenBao's data is kept data) and [ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/) §7 (Keycloak's is); both to be revisited, see [Consequences](#consequences) |
| **Related** | [ADR-0007: Terraform State Custody](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/) §5, [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/) §4, [ADR-0021: Tenant Secrets](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/), [ADR-0025: Identity Directory](/docs/architecture/decisions/platform-services/0025-identity-directory/) §7, [ADR-0031: Deevnet PKI](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §6 |

---

## Context

**The site was designed so that code rebuilds everything.** The substrate is rebuilt from inventory
and its vault. A tenant is rebuilt from its own repository. ADR-0007 §5 made it a rule for tenants:
*"no tenant declares a resource whose value cannot be re-derived from code"*.

**ADR-0012 §4 broke that rule for device secrets.** The API generates each device's broker password
and Wi-Fi key, and *"the tenant's state is the authoritative copy"*. Those secrets sit on devices,
some written over USB into flash. Losing the API's database and a tenant's state together costs a
visit to every device (ADR-0012 §5).

**ADR-0014 answered with a copy of state on separate hardware, taken on every write.** It works, but
it makes the substrate keep data, adds a host to build and watch, and puts a restore on the recovery
path. It also recorded the other way out, its option E: keep device secrets in the tenant's code,
and state is re-derivable again. It left that to ADR-0012's acceptance, which didn't take it up.

**Two later records already lean towards option E.** ADR-0031 §6 has a device generate its own key,
which *"never enters the substrate"*, and the broker trust a certificate instead of a password.
ADR-0021 makes the tenant's repository the authoritative copy of its runtime secrets.

**What the API issues is already re-mintable.** Log tokens and the Grafana password are re-issued by
a reconcile, and a tenant asks for its own index at creation, so a re-created tenant keeps its
identity.

---

## Decision

### 1. Code is the authoritative copy

- **The substrate:** inventory and its vault, in git.
- **A tenant:** its repository, with its secrets in it, encrypted with age to its own recipients, as
  ADR-0012 §9 already delivers its credentials.
- **Nothing else is authoritative.** The API's database, the Terraform state store, the broker's
  auth database and the controller's keys are working copies, rebuilt from code.
- **That includes the tenant registry.** ADR-0015 made the API's database *"the record of which
  tenants exist"*. It becomes a working copy: each tenant's repository names the tenant and the
  index it asks for, and an index doesn't move when the tenant is re-created.

### 2. Recovery never depends on a backup

After losing the substrate, or any part of it:

1. **The substrate is rebuilt from inventory.**
2. **Each tenant is admitted again at its own index.**
3. **Each tenant applies from its repository.** The provider supplies every secret from the
   tenant's code, and the API writes it back into the broker, the controller and its own
   database.

No step restores a backup, and no device is visited.

### 3. Device secrets live in the tenant's code

- **The target is a key generated on the device** (ADR-0031 §6). It never leaves the device, and
  the certificate the Tenant Device CA signs is public.
- **Until then, the tenant supplies each device secret.** The tenant generates the broker password
  and keeps it, age-encrypted, in its repository. The provider passes it to the API as a write-only
  argument, so it never lands in state.
- **The Wi-Fi key the tenant was handed** is kept the same way, and supplied the same way when the
  controller has lost it.
- **This amends ADR-0012 §4.** The API no longer generates a device secret, and the tenant's state
  is no longer its authoritative copy.

### 4. ADR-0012 §5's requirement stands, with a new source

- **A substrate rebuild still never costs a device visit.** The restore path now reads the secret
  from the tenant's code instead of its state.
- **The one case that costs a re-flash becomes the tenant's own loss:** a tenant that loses its
  repository's secrets rebuilds, and re-provisions its devices. Keeping that copy is its
  obligation, as ADR-0010 §4 says of any copy the substrate isn't.

### 5. Terraform state is a convenience again

- **Losing it costs a rebuild, not a loss**, as ADR-0007 sized it. The tenant re-applies, importing
  what still exists.
- **The state store has no replica.** ADR-0014's copy on separate hardware, and its restore
  rehearsal, are withdrawn.
- **Working copies may still sit on a data disk**, so that rebuilding a VM's image doesn't cost every
  tenant a re-apply. That is a convenience, not part of the recovery path.

### 6. Some things are lost on purpose

| Lost in a rebuild | Why that is accepted |
|---|---|
| The API's audit log | Every change a tenant makes is now a commit. Git history of the inventory and of each tenant's repository is the record ADR-0012 asked the audit log to be; the log starts fresh after a rebuild |
| Tenant bucket contents | Tenant data, which the substrate only stores. The tenant keeps its own copy (ADR-0010 §4). ADR-0026's `replicated` option is withdrawn |
| Credentials the API issued to a tenant (its API token, state-store keys) | Re-issued at re-admission, through the handover, like the first time |
| Tenant logs in the log store | Operational data, held for a retention period (ADR-0022 §6). A tenant that needs its logs beyond a rebuild keeps its own copy |

---

## Consequences

**The substrate keeps no data.** No host holds a copy, and nothing needs a backup schedule or a
restore drill to make recovery work.

**The provider and the API change.** Device resources take a tenant-supplied secret as a write-only
argument, and the restore path reads it from configuration. Today's device secrets for `eds` and
`mabell` move from state into their repositories. That is a change record's work.

**Each device registration is a secret-bearing commit** in the tenant's repository, until device
keys replace passwords. A tenant that loses its age keys loses its device secrets; that is the cost
ADR-0014 recorded for option E, and it falls on the tenant.

**Two records conflict with this one, and are revisited separately:**
- **ADR-0016** makes OpenBao's data kept data, with a snapshot copied off the VM. Most of what
  OpenBao holds is delivered from the vault or re-issued. The exception is the Tenant Device CA,
  whose key ADR-0031 has generated inside OpenBao: losing it means a new device CA, and every
  device enrolling again (open question 2).
- **ADR-0025 §7** makes Keycloak's database kept data, because users' credentials exist nowhere
  else. It must be revisited before Keycloak is built.

---

## Alternatives considered

- **ADR-0014's copy on separate hardware, taken on every write.** Withdrawn: it keeps the device
  secrets' only copy in the substrate, needs its own host, and puts a restore on the recovery path.
- **A scheduled backup of state.** Not chosen: it leaves a window, and still puts a restore on the
  path.
- **Wait for device keys before changing anything.** Not chosen: until ADR-0031 §6 is built, every
  new device would add a secret whose only copy is tenant state.

---

## Open questions

1. **Re-admission at scale.** After a full rebuild, the operator re-admits every tenant at its index
   and re-issues its credentials. Should the API accept the tenant's own record of what it was
   issued, so that re-admission is one step per tenant?
2. **The Tenant Device CA's key.** Should it be issued like the Substrate CA, its key in the site's
   vault and imported into OpenBao, so that losing OpenBao doesn't change the device CA? Until device
   keys are built, nothing depends on it.

---

## Current state

- **Proposed. Nothing is built.**
- The API generates device broker passwords and the tenant Wi-Fi keys, and tenant state holds them.
- The state store, the API's database and its audit log are on the provisioning VM's OS disk, with
  no copy.
