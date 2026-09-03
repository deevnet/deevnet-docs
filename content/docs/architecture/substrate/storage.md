---
title: "Storage"
weight: 3
---

# Substrate Storage

Defines the shared and persistent storage model for Deevnet sites.

---

## Status

**Shared** storage is a **planned future addition** to core services. This document will be expanded as the storage architecture is defined.

---

## Intent

Shared storage will provide persistent volumes for substrate consumers — both management-plane services and tenant workloads — independent of any single compute host.

---

## Virtual Machine Disks

Every virtual machine built on the substrate has its disks divided into two kinds, with different
owners and different lifetimes:

| Disk | Owned by | Lifetime |
|------|----------|----------|
| **OS disk** | The base image the VM was created from | Replaced whenever the image is rebuilt — nothing on it survives, and nothing is expected to |
| **Data disk** | Whatever creates the VM | Outlives the VM: it is declared, sized and attached per workload, and can be detached and reattached |

### The OS disk is small and growable

A base image carries an operating system and its packages — not a workload. It is therefore sized
for the operating system alone, and it is **growable**: a VM that needs a larger root filesystem is
given a larger disk at creation time, and tooling already present in the image expands the
filesystem to fill it on first boot. No image rebuild is required to accommodate a bigger consumer.

Sizing the image for the largest imaginable workload is the alternative, and it is a poor trade.
Every VM created from that image inherits the size, which makes each one slower to copy, to migrate
and to back up, and commits pool capacity that nothing will ever use. It is also close to
irreversible: the virtualization platform can grow a virtual disk but cannot shrink one, so the size
baked into an image propagates to every VM built from it until the image itself is rebuilt.

Growability is a property of how the OS disk is laid out, not an afterthought. The base image
partitions its root filesystem directly, because the expansion tooling that ships inside the image
can grow a partition-backed root unaided — an extra volume-management layer between the partition
and the filesystem would need tooling in the image and a first-boot step in every consumer.

### State does not live on the OS disk

Because the OS disk is replaced on every image rebuild, anything worth keeping belongs somewhere
else: on a data disk, or on shared storage. This is the same stateless principle the substrate
applies to hosts — the image is a build artifact, and a VM must be reconstructible from its
declaration plus its data, never from the accumulated contents of its root filesystem.

For tenants, the data disk is part of the tenant's own Terraform, alongside the VM it attaches to.
That keeps the split visible in the tenant's code: the substrate supplies an image with a small OS
disk, and the tenant declares whatever capacity its workload actually needs. See the
[Tenant Contract](/docs/architecture/tenant/) and
[Building Tenants](/docs/architecture/tenant/building/).
