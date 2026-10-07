---
title: "ADR-0035: A Fixed Address for a Tenant's Device"
weight: -35
---

# ADR-0035: A Fixed Address for a Tenant's Device

|  |  |
|--|--|
| **Status** | Proposed (2026-10-06). Built by [CHG-0044](/docs/changes/2026/0044-tenant-device-addresses/); Accepted when that change completes. |
| **Date** | 2026-10-06 |
| **Scope** | How a tenant's device gets the same address every time on the device network, and what its name is. Not what may reach the device ([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/), unchanged), and not its identity ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §6). |
| **Amends** | [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) open question 2 and [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §3 and open question 3: "leases from the IoT pool" becomes "leases from the pool unless its tenant reserves it an address". "No substrate host record" stands. |
| **Related** | [ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/) (every device has a tenant), [ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/) (a tenant's names are in its own zone), [ADR-0009](/docs/architecture/decisions/substrate/0009-network-device-config-ownership/) (inventory owns the segment), [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) (a tenant's code restores it) |

---

## Context

**A tenant's device leases whatever address the pool gives it.** ADR-0011 decided that on
2026-09-15: an application-owned device takes no substrate host record, leases from the IoT pool,
and is named in its owner's zone. The reasoning was that a device's identity is its credential, not
its address, and that device churn should never become a substrate commit.

Both halves of that reasoning still hold, and neither says a device's address has to move.

**Some devices are dialed, not just heard from.** A gateway with a web page, or a device someone
connects to for diagnosis, is found by address or by a name that needs one. On the pool that address
changes whenever the lease does.

**The one device that had a fixed address had it as a substrate host.** The Ma Bell gateway was
declared in inventory, with a reservation, an A record and two aliases in the substrate's zone. Since
[ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/) it
belongs to a tenant, and a tenant's device in inventory is exactly the substrate commit ADR-0011 set
out to avoid.

**Two constraints shape the answer.**

- The device network is the substrate's, one subnet shared by every tenant. A tenant can't own a
  block of it the way it owns its overlay subnet.
- A MAC address is copied by anyone on the segment. Whatever is built on one can't be a control.

## Decision

### 1. A fixed address on the device network is a tenant service

A tenant asks the Deevnet API for a fixed address for a device it has registered, and the device then
gets that address every time it joins. It is asked for like every other tenant service: declared in
the tenant's own code, and removed the same way.

Asking is optional. A device nobody asked for leases from the pool, as before.

### 2. The reservation is for the device's registered MAC

The registry entry already carries an optional MAC. A device that is to hold an address must have
one, and it is the only copy: changing it moves the reservation, so replaced hardware is found where
the old hardware was.

### 3. The address is allocated from a range set aside for tenants

A device network is divided in three, in inventory:

| Part | Holds | Written by |
|---|---|---|
| Low | The gateway and substrate-owned hosts on the segment | Inventory |
| Middle | Tenants' device addresses | The Deevnet API |
| High | The dynamic pool | The DHCP server |

On the IoT network of the mobile site that is below `.25`, `.25` to `.200`, and `.201` to `.254`.

The API gives a device the lowest free address in the tenant range, or the one the tenant names if
it is free. One tenant may hold a bounded share of the range, so a shared range can't be emptied by
one tenant.

### 4. The tenant's state remembers the address

The API allocates; it does not derive. A tenant's state records the address it was given and asks
for the same one whenever it re-applies, so the address survives the loss of the API's own records
([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)).

### 5. The address is the substrate's, the name is the tenant's

Reserving an address publishes `<device>.<tenant zone>` for it, in the tenant's own zone, and
removing the reservation removes the name. A tenant may publish further names for an address it
holds, and for no other address on the device network.

Nothing is written to the substrate's zone.

### 6. An address is addressing, never authorization

A reservation says where a device is found. It is not evidence of who is speaking
([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/)
§2), and no service may treat it as one.

It also changes nothing about what can reach the device. The zone policy decides that, and this
record adds no rule to it.

### 7. A clash never says who holds what

One MAC holds one address on a network, and one address has one holder, across all tenants. A request
that would break either is refused without naming the other party. A MAC or address that a
substrate host holds is refused the same way.

### 8. Only substrate-owned hardware is an inventory host on a device network

A tenant's device is not declared in inventory. Its address and its name come from its tenant,
through the API.

### 9. Two writers share the DHCP server's reservations, and neither touches the other's

Inventory's reservations and the API's sit in one table. Each is marked with its writer, each writer
changes only its own, and a writer that finds the other's row in its way stops instead of taking it
over.

The API's reservations are derived state. A rebuilt router has lost them, and a reconcile of the
tenant puts them back.

## Consequences

- **A device can be found at one address and one name**, from wherever the zone policy already allows
  it to be reached. Today that is the operator networks.
- **The registry's MAC now does something.** It was a label; it is now what an address is reserved
  for. It is still never an authorization input.
- **The API's uniqueness rule for a MAC changes for devices that hold an address.** The registry
  still lets two tenants record the same MAC. Only one of them can hold an address for it, and the
  refusal the second gets tells it that the MAC or the address is taken on that network, which is
  more than the API disclosed before.
- **A tenant can hold an address for a MAC that isn't its device's.** Nothing proves a tenant owns
  the hardware behind a MAC. The cost to another tenant is a refused reservation, never access.
- **The API writes to the router's DHCP server as well as its resolver.** The router credential it
  uses covers more than before, which
  [CHG-0038](/docs/changes/2026/0038-reconcile-restores-everything/) has to allow for when it
  narrows that credential.
- **A device network's dynamic pool is smaller.** On the IoT network it goes from 101 addresses to 54.
- **The Ma Bell gateway leaves inventory**, and its names move from the substrate's zone to its
  tenant's.

## Alternatives considered

- **Leave it as it was: pool only.** Rejected. It left the one device that needed a fixed address
  declared as a substrate host, against ADR-0032.
- **A block of the device network per tenant, derived from the tenant's index.** This is how a
  workload's address is derived, and it would need no allocation. Rejected: a site holds up to 62
  tenants and the device network is one /24, so a block would be four addresses with nothing left
  for the pool.
- **The API allocates and the tenant can't ask for an address.** Simpler. Rejected: after the API's
  records are lost, each device's address would depend on the order tenants re-applied.
- **The tenant always names the address.** Fully in the tenant's code. Rejected as the only way:
  every tenant would have to find a free address on a network it can't see. Kept as an option.
- **A static address in the device's firmware.** Needs nothing from the substrate. Rejected: nothing
  stops two tenants choosing the same one, and the DHCP server would lease it to a third.
- **The device's name in the substrate's zone.** This is what the Ma Bell gateway had. Rejected:
  it makes a tenant's device a substrate commit, and ADR-0004 already gives a tenant a zone.
- **A larger device network.** A wider subnet would make room for a block per tenant. Not chosen now:
  it renumbers a live segment, and allocation from a shared range is enough for a lab.

## Open questions

1. **Reverse DNS for a device's address.** The reverse zone for a device network is the substrate's,
   and no PTR is published for a tenant's device. Publishing one would mean the API writing host
   entries on the router's resolver, a second write surface there.
2. **A device network other than IoT.** The vendor-device network has no tenant range. Nothing asks
   for one.
3. **Whether a tenant workload should reach its device at this address.** ADR-0020 §4 forbids a rule
   from a device network to a tenant network, and this record doesn't reopen it. The other
   direction has not been asked for.

## Current state

Not built. [CHG-0044](/docs/changes/2026/0044-tenant-device-addresses/) builds it and moves the Ma
Bell gateway to its tenant.
