---
title: "Substrate and Tenant"
weight: 4
aliases:
  - /docs/architecture/tenant/building/
---

# The Substrate–Tenant Boundary

A site is split into two things that change at different rates and are owned by different people:
the **substrate**, which the operator runs, and the **tenants**, which each run themselves. This
page is the specification of the line between them: what crosses it, what each side owes the other,
and how far each promise is enforced today. Where another page disagrees with this one, this one
wins.

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

## What every tenant gets

**A tenant's first apply gives it all of this, with nothing further to declare.** A tenant with no
workloads still conforms and still has all of it.

| The substrate provides | The tenant does | Status |
|---|---|---|
| Its index, and every identifier derived from it | Uses what is issued | Enforced |
| Its own API token, in exchange for the enrollment token | Keeps it; it is the tenant's one credential | Enforced |
| An isolated virtual network with a gateway and egress through the perimeter | Nothing, unless it adds workloads | See [How far isolation goes](#how-far-isolation-goes) |
| A delegated DNS zone, and a key scoped to it | Publishes its own records | Enforced |
| A state store prefix and a credential scoped to it | Uses it, or keeps custody elsewhere | Enforced and measured |
| Log partitions, with an ingest and a read token of its own | Sends and reads its logs | Enforced and measured |
| A dashboards organization, with its logs wired in | Builds its own dashboards | Enforced and measured |

---

## What a tenant may declare

**Everything else exists only if the tenant declares it, through the same interface.** None of it
needs the operator. What each one takes to declare is in the [tenant guide's
services](/docs/runbook/tenant/services/).

| A tenant may declare | The substrate provides | Status |
|---|---|---|
| Workloads: how many, how big, whose SSH keys | The VMs, with derived addresses | Enforced |
| Wi-Fi keys | A key that lands its devices on the device segment | Enforced |
| Devices | An entry in its registry | Enforced and measured |
| Broker accounts | An account confined to its own topics | Enforced and measured |
| Device addresses | A fixed address on the device network, and a name in its zone | Enforced |
| Service certificates | A certificate for its own key, under its own names | Enforced |
| Names | Records in its own zone, published by the tenant | Enforced |

**Tenant-facing services still to come are not part of this contract.** Metrics and alerting,
identity, object storage, a development workload and resource quotas are on the
[Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/) roadmap,
and a tenant cannot rely on them yet.

---

## What stays on the tenant's side

**The substrate builds a tenant's infrastructure, and three things stay the tenant's own.**

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

## What a conforming tenant does

**A tenant conforms when all of these are true, whatever it runs.**

1. **It is declared as code** in a repository it owns, which may be its application's own.
2. **It reaches the substrate only through the provisioning API**, and holds no substrate credential.
3. **It declares nothing about where it lands.** Its addresses and identifiers are the ones issued.
4. **It keeps its state safe.** The state holds every credential it was issued, whichever store it
   is in, and it is never committed to a public repository.
5. **It can deliver its own application again**, if it has one.
6. **It keeps its own copy of what it cannot lose.** Nothing it puts in a shared service is safe as
   the only copy.

---

## How far isolation goes

**Some isolation is enforced by the network, some by credentials, and some not yet at all.**

| Between | Held by | Status |
|---|---|---|
| A tenant and the management segment | Perimeter policy | Enforced |
| One tenant's logs and another's | Tokens scoped per tenant | Enforced and measured |
| One tenant's broker topics and another's | Accounts scoped per tenant | Enforced and measured |
| One tenant's state prefix, dashboards or device registry and another's | Credentials scoped per tenant | Enforced and measured |
| One tenant's zone and another's | A key scoped to one zone | Enforced |
| One tenant's workloads and another's | Separate routing domains | Built; no record measures it yet |
| One tenant's devices and another's | Nothing in the network: they share a segment and can reach each other | Not enforced. Each device-facing service authenticates its callers instead |
| An operator and a tenant's workloads | A rule, not the network: operators can reach them | By rule ([ADR-0018](/docs/architecture/decisions/tenant-networking/0018-operator-access-to-tenants/)) |
| One tenant's load and another's | Nothing: there are no quotas, so one tenant can use up the hypervisor | Not enforced |

Measuring workload isolation is on the
[Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/) roadmap.

---

## When a service fails

**Every service is best effort: there is no uptime figure, and no promise of notice before an
outage** ([ADR-0043](/docs/architecture/decisions/tenant-model/0043-tenant-contract-terms/)). A host
restart affects every tenant using that domain.

| When this is down | What stops | What keeps working |
|---|---|---|
| The provisioning API | Every change a tenant declares | Everything already running: nothing at runtime depends on it |
| The state store | Plans and applies for tenants that keep state there | Everything already running |
| Tenant DNS | Tenant names stop resolving | Connections by address |
| The device broker | Messages to and from devices | Each device, as far as its firmware allows |
| The log store | Storing and reading logs | The workloads and devices that send them |
| Dashboards | Viewing dashboards | Everything they read from |

**Recovery is shared.** The operator brings the service back and reconciles each tenant. The tenant
applies its own code again, and pushes its application again. A
[tenant's recovery](/docs/runbook/tenant/recovery/) depends on which part was rebuilt. Two steps are
not yet complete: a plain apply does not bring back lost workloads or republish lost records, so
today the operator has to help
([Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/)).

---

## When the contract changes

**A breaking change gets a change record and a release note before it lands**
([ADR-0043](/docs/architecture/decisions/tenant-model/0043-tenant-contract-terms/)). A change is
breaking when a conforming tenant must do something to keep working, or when its next apply would
replace or reissue something it relies on. The API and the provider are versioned, and their release
notes say what a tenant must do. Until 1.0, a minor release may be breaking.

---

## When a tenant leaves

**A delete removes what a tenant can use and everything it leaves behind.** It removes:
- its network, zones, accounts and keys, and its tokens for the shared services;
- every version of its state;
- every log line in its partitions, before its index can be given to another tenant;
- everything it saved in its dashboards organization, which is then retired under another name.

Its API token is revoked with its name: no token for that name works again until the name is
admitted again.

**Only the audit log remains, on purpose.** It records what each tenant did and outlives every
tenant.

---

## Rebuild

**The same declaration is meant to rebuild a tenant on a rebuilt substrate, without editing,** because
a tenant declares what it is rather than where it sits, and the substrate issues the rest. No tenant
has yet been rebuilt in a drill, or at another site
([Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/)). A tenant's index is never reused while that tenant exists.

How the boundary is implemented — the API and the provider tenants use — is in
[Deevnet Software](/docs/platforms/deevnet-software/). How a tenant uses it is the
[tenant guide](/docs/runbook/tenant/).
