---
title: "Substrate and Tenant"
weight: 4
aliases:
  - /docs/architecture/tenant/building/
---

# The Substrate–Tenant Boundary

A site is split into two things that change at different rates and are owned by different people:
the **substrate**, which the operator runs, and the **tenants**, which each run themselves. This
page is about the line between them: what crosses it, in which direction, and what never does.

---

## Two lifecycles

| | Substrate | Tenant |
|---|---|---|
| **Owned by** | The operator | The tenant |
| **Defined in** | Site inventory and automation | The tenant's own repository |
| **Changes** | Rarely, deliberately, as change records | Often, at the tenant's own pace |
| **Lifecycle** | Configured: it exists, and is brought to its declared state | Created and destroyed: `destroy` has to work and mean something |
| **State** | Derived from inventory; nothing to carry | The tenant's declaration, plus the state of what it has declared |

The split is deliberate. A tenant is created and destroyed often enough that its tooling must track
what it owns and remove it cleanly. The substrate is configured, not created, and should not pay for
that. So the two are declared differently — the substrate as procedural configuration, the tenant
declaratively ([ADR-0006](/docs/architecture/decisions/tenant-model/0006-tenant-code-boundary/),
[ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)).

---

## One interface, one credential

Everything a tenant asks of the substrate goes through **one interface**: the site's provisioning
API. The tenant declares what it wants; the substrate decides how and where to build it.

- **Requests go in.** That the tenant exists; its workloads; the names it wants; its devices and
  their keys.
- **Identifiers and credentials come out.** Its index, and everything derived from it; a DNS zone
  and the key that writes to it; a state-store credential; log tokens; a dashboards login.

A tenant holds **one credential**: its own API token. It never holds a hypervisor login, a router
key, a vault password or a controller credential, so there is nothing it could use to reach around
the interface. The substrate, for its part, holds each tenant's issued secrets only to re-ensure
them, and never writes into what the tenant owns — its records, its state, its code.

---

## Admission is the only substrate act

Everything in a tenant's life is its own, except its beginning. **Admission** registers the tenant's
name and issues a single-use enrollment token, delivered encrypted to the tenant
([ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/)). The tenant's first apply
spends it, and receives its own token in exchange.

After that, nothing a tenant does needs the operator: adding a workload, publishing a name, issuing
a device key are all the tenant's own changes
([ADR-0010](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/)).

---

## Issued, not chosen

A tenant chooses nothing that could collide with another tenant or with the substrate. For a tenant
at index `n` on `mobile`, everything derives from that one number
([ADR-0002](/docs/architecture/decisions/tenant-networking/0002-tenant-fabric-numbering/)):

| Object | Derivation | `eds` (index 2) |
|--------|-----------|-----------------|
| Isolated network (its own VRF) | the tenant's name and index | `eds` |
| Subnet, with SNAT | `10.20.{128+n}.0/24` | `10.20.130.0/24` |
| Anycast gateway | `.1` of that subnet | `10.20.130.1` |
| Workload addresses | `.10` upward, by ordinal | `10.20.130.10` |
| DNS zone | `<tenant>.<site>.deevnet.net` | `eds.mobile.deevnet.net` |

Workload addresses are **derived, not leased**, like every address on the site. A tenant's
declaration therefore holds nothing about where it lands — which is why a new tenant is a copy of
the reference tenant with the name changed.

---

## What stays on the tenant's side

The substrate builds a tenant's infrastructure. Three things stay the tenant's own:

- **Its application.** The substrate does not deliver it; the tenant pushes it to its workloads,
  and pushes it again after one is lost
  ([ADR-0034](/docs/architecture/decisions/tenant-model/0034-tenants-deliver-their-own-code/)). The line is between
  *operating* a machine and *owning what runs on it*, and it is a rule rather than a physical fact
  now that operators can reach tenant workloads
  ([ADR-0018](/docs/architecture/decisions/tenant-networking/0018-operator-access-to-tenants/)).
- **Custody of its state.** The site offers a state store; the tenant may keep its state elsewhere
  instead ([ADR-0007](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/)).
- **Its devices.** A tenant declares the devices it owns through the same interface, but a device
  never joins the tenant's network ([Edge Devices](/docs/architecture/edge-devices/)).

---

## Rebuild

Because a tenant declares what it is rather than where it sits, and the substrate issues the rest,
the same declaration rebuilds it on a rebuilt substrate — or, in principle, at another site —
without editing. A tenant's index is never reused while that tenant exists.

How the boundary is implemented — the API and the provider tenants use — is in
[Deevnet Software](/docs/platforms/deevnet-software/). How a tenant uses it is the
[tenant guide](/docs/runbook/tenant/).
