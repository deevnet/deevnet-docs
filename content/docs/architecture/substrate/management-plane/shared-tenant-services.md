---
title: "Shared Tenant Services"
weight: 2
---

# Shared Tenant Services

### Purpose

Shared tenant services are the services the substrate runs **for tenants**, so that each tenant
doesn't have to run its own. The substrate owns the service; the tenant owns what it puts in.

Some of them can't exist inside a tenant at all. A tenant has no inbound path, so a device on the
IoT segment couldn't reach a broker running inside one. And a tenant zone needs a parent that only
the substrate holds.

---

## 1. Where They Sit

| Segment | Reached by | Domains |
|---------|------------|---------|
| **Platform** | Tenants, over the tenant perimeter; operators, from management | Provisioning, Identity, Tenant observability |
| **IoT backend** | Devices on the IoT segment | Device messaging |

Shared tenant services never sit on the management segment. The segmentation standard says tenant
networks must not reach it directly, and neither may the IoT backend segment.

Where one shared tenant service has to write to another on a different segment, a **narrow rule**
allows that one host to reach that one port, and nothing else. An example is the platform API
writing a device's broker account.

---

## 2. Domains

| Domain | Segment | Holds | Decided in |
|--------|---------|-------|------------|
| **Provisioning** | Platform | The **state store** for tenant infrastructure code; the **platform API** for what backing services can't scope themselves | [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/); [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) *(Proposed)* |
| **Identity** | Platform | **Tenant authoritative DNS**: one delegated zone per tenant; later, a directory | [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) |
| **Tenant observability** | Platform | Logs and metrics tenants share | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) |
| **Device messaging** | IoT backend | The **message broker** devices connect to, and its authentication store; later, other device rendezvous services | [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) *(Proposed)* |

### 2.1 Provisioning

Provisioning holds what a tenant's `apply` talks to.

- **The state store is offered, not mandated.** A tenant may keep its state elsewhere and carry its
  own custody. A dependency a tenant chooses is acceptable in a way an inherited one is not.
- **Each tenant's credential is scoped by the store** to that tenant's own prefix. A tenant is
  refused another tenant's state by the server, not by its own code declining to ask.
- **The platform API** fronts services whose own interface can't confine a tenant. Examples are a
  per-device wireless key, and a broker account limited to the tenant's topics. The API holds the
  backing credentials, and the tenant never holds one that could go around it.
- **The API provisions; it is never in a device's path.** Devices talk to the broker and the
  wireless network, never to the API.

### 2.2 Identity

- **Each tenant gets a delegated zone** under the site zone, and writes its own records into it.
  The core network's resolver forwards the zone to this service, so tenant records never enter the
  resolver's own configuration
  ([Naming and Addressing](/docs/architecture/substrate/naming-and-addressing/)).
- **A per-zone key confines each tenant** to its own zone.

### 2.3 Tenant observability

- Tenants reach it over the tenant perimeter, as they do the rest of the platform segment.
- It is separate from substrate observability, which sits on management where tenants can't reach
  it.

### 2.4 Device messaging

- **It sits on the IoT backend segment**, where devices on the IoT segment can reach it.
- **The broker authenticates from its own store**, which lives beside it. Losing the provisioning
  domain therefore never disconnects a device.
- **Only devices on the IoT segment get a broker account.** The IoT vendor segment is isolated from
  every internal segment, so an account for one of its devices could never be used.

---

## 3. Onboarding Versus Lifecycle

Binding a tenant to a shared service is a substrate act, done once. Everything after that is the
tenant's own act, through the service's interface.

| | At onboarding (substrate) | Recurring (tenant) |
|---|---|---|
| **Identity** | Create the tenant's zone and issue its key | Add, change and remove records |
| **Provisioning: state** | Issue a credential scoped to the tenant's prefix | Plan and apply against it |
| **Provisioning: platform API** | Issue one API credential | Register devices, issue their wireless keys and broker accounts |
| **Tenant observability** | *To be defined* | *To be defined* |

A recurring tenant action that needs a substrate commit fails the test in
[How Tenants Consume the Plane](/docs/architecture/substrate/management-plane/#how-tenants-consume-the-plane).
The existing debt is named in
[ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/): device broker
accounts and topic permissions are still kept in substrate inventory.

---

## 4. Tenant Content Is the Tenant's to Restore

- **What a tenant writes into a shared service can be rebuilt from the tenant's own code.** Records
  come from the tenant's infrastructure code, and so do device registrations.
- **A service's database is hosted tenant state, not the source of truth.** If a substrate rebuild
  loses it, each tenant re-applies its own code to restore it.
- **A substrate rebuild never costs a device visit.** Secrets a device already holds are restored
  from the tenant's state, not regenerated
  ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §5, *Proposed*).
- **A tenant may decline a service** wherever declining is possible, as it can for the state store.
  The service documents what declining costs.

---

## 5. Isolation Model

Isolation here means **no tenant code runs in this tier**. A service still serves tenants, but no
tenant can execute in it or write outside its own scope.

| Attribute | Value |
|---------|------|
| **Workload type** | Substrate-owned, tenant-facing |
| **Change cadence** | Slow and deliberate |
| **Tenant access** | Through each service's own interface, confined to the tenant's scope |
| **Blast radius** | A host restart affects every tenant using that domain; accepted at lab scale |

Tenant DNS and the state store sit in different domains because they fail differently. If tenant
DNS is down, tenant names stop resolving. If the state store is down, no tenant can change
anything.
