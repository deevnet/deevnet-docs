---
title: "ADR-0014: Tenant State Durability"
weight: 14
---

# ADR-0014: Tenant State Is Kept Data, Copied Away From What It Restores

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-16 |
| **Scope** | How the tenant state store's contents survive losing the host, disk or hypervisor they live on, and how that copy is kept apart from the platform API's database, which the state restores |
| **Extends** | [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), which offered the store and recorded its durability as *"the weakest part of the decision"*; [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), whose §1 and §6 put the store and the API's database in one VM |
| **Extended by** | [ADR-0026: Object Storage](/docs/architecture/decisions/0026-object-storage/) — the store is defined by a contract, runs pgsty/silo, and also offers tenant buckets *(Proposed)* |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §4, [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) §4 and §5, [Substrate Storage](/docs/architecture/substrate/storage/), [Limits](/docs/policies/risk-management/resiliency/) |

---

## Context

### ADR-0007 sized state loss as a rebuild

When the store was offered, losing state was cheap, and ADR-0007 said exactly how cheap:

> **Losing state costs a rebuild, not a loss** — which is exactly what the architecture's own claim
> that a tenant is rebuilt from code, not from a backup, is supposed to guarantee.

It then recorded what the store gave up by leaving git:

> **Durability moved rather than vanished.** Git gave replication for free; the store's own data now
> needs backing up. Bucket versioning is enabled, which turns an overwrite into an undo, but that is
> not a backup and should not be mistaken for one. This is the weakest part of the decision and it is
> recorded as such.

No later record picked that up.

### ADR-0012 makes state the authoritative copy of device secrets

ADR-0012 changes what state is worth. Its §4 was decided in review:

- *"**The tenant's state is the authoritative copy.** The API's copies are working copies,
  restorable from the tenant's state (§5)."*
- The API generates each device's Wi-Fi key and broker password, and they land in the tenant's
  state as sensitive values.

Its §5 sets the requirement that depends on this, *"a substrate rebuild never costs a device
visit"*, and names the one exception:

> **The one case that still costs a re-flash:** losing the API's database **and** the tenant's state
> together.

For a device whose credentials are written into NVS over USB, as ADR-0011's Ma Bell gateway's are,
a re-flash is a site visit per device.

Once §4 is built, ADR-0007's sizing no longer holds for a tenant with IoT resources. Losing that
tenant's state loses secrets that exist on devices and nowhere else the tenant controls. It also
sits against ADR-0007 §5, *"no tenant declares a resource whose value cannot be re-derived from
code"*, because a generated device secret can't be re-derived.

### ADR-0013 put both copies in one VM

ADR-0013 (*Accepted*) groups services by domain. The provisioning domain holds *"what a tenant's
`terraform apply` talks to"*:

| Host | Holds |
|---|---|
| `dv02prv001v01` | the Deevnet API and its database (ADR-0012); the tenant state store, folded in (§6) |

The grouping is sound. But for a tenant using the offered store, it puts the API's database and
the tenant's state in one failure domain. **ADR-0012 §5's exception is then a single event:**
losing that VM's disk.

### What is true today

Read on `dv02prv001v01` and in the automation on 2026-09-16:

- **Both data sets are on the OS disk.** The VM has one 32G disk, `sda`, with the root filesystem on
  `sda3`. MinIO's data (`/srv/minio/data`) and PostgreSQL's (`/srv/deevnet-api/pgdata`) are
  directories on that root filesystem. Its host_vars declare no `data_disk`. Of the VMs in
  inventory, only `dv02bld001v01` declares one.
- **That contradicts the storage architecture**, which says the OS disk is *"Replaced whenever the
  image is rebuilt — nothing on it survives, and nothing is expected to"*, and that *"anything worth
  keeping belongs somewhere else"* ([Substrate Storage](/docs/architecture/substrate/storage/)).
- **The VM's disk is on a single physical disk.** `local-lvm-big-thin` is a thin pool on
  `vgbigdata`, one 1.8T disk with *"No redundancy. Each data disk is a single disk. Losing it loses
  every VM disk on it."*
  ([Hypervisor Storage](/docs/roadmap/infrastructure/mobile/hypervisor-storage/)).
- **Nothing copies it off the host.** The `proxmox_vm` role attaches data disks with
  `backup: false`, and [Limits](/docs/policies/risk-management/resiliency/) records that *"No collection carries
  off-box backup automation"*.
- **Versioning is on** for the `tf-state` bucket, as ADR-0007 said.
- **The bucket holds no state yet.** The old store VM, `dv02tst001v01`, was wiped rather than
  migrated in [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/), and `t-demo` is destroyed.
  The API is a shell with no device resources. **Nothing is at risk today**, which makes this the
  cheapest moment to decide.

---

## Options considered

### A — Keep today's arrangement

Versioning on a bucket on the OS disk.

- **Pros:** nothing to build.
- **Cons:**
  - An image rebuild of the VM loses every tenant's state.
  - So does the loss of one physical disk on the management hypervisor.
  - Either one also loses the API's database, so every device of every opted-in tenant needs
    re-flashing.
- **Verdict:** Rejected.

### B — Put the store and the API's database in different VMs

Undo ADR-0013 §6 for the store.

- **Pros:** a lost or rebuilt VM no longer takes both.
- **Cons:**
  - Both VMs would still be on the same hypervisor and the same single disk, so the failure that
    matters most is unchanged.
  - It separates a domain ADR-0013 grouped on purpose.
- **Verdict:** Rejected. It moves the problem without removing it.

### C — A data disk, and a scheduled off-host backup

- **Pros:**
  - Survives an image rebuild and the loss of the hypervisor's disk.
  - Simple to build.
- **Cons:**
  - **It leaves a window.** A device registered after the last backup and before the loss has
    secrets in no copy that survived. With a nightly schedule, the window is up to a day of device
    registrations, each a re-flash.
- **Verdict:** Rejected as the whole answer, but kept for the API's database (§5).

### D — A data disk, and a copy taken on every write, on separate hardware

The store's contents are replicated as they are written to a second copy that shares no disk and
no host with the first.

- **Pros:**
  - Closes C's window: a secret written to a tenant's state reaches the second copy within moments,
    not at the next backup.
  - Survives an image rebuild, the VM's loss, and the hypervisor's disk.
  - State is small and changes only when a tenant applies, so the volume is trivial.
- **Cons:**
  - A second store, or a store-native replication target, to build and to watch.
  - Replication faithfully copies a bad write or a deletion. Versioning, kept on both sides, is
    what makes that recoverable.
  - The replica holds secrets, so it is a secret store in its own right.
- **Verdict: Chosen.**

### E — Keep device secrets out of state

The tenant generates each device's secrets, keeps them in its own repository encrypted with age as
ADR-0012 §9 already does for tenant credentials, and passes them to the API write-only.

- **Pros:**
  - State goes back to being re-derivable, and ADR-0007's sizing and §5 hold again.
  - Git becomes the durable, versioned, off-host copy, as it was before the store.
- **Cons:**
  - It reverses ADR-0012 §4, which chose *"the API generates"* in review, and its considered
    alternative of tenant-generated secrets.
  - Every device registration becomes a secret-bearing commit in the tenant's repository.
  - Losing a tenant's age keys loses its device secrets.
- **Verdict:** Not chosen by this record, because it would reopen a decision ADR-0012 made in
  review. It is recorded so that ADR-0012's acceptance can weigh it (Open question 2).

---

## Decision

**Option D**, for the tenant state store. The API's database gets a scheduled backup (§5).

### 1. Tenant state is kept data

- **The store is operated as holding data that can't be re-derived.** Once ADR-0012 §4 is built,
  that is true for any tenant with IoT resources, and the store can't tell which tenants those are.
- **ADR-0007's sizing still describes a tenant with no secret-bearing resources.** It no longer
  describes the store as a whole.

### 2. State lives on a data disk

- **The store's data and the API's database move to a data disk** declared on the provisioning VM,
  per [Substrate Storage](/docs/architecture/substrate/storage/).
- **Rebuilding the VM's image never touches them.**
- This is done while the bucket is empty.

### 3. Every write is copied to separate hardware

- **The copy is taken on write, not on a schedule**, so no device registration waits for a backup
  window.
- **The copy shares no physical disk and no host with the store.** A second VM on the same
  hypervisor disk does not qualify.
- **The copy is on site and needs no internet**, so a restore works under the same conditions as
  the rest of a rebuild. [Correctness §5.4](/docs/standards/correctness/) requires substrate
  provisioning to work without upstream internet, and restoring the store is part of provisioning
  the substrate again.
- **Versioning is kept on both sides**, so a deletion or bad write that replicates can still be
  undone.
- **Where the copy lives is Open question 1.**

### 4. The copy is a secret store

- **Its credentials are substrate-only.** No tenant credential reads or writes it; tenants only ever
  use the primary.
- **It is encrypted at rest**, or it sits on storage that is.
- **Losing or exposing it is treated as exposing every opted-in tenant's state.**

### 5. The API's database is backed up on a schedule

- **Its loss is recoverable without the backup.** The database is hosted tenant state (ADR-0012
  §5), and each tenant's next apply restores it from state.
- **But one thing in it is not re-derivable:** the API's audit log. ADR-0012 gives it a job no
  other record does: *"The API's audit log is that record for IoT."*
- **So it is backed up off the host on a schedule**, to the same separate hardware as §3. A lost
  day of audit entries is accepted.

### 6. Rebuild order

After a substrate rebuild that loses the provisioning VM:

1. **Restore the store from its copy** before any tenant applies.
2. **Restore the API's database from its backup**, if one exists.
3. **Tenants apply.** Anything the API is missing is restored from state through ADR-0012 §5's
   restore path, with the secrets the devices already hold.

Applying before step 1 would plan against empty state, and every device resource would be a fresh
create with new secrets.

### 7. A restore is rehearsed before this is accepted

- **A backup nobody has restored is not counted.** ADR-0007 rejected an option partly for *"a
  restore nobody rehearses"*.
- **The change that builds this restores the store from its copy** onto a fresh VM, and a tenant
  plans against it with no changes.

### 8. Declining the store carries the same obligation

A tenant that declines the store (ADR-0007 §1) and holds IoT resources is the only keeper of its
devices' secrets. ADR-0010 §4 requires a service to document what declining costs, and this is
that cost for the store: the tenant needs its own copy that meets §3.

---

## Consequences

**ADR-0012 §5's promise becomes true of the platform, not just of the API.** Losing the provisioning
VM, or the management hypervisor's disk, costs a restore and an apply, not a device visit.

**Deevnet gets its first off-box copy of anything.** [Limits](/docs/policies/risk-management/resiliency/) lists
*"On-box backups only"*, and says off-box config backup automation is *"the smallest item on this
list, and the one with the best return"*. This covers the store and the API's database only. Router configuration
and everything else stay as they are.

**A new failure mode needs watching.** A replica that quietly stops replicating looks healthy until
the day it's needed. Replication lag or failure needs to reach substrate observability, which has
no tooling yet.

**The provisioning VM is rebuilt with a data disk.** The bucket and the API are empty today, so this
costs nothing now and more with every tenant that uses the store.

**The substrate holds a second copy of tenant secrets.** It was already true that the store holds
them. The replica doubles where that exposure lives, and §4 exists because of it.

**ADR-0007 §5 and ADR-0012 §4 still disagree.** This record makes state that holds secrets durable.
It doesn't decide whether state should hold them. That stays with ADR-0012.

---

## Open questions

1. **Where does the copy live?** It has to meet §3: separate hardware, on site, no internet.
   - **The tenant hypervisor.** It's on site, always on, and has its own disks. But it is the tenant
     compute domain, and ADR-0001 and ADR-0004 keep substrate services off it.
   - **The Builder.** It has a data disk and is present at every rebuild, which is when the copy is
     needed. But ADR-0008 gives it no site, and ADR-0013 moved the controller off it because a
     site's steady state shouldn't depend on it staying attached. A copy that pauses whenever the
     Builder is away reopens C's window.
   - **A small dedicated storage device** on the management segment. It meets §3 cleanly, but it is
     new hardware and a new host class.
2. **Should ADR-0012 §4 be revisited in favour of Option E** before ADR-0012 is accepted? If it
   is, §1 and §3 of this record relax back towards C, because state would no longer hold anything
   that isn't re-derivable.
3. **Does the fabric's state need the same treatment?** ADR-0007 reserved a prefix for it in the
   same bucket, so §3 would cover it anyway. The question is whether it needs anything more.

---

## To confirm when building

- **The store can replicate to the chosen target with versioning on both sides**, and a
  replicated delete can be undone from the replica.
- **A restore onto a fresh VM gives a tenant a no-change plan** (§7).
- **Replication failure is visible** to whatever watches the substrate.

---

## Current state

- **Proposed.** Nothing is built.
- The store and the API's database are on the provisioning VM's OS disk, with no off-host copy.
- The bucket holds no tenant state, and the API holds no device resources.
