---
title: "ADR-0032: Every Edge Device Belongs to a Tenant"
weight: -32
---

# ADR-0032: Every Edge Device Belongs to a Tenant

|  |  |
|--|--|
| **Status** | Accepted (2026-10-03): already how the platform works. The Deevnet API registers devices only under a tenant, and mabell is a tenant with devices and no workload. |
| **Date** | 2026-10-03 |
| **Scope** | Who may own an edge device. Not where a device attaches, or how it reaches services ([ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §1–§4, unchanged). |
| **Amends** | ADR-0011 §1, the *Ownership* row: "the application, which may or may not be a tenant" becomes "the application, through its tenant" |
| **Related** | [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) (devices registered through the API), [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) (tenant device identity) |

---

## Context

ADR-0011 split a device's concerns across four owners, and gave **ownership** to "the application,
which may or may not be a tenant". That left room for a device whose owner is something other than a
tenant, without saying what that something would be.

Nothing ever filled the room:

- **The API registers devices only under a tenant.** It has no other path:
  `POST /v1/tenants/{name}/devices`.
- **Every per-owner thing the platform issues is a tenant's.** Credentials, Wi-Fi keys, broker
  accounts and topics, log partitions and dashboards are all tenant-scoped, and so is removal.
- **An application with devices and no workload is already a tenant.** mabell owns a gateway and
  runs nothing on the site.

Device identity ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §6) names the
tenant in every device's certificate. A device with no tenant would have no identity to issue.

Being possible is not a reason to allow it. A second kind of owner would need its own registration,
credentials, scoping and removal: a second owner model, for no device that needs one.

## Decision

### 1. Every edge device belongs to a tenant

An application that owns devices does so **through its tenant**. A device is registered under a
tenant, carries that tenant's identity, is reached through that tenant's scoped platform services,
and is removed with it.

### 2. A tenant may have devices and no workloads

An application that runs nothing on the site, only devices, is admitted as a tenant all the same, as
mabell is. "Tenant" means *an accountable owner of things on the site*, not *something running
virtual machines*.

### 3. Nothing else in ADR-0011 changes

- **Ownership is still not network placement.** A device does not join its tenant's network.
- **Attachment is still by trust class.** The segment depends on how far the device's firmware is
  trusted, not on whose tenant it is.
- **Access is still scoped per owner**, and the owner is now always a tenant.
- **Substrate devices are not edge devices.** Switches, access points, hypervisors and the Builder
  pass ADR-0011's ownership test as substrate, and their identity is the substrate's.

---

## Consequences

**One owner model serves everything a device needs.** Admission, credentials, Wi-Fi keys, broker accounts, device certificates, logs
and removal all hang off a tenant, and nothing has to be invented for a device without one.

**Device identity is tenant identity.** The Tenant Device CA, the tenant in each certificate's OU and
URI, and per-tenant authorization at the broker all follow directly.

**A tenant can be as small as one device.** Admitting a tenant for a single device is the expected path, not a
workaround.

---

## Alternatives considered

- **Rejected: a registry of non-tenant owners.** It keeps ADR-0011's wording literally true, but needs
  a parallel owner model (registration, credentials, scoping, removal) that no device needs, and
  device identity would need an owner type that is not a tenant.
