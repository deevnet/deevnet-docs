---
title: "ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider"
weight: 12
---

# ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-14 |
| **Scope** | How a tenant reaches an IoT platform service whose own interface can't confine it to its scope, and what the substrate builds so it can |
| **Extends** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §1 and §3, which require a scoped service but don't say how one is built when the backing software can't scope itself |
| **Answers, in part** | [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) open questions 1 (scoped registration) and 3 (per-device Wi-Fi keys) |
| **Related** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/), [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/) |

---

## Context

### The rule has no mechanism for IoT

ADR-0010 set the test for a platform service: *does this recurring tenant action need a substrate
commit?* For IoT, two actions fail it today:
- registering a device with the MQTT broker
- granting it topics

ADR-0011 adds a third that it wants per device: a Wi-Fi key.

ADR-0010 §3 also says a service that can't confine a tenant *"is not offered as self-service."*
The validation on 2026-09-14
([ADR-0011 → Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14))
found that **neither backing service can confine a tenant:**

- **The broker.** Mosquitto's dynamic security plugin changes clients and permissions at runtime,
  but its administrative access is all-or-nothing
  ([mosquitto.org](https://mosquitto.org/documentation/dynamic-security/)).
- **The Wi-Fi controller.** Omada 6.3.0.45 documents per-device PPSK keys, each with its own VLAN.
  But every such write lists the permission *"Site Settings Manager Modify | Network Config Page
  Modify"*, the same one that creates SSIDs and ACLs.

Handing a tenant either credential hands it the whole service.

### How DNS solved the same problem

The substrate has already chosen the same shape three times:

| Record | What the substrate issues | What the tenant does after |
|---|---|---|
| [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) | A zone and a TSIG key, once | Writes its own records over RFC 2136 |
| [ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/) | A fabric attachment | Keeps its desired state in its own repository |
| [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/) | A state-store credential, declinable | Keeps its own Terraform state |

DNS had one advantage the IoT services lack: **a protocol with scoping built in.** The tenant
module records why it didn't use the PowerDNS HTTP API:

> PowerDNS's HTTP API has a single global key, so publishing through it would let any tenant write
> any zone. A per-zone TSIG key is scoped by the server
> — `deevnet-tenant-factory/modules/tenant/versions.tf`

That is the same situation the broker and the controller are in now. There is no MQTT or Omada
equivalent of a per-zone TSIG key, so if the scoping is to exist, Deevnet has to supply it.

### What the application owner actually wants

The goal is IoT platform services in the manner of a public IoT platform. The platform supplies
the facilities for connecting, identifying and serving devices. The owner writes the firmware,
owns the devices and their keys, and declares what it wants in its own Terraform.

---

## Options considered

### A — Hand tenants the backing credentials

Give each tenant an Omada Open API client and dynsec admin rights.

- **Pros:** nothing to build.
- **Cons:** neither credential can be narrowed to one tenant, so each tenant could rewrite the
  site's wireless and every other tenant's broker permissions. It fails ADR-0010 §3 outright.
- **Verdict:** Rejected.

### B — The substrate acts per device

Today's model. Device accounts, ACLs, and eventually keys are declared in substrate inventory and
applied by substrate automation.

- **Pros:** it works, it's reviewable in git, and it's the pattern the substrate uses everywhere.
- **Cons:** every device is a substrate commit, which fails the ADR-0010 test.
- **Verdict:** Rejected. It stays as the recorded debt ADR-0010 lists until this record is built.

### C — Tenants run their own broker and Wi-Fi

- **Cons:** already rejected by ADR-0010 Option C. There is one physical access network, and tenants
  have no inbound path for devices to reach.
- **Verdict:** Rejected.

### D — A Deevnet API, consumed through a Terraform provider

The substrate runs an API that holds the backing credentials, confines every request to the
calling tenant, and drives the backing services. Deevnet publishes a Terraform provider for it,
and tenants declare devices in their own Terraform.

- **Pros:**
  - It meets ADR-0010 §3 for services that can't scope themselves.
  - Tenant desired state stays in the tenant's repository (ADR-0006) and state (ADR-0007).
  - **The backing implementation can change without the tenant noticing:** a different broker, a
    different controller, a different Wi-Fi vendor.
  - It gives the platform one place to record what changed, which ADR-0010 noted no service yet has.
- **Cons:**
  - It is a new service to build, run, secure and version.
  - It holds privileged credentials, so its compromise is a site-wide compromise of those services.
  - A provider brings schema-versioning discipline and a distribution problem (§7).
- **Verdict: Chosen.**

**An API without a provider** was also considered. It is viable for imperative work, but desired
state would then live in scripts or in the API's own database rather than in tenant Terraform. That
breaks ADR-0010 §4's re-derivability. The provider is the primary interface; the API stays callable
directly for work that isn't declarative.

---

## Decision

**Option D.**

### 1. Two planes; the tenant sees only the control plane

```
                      DEEVNET IoT PLATFORM SERVICES
 ┌───────────────────────────────────────────────────────────────┐
 │ CONTROL PLANE        Deevnet API  ·  Terraform provider       │
 │                                                               │
 │  v1:     device registry · Wi-Fi key binding ·                │
 │          broker account binding                               │
 │  later:  identity/PKI · policy · firmware release hosting ·   │
 │          OTA/jobs · observability      (each its own record)  │
 └───────────────────────────────┬───────────────────────────────┘
                                 │ holds the backing credentials;
                                 │ confines every call to one tenant
 ┌───────────────────────────────┴───────────────────────────────┐
 │ DATA PLANE           substrate implementations, never         │
 │                      tenant-facing                            │
 │                                                               │
 │  Wi-Fi controller + IoT VLANs · MQTT broker · DNS/DHCP ·      │
 │  artifacts                                                    │
 └───────────────────────────────┬───────────────────────────────┘
                                 │ devices use data-plane services
                                 │ only
                    application-owned edge devices
                                 │
 ┌───────────────────────────────┴───────────────────────────────┐
 │ TENANT / APPLICATION                                          │
 │                                                               │
 │  firmware · signing keys · backend services ·                 │
 │  Terraform (desired state)                                    │
 └───────────────────────────────────────────────────────────────┘
```

- **The API is the only tenant-facing control surface for IoT services.** The Omada controller and
  the broker's administrative interface are implementations behind it. No tenant holds their
  credentials.
- **Devices never call the control plane.** They connect to Wi-Fi and the broker as they do today.

### 2. Scope is enforced by the API, and issued once

- **One credential at onboarding.** At onboarding the substrate issues each tenant one API
  credential. It is the same act, and the same shape, as the TSIG key (`vault_tenant_tsig_keys`)
  and the state key (`vault_tenant_state_keys`).
- **Every object belongs to exactly one tenant.** The API refuses any read or write outside the
  calling tenant's objects.
- **The backing credentials are the API's alone**, held by the substrate: the Omada Open API client
  and the broker's admin account.

This is how ADR-0010 §3 is met for a service whose own interface can't meet it. The confinement is
a control enforced by the API, not a convention, because the tenant never holds a credential that
could go around it.

### 3. Version 1 is a registry and two bindings

v1 covers exactly the actions that fail ADR-0010's test. Resource names below are working names.

| Resource | What it is | Confined by the API to |
|---|---|---|
| `deevnet_iot_device` | A registry entry: name, trust class (`iot` or `iot_vendor`), optional MAC | The calling tenant |
| `deevnet_iot_wifi_key` | A per-device PPSK key | **The VLAN of the device's trust class.** The tenant can't choose a VLAN, so no tenant network ever reaches the air (ADR-0011 Option B stays rejected). |
| `deevnet_iot_broker_account` | An MQTT account for the device, with its topic permissions | Topics under the tenant's prefix, `<tenant>/…`. The existing ACLs already follow this: `eds/lightstand/…`. |

Everything else in the layer model is a later layer:
- identity and PKI
- policy
- firmware release hosting
- OTA and jobs
- observability

Each needs its own record. OTA and jobs in particular are imperative and are unlikely to be
Terraform resources at all.

### 4. The API generates device secrets; the tenant keeps them

- **Generated on create.** The API generates the Wi-Fi key and the broker password. The provider
  returns them as sensitive attributes, and they land in the tenant's own state (ADR-0007: its
  prefix in the offered store, or its own backend). The owner provisions them onto the device.
- **The substrate stores only what authentication needs.** For the broker that is a password hash.
  A PPSK key is stored by the controller in usable form because the AP needs it, which is a
  property of the protocol, not a copy kept for the substrate's use.
- **Rotation is a replacement.** Replace the resource and re-provision the device.
- **Device identity is not firmware signing.** If identity PKI is added later, it is device
  identity only. Firmware signing keys never reach the substrate (ADR-0011 §4).

### 5. Tenant content is re-derivable from tenant Terraform

- **The API's database is hosted tenant state, not the source of truth** (ADR-0010 §4).
- **After a substrate rebuild** that loses it, each tenant's `terraform apply` restores its objects.
  The provider reads them as missing, and Terraform plans them again.
- **The cost:** a re-created key or password is **new** unless secrets can be supplied back, so
  re-deriving the platform could mean re-provisioning every device. That is Open question 2. It
  decides whether a substrate rebuild costs one `terraform apply` per tenant or a USB visit per
  device.

### 6. One object class is carved out of ADR-0009

- **ADR-0009 still holds for site structure.** Inventory remains the only declaration of site
  structure: networks, SSIDs, AP settings, and **one PPSK profile per trust class**. The controller
  applies that inventory, as ADR-0009 decided.
- **The carve-out: keys inside those profiles are tenant content**, written by this API, not by
  inventory.
- **The existing guard already fits.** ADR-0009's automation never deletes objects inventory
  doesn't declare (§7), so it leaves the keys in place already. What changes is its report: it has
  to recognise API-owned keys as expected rather than list them as drift.
- **This extends ADR-0009 for one object class; it does not supersede it.**

### 7. Placement and distribution

- **The API runs as a substrate platform service on the platform segment.**
  - Tenants reach it over `tenant_transit -> platform`, which the declared zone policy already
    allows.
  - Operators reach it from management.
  - Nothing on the IoT segments needs a path to it.
- **The provider is versioned like the tenant module.** Tenants pin it and commit the lock file,
  as they already do for `bpg/proxmox` and `hashicorp/dns`.
- **How the binary reaches a tenant is open** (Open question 7). Every provider tenants use today
  comes from the public registry, and this would be the first that doesn't.

---

## Consequences

**ADR-0010's failing rows become conformant once this is built.** Registering a device, and
granting it topics and a Wi-Fi key, become `terraform apply` in the tenant's repository. Until then
they stay recorded debt.

**The substrate gains a privileged service.** The API holds credentials that can rewrite the
site's wireless configuration and every broker permission. Its authentication, audit log and
availability are platform responsibilities. A compromised API is a site-wide compromise of those
services, which is also true of the credentials today, but they currently sit in the vault rather
than in a running service.

**The platform gets a record of what changed.** ADR-0010 noted that a service tenants change
without commits needs its own record, and that none had one. The API's audit log is that record
for IoT.

**Substrate rebuild and tenant re-apply become coupled.** Restoring IoT service after losing the
API's database needs every tenant to apply again, and possibly to re-provision devices (§5).

**Deevnet owns a public schema.** A breaking provider change needs versioning discipline like
`tenant-module-vX.Y.Z` (ADR-0006), and a deprecation path.

**It is the first service placed where the declared policy expects.** Today's tenant-facing
services, tenant DNS and state, sit on the management segment. Tenants reach them only because the
core router currently passes everything (ADR-0011 → Validation). This record doesn't move them, but
it shouldn't repeat that.

**It depends on data-plane work that isn't done.** As of 2026-09-14:
- the broker doesn't answer
- PPSK is untested on the AP, pending [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)
- the IoT segments aren't enforced, pending [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)

An API over a data plane that doesn't enforce anything confines nothing that matters.

**Building it is real work:** an API service, plus a provider on the Terraform Plugin Framework in
Go. The Builder already provides Go.

---

## Open questions

1. **Which broker sits behind the API?** Mosquitto with dynsec driven by the API, or a broker with
   native tenant namespaces. The API makes the choice swappable, which is the point of the
   decoupling, but v1 needs one.
2. **Are secrets restorable after a substrate rebuild?** Either the tenant supplies its existing
   secrets back on re-create, making them restorable and avoiding a re-provision, or every rebuild
   means re-provisioning devices. It shapes the provider schema from v1.
3. **Can a custom Omada role narrow the API's own controller credential?** This is defence in
   depth for §2, not tenant scoping. It wasn't checked.
4. **Where does the API's database live, and how is it backed up?** It is hosted tenant state:
   losing it is recoverable (§5), but not free.
5. **How does a registry entry relate to ADR-0011 open question 2?** A device could still have a
   substrate host record, or lease from the IoT pool and be named in its owner's zone. The provider
   could compose with the existing `hashicorp/dns` path rather than wrap DNS.
6. **Where is topic confinement enforced?** The API can validate permissions before writing them,
   or the broker can enforce per-tenant patterns, or both.
7. **How does the provider binary reach tenants?** The leaning is a network or filesystem mirror on
   the artifact server, consistent with how it already stages images. A private registry or
   `dev_overrides` are the alternatives.
8. **How is the tenant's API credential delivered?** Tenants today read their TSIG and state keys
   out of the substrate vault (`ansible-vault view` in the tenant Makefile), which means the tenant
   operator needs substrate vault access. That is a coupling this record doesn't fix. Is v1
   delivered the same way, or issued so the tenant never touches the substrate vault?

---

## Current state

- **Proposed.** Nothing is built.
- The broker accounts and topic permissions remain in substrate inventory as ADR-0010 debt. No
  Wi-Fi keys are per device.
- Acceptance waits on ADR-0010 and ADR-0011, and at least on Open questions 1, 2 and 7.
