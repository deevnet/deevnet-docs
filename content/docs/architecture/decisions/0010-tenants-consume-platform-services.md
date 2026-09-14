---
title: "ADR-0010: Tenants Consume Platform Services"
weight: 10
---

# ADR-0010: Tenants Consume Platform Services; They Are Not Woven Into the Substrate

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-13 |
| **Scope** | What makes a substrate-run service safe for a tenant to depend on, and where issuing a tenant something ends and becoming part of it begins |
| **Extends** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/) §5, which drew the onboarding-versus-recurring line for DNS only |
| **Extended by** | [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) — how §3 is met when the backing service can't confine a tenant itself *(Proposed)* |
| **Related** | [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/), [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) |

---

## Context

Three records have drawn the same line, each for one thing, and none of them says it is a rule:

- **DNS.** [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) §5: *onboarding is
  a substrate act; the tenant lifecycle is not.* The substrate issues a zone and a TSIG key once.
  After that, the tenant writes its own records over RFC 2136, and no substrate commit is involved.
- **Code.** [ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/): a tenant's code lives
  in its own repository. The substrate issues a fabric attachment and does not keep the tenant.
- **State.** [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/): the substrate
  offers a state store, and *the opt-out is what makes the dependency acceptable.*

Because the line was never written down as a rule, the next service arrived without it.

### The first service that weaves a tenant in

The MQTT broker `dv02mqt001v01` was onboarded with the `eds` tenant on 2026-09-07. Its topic
permissions are kept in substrate inventory, and the file says why:

> Kept in inventory rather than the role so that adding a device is an inventory act, like adding a
> tenant.
> — `ansible-inventory-deevnet/mobile/group_vars/mqtt_brokers.yml`

Giving EdS a second LP stand therefore means:
- an entry in `vault_mqtt_users` in the substrate vault
- an entry in `mqtt_acls` in substrate inventory
- a run of the substrate's `mosquitto` role

That is a commit, a vault edit and a substrate apply for something that recurs, which is exactly
the kind of act ADR-0004 §5 says must never need one. The comment's comparison is also the wrong
way round: adding a *tenant* is an onboarding act, while adding a *device* is part of that tenant's
lifecycle.

None of this is a defect in how the broker was built. It is what an unstated rule produces.

### What the rule is

The comparison that makes it concrete is a public IoT platform such as AWS IoT Core. The provider
runs a device registry, a credential and policy engine, a broker, and update delivery. A customer
registering its thousandth device does not change the provider's infrastructure. The customer owns
its firmware, its devices and its signing keys. The provider owns the facilities they are built on.

Stated for Deevnet: **a tenant may depend on the substrate; the substrate must not come to contain
the tenant.**

This matters for more than tidiness. ADR-0004's consequences rest on *stateless substrate holds at
both ends*: the core router can be rebuilt without losing tenant names, because tenant records
don't live in its inventory. Every tenant fact written into substrate inventory erodes that, one
comment at a time.

---

## Options considered

### A — Tenant resources are substrate inventory acts

The broker's current model. Each thing a tenant needs from a shared service is declared in substrate
inventory and applied by substrate automation.

- **Pros:**
  - One mechanism, the one the substrate already uses everywhere.
  - Every change is reviewable in git.
  - No new service surface.
- **Cons:**
  - Every recurring tenant act becomes a substrate commit.
  - Substrate inventory accumulates tenant content, and a tenant can't be rebuilt from its own
    repository alone.
  - The substrate operator stays in the loop for a tenant's whole lifecycle.
  - It contradicts ADR-0004 §5 and ADR-0006 in everything but name.

### B — Scoped platform services

The substrate runs the service. At onboarding it issues the tenant a credential or namespace that
the service confines to that tenant. From then on the tenant uses the service directly.

- **Pros:**
  - It is the model ADR-0004 and ADR-0007 already chose, generalized.
  - Tenant content lives in the service and in the tenant's own code, not in substrate inventory.
  - A tenant is restored by a tenant rebuild.
- **Cons:**
  - Each service needs a way to confine a tenant to its own scope, and not every service has one.
  - The service's data becomes tenant state hosted by the substrate, so it needs to be re-derivable.
  - Changes stop being visible as substrate commits, so visibility has to come from the service.

### C — Tenants run their own copies

Each tenant runs its own broker, its own DNS, and so on.

- **Pros:** complete independence.
- **Cons:**
  - Duplication in every tenant.
  - It is impossible for the things only the substrate can provide: the physical access network,
    the perimeter, and the parent DNS zone.
  - Tenants have no inbound path
    ([ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)), so a
    device on the IoT segment couldn't reach a broker inside one.
- **Verdict:** Rejected. It remains open to a tenant that declines a service (§4).

---

## Decision

**Option B.** Tenants consume platform services; the substrate does not absorb tenant content.

### 1. What a platform service is

A platform service:

1. **is run by the substrate**, as substrate code applied by substrate automation;
2. **is bound to a tenant once, at onboarding**, by issuing a credential, a namespace or both. This
   is the same act that already issues the fabric attachment, the TSIG key and the egress;
3. **is used by the tenant through the service's own interface**, and no recurring tenant act
   requires a substrate commit;
4. **confines each tenant to its scope** (§3);
5. **can be declined where declining is possible** (§4).

### 2. The test

> **Does this recurring tenant action need a substrate commit?**

Onboarding may. Nothing that recurs may.

| Tenant action | Needs a substrate commit today? | Conforms? |
|---|---|---|
| Add, change or remove a DNS record | No, RFC 2136 with the tenant's key | Yes |
| Rebuild or destroy the tenant | No, `terraform apply` in its repository | Yes |
| Keep Terraform state | No, the offered store or its own | Yes |
| Register a device with the MQTT broker | Yes, vault, inventory and the `mosquitto` role | **No** |
| Grant a device access to a topic | Yes, `mqtt_acls` in inventory | **No** |

### 3. Scope is enforced by the service

A tenant's credential must not reach another tenant's scope. The service enforces this itself where
it can.

Where it can't, the gap is written down as a convention rather than presented as a control. This is
the precedent [ADR-0005](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/) set for the
zone apex.

**A service that cannot confine a tenant is not offered as self-service.** Until it can, the
interim arrangement is recorded as debt, not quietly adopted as the model.

### 4. Tenant content is the tenant's to restore

Whatever a tenant creates in a platform service must be re-derivable from the tenant's own code,
as tenant DNS records are re-derivable from tenant Terraform. The substrate may host that content,
but it is never the only copy.

A tenant may decline a service wherever declining is possible, as ADR-0007 allows for state. The
service documents what declining costs.

### 5. Naming

These are **platform services**. The subset that serves devices is **IoT platform services**.

"IoT as a Service" is a fair informal name, with one caution. The market term often includes the
provider supplying and operating the devices themselves. Here the devices are never the platform's
(see [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)).

---

## Consequences

**Existing weaving becomes named debt.** It is not rewritten by this record:

- MQTT device accounts (`vault_mqtt_users`) and topic permissions (`mqtt_acls`) in substrate
  inventory.
- The `edge_devices` group sitting under `infrastructure` in `mobile/hosts.yml`, holding a device
  whose purpose is an application's.
- The `tenant_transit -> iot_backend` zone rule carries the comment *Added for EdS*. The rule
  itself is tenant-agnostic and onboarding-shaped, so only the comment weaves. It is listed so the
  distinction is on record.

**Some services lack the mechanism this requires.** Mosquitto's dynamic security plugin can change
clients and permissions at runtime, but its administrative access is all-or-nothing: a tenant can't
be limited to its own topic prefix
([mosquitto.org](https://mosquitto.org/documentation/dynamic-security/)). The broker therefore can't
be self-service as it stands. How it becomes so is an open question of
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/).

The Wi-Fi controller is a second example, found on 2026-09-14. Its documented API can add and
revoke a per-device key, with the device's VLAN, one key at a time. That is the shape a platform
service needs. But every such write lists the permission *"Site Settings Manager Modify | Network
Config Page Modify"*, the same one that creates SSIDs and ACLs. A credential issued to one owner
for its devices' keys could therefore rewrite the site's wireless configuration. Under §3, device
keys are not self-service until something in front of the controller confines them. Whether a
custom controller role can narrow the grant has not been checked.

[ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) proposes the mechanism for both: a
Deevnet API that holds the backing credentials and confines each tenant, consumed through a
Terraform provider.

**Services get heavier.** A service with a scoped interface is more machinery than an inventory
file. The alternative is cheaper per change and more expensive in aggregate, and its cost stays
hidden until a substrate rebuild has to carry tenant content it should never have held.

**Substrate visibility moves.** Today a new device shows up as a commit. Afterwards it shows up
only in the service. A service that tenants change without commits needs its own record of what
changed, and none of the substrate's services has one yet.

---

## Current state

- **Proposed.** Nothing is implemented by this record.
- **DNS and state already conform** (ADR-0004, ADR-0007). **The MQTT broker does not.**
- **Validated read-only on 2026-09-14**, as recorded in
  [ADR-0011 → Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14):
  - **The broker.** `dv02mqt001v01` doesn't answer: it isn't in DNS, doesn't reply to ping, and its
    MQTT ports are closed. So none of the scoping candidates for making it self-service could be
    tried against it.
  - **The Wi-Fi controller.** It offers per-device keys (PPSK) through its documented API, but only
    under site-wide network permissions. It is a second service with no tenant scope.
- The record is opened alongside
  [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/), which applies it
  to physical devices.
