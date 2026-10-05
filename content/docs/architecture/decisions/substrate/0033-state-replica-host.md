---
title: "ADR-0033: State Replica Host"
weight: -33
---

# ADR-0033: The State Replica Is a Dedicated Raspberry Pi on the Management Segment

|  |  |
|--|--|
| **Status** | Proposed. Accepted when the change that builds it has restored the store from it ([ADR-0014](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/) §7) |
| **Date** | 2026-10-05 |
| **Scope** | Where ADR-0014's on-write copy and the Deevnet API's database backups live: the host, its hardware, its network, and how it stays independent of what it protects. Not a copy kept offline and off the site, which is undecided, and not storage for data disks that move between hosts (the [Shared Storage](/docs/roadmap/infrastructure/mobile/shared-storage/) project). |
| **Extends** | [ADR-0014: Tenant State Durability](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/), answering its open question 1; [ADR-0026: Object Storage](/docs/architecture/decisions/platform-services/0026-object-storage/), answering its open question 2; [ADR-0025: Identity Directory](/docs/architecture/decisions/platform-services/0025-identity-directory/), answering its open question 3 |
| **Related** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/tenant-networking/0001-tenant-network-fabric/) and [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/) (substrate services stay off tenant compute), [ADR-0008: Host Naming](/docs/architecture/decisions/naming-and-dns/0008-host-naming-site-codes/) (the role code), [ADR-0013: Domain VMs](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/) |

---

## Context

**ADR-0014 decided that every write to the tenant state store is copied to separate hardware, and
left open where.** The copy is taken on write, shares no physical disk and no host with the store, is
on site and needs no internet (§3). The API's database is backed up to the same place on a schedule
(§5). ADR-0026 made the copy a replication target for a second object-storage instance, and also the
target for tenant buckets that opt in. ADR-0025 asked whether Keycloak's backups go there too.

**The site has four kinds of machine, and only one of them is free to hold it.**

| Machine | Fit |
|---|---|
| The substrate hypervisor | Runs the provisioning VM, which holds the store. A second VM there shares its host and disk, which §3 rules out |
| The tenant hypervisor | Tenant compute. ADR-0001 and ADR-0004 keep substrate services off it, and the substrate's recovery would then depend on tenant hardware |
| The Builder | Has no site (ADR-0008) and is away at times. A copy that pauses whenever it is away reopens the window ADR-0014 closed |
| The Pi lab's four Raspberry Pi 4s | Separate hardware, small, always on if wired and powered |

**The data is small.** Each tenant's state is kilobytes to megabytes, the API's database is small,
and tenant buckets that opt in are capped by their quotas (ADR-0026).

---

## Decision

### 1. A dedicated Raspberry Pi 4

- **One of the Pi lab's Raspberry Pi 4s leaves the lab and becomes a substrate host.** `rpi001`
  becomes `dv02rep001p01`, under a new role code, `rep` (replica). The lab keeps three.
- **It is a substrate host, not lab compute.** It is built and managed like the other substrate
  hosts, and no tenant uses it.

### 2. It boots and stores on a USB SSD

- **The SSD holds the system and the data.** microSD cards wear out under the constant small writes
  of a versioned store.
- **The data is the same data ADR-0014 §4 describes:** substrate-only credentials, encrypted at rest
  (open question 1), and treated as a copy of every opted-in tenant's state.

### 3. It is wired, on the management segment

- **One wired interface, on management**, carrying both replication and its own management.
- **Not the storage segment.** It is not built, a minimal site may omit it, and it must not carry
  anything but storage traffic ([Network Segmentation](/docs/standards/network-segmentation/) §3).
  A one-interface host there would need a second network for its own management.

### 4. It holds three things

| What | How | Decided by |
|---|---|---|
| The state bucket, and tenant buckets that opt in | A second object-storage instance, the replication target | ADR-0014 §3, ADR-0026 §3 |
| The Deevnet API's database | Scheduled backups | ADR-0014 §5 |
| The identity directory's database | Scheduled backups, once Keycloak exists | ADR-0025 §7 |

### 5. It stands alone at a rebuild

- **It needs nothing that runs on the substrate hypervisor** to boot and serve: not its DNS, not
  OpenBao, not the Deevnet API. ADR-0014 §6 restores the store from it **first**, so it must be up
  while everything it protects is down.
- **Its certificate comes from the Substrate CA through Ansible**, like every substrate host's
  ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)), so issuing it needs no
  running service either.

### 6. It may be taken offline on a schedule

- **The hardware is also used offline for rare, scheduled operator work.** For those windows the
  replica is down, and the store has no copy.
- **This is not the Builder's case.** The Builder is away routinely and unpredictably; these windows
  are rare and chosen. Run them when no tenant is applying.
- **Replication must catch up afterwards on its own**, without a manual resync (to confirm when
  building).

---

## Consequences

**ADR-0014's §3 can now be built.** Its open question 1 is answered, and so are ADR-0026's question 2
and ADR-0025's question 3. ADR-0014 still needs its §7 rehearsal before it is accepted, and the change
that builds this host is where that happens.

**The site gains a host class and a machine to patch.** `rep` is a new role, with its own inventory
group, image and switch port. The Pi lab drops to three slots.

**The copy is beside the original.** Losing the whole site (theft, fire or damage in transit for a
mobile site) loses both. A copy kept offline and off the site would cover that, and is not decided.

**The store is uncopied during each offline window**, a cost accepted because the windows are rare
and scheduled.

---

## Alternatives considered

- **A VM on the substrate hypervisor.** Rejected: it shares the host and disk with the store, which
  ADR-0014 §3 rules out.
- **The tenant hypervisor.** Rejected: substrate services stay off tenant compute (ADR-0001,
  ADR-0004).
- **The Builder.** Rejected: it is away routinely (ADR-0014 open question 1).
- **A Raspberry Pi Zero 2 W.** Rejected: no Ethernet port, 512 MB of memory for an object-storage
  server, and only a microSD card to store on.
- **A storage host on the storage segment.** Not chosen for this: it is new hardware and a new
  segment for kilobytes of state. It is still the [Shared Storage](/docs/roadmap/infrastructure/mobile/shared-storage/)
  project's question, for data disks that should outlive a hypervisor, and this record doesn't
  prevent it.

---

## Open questions

1. **Encryption at rest with no TPM.** The Pi has no TPM, so a disk that unlocks unattended needs
   its key from somewhere. The candidates are a key held on the host (protects only a removed SSD),
   network-bound unlocking from another host (which brings back a dependency §5 forbids), or the
   object-storage engine's own server-side encryption.
2. **Power.** A replica that loses power whenever the substrate hypervisor does protects less. Does
   it get its own UPS, or share the site's?

---

## To confirm when building

- That the object-storage engine's bucket replication queues writes while the target is down, and
  catches up when it returns.
- That the Pi 4 boots from the USB SSD with the factory-default bootloader configuration, with no
  microSD inserted.
- That a Pi 4's USB 3 SSD keeps up with replication and the API's backups with room to spare.

---

## Current state

- **Proposed. Nothing is built.**
- `rpi001` is in the Pi lab, with no link.
- The store and the API's database are on the provisioning VM's OS disk, with no copy.
