---
title: "Storage"
weight: 3
---

# Substrate Storage

How the substrate stores data today: every disk a virtual machine has lives on the local storage of
the hypervisor that runs it, split into an OS disk and a data disk with different owners and
lifetimes.

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
else: on a data disk. This is the same stateless principle the substrate
applies to hosts — the image is a build artifact, and a VM must be reconstructible from its
declaration plus its data, never from the accumulated contents of its root filesystem.

---

## Local, not shared

Every disk is local to one hypervisor. A data disk outlives its VM, but not its host: losing a
hypervisor's storage loses every disk on it, and nothing can be moved to another host while it is
down ([Compute → Nothing is clustered](/docs/architecture/substrate/compute/#nothing-is-clustered)).
The storage segment exists in the segment model for storage traffic, and nothing sits on it yet.

Storage that outlives a single host — persistent volumes for the management and control planes and
for tenant workloads — is the [Shared Storage](/docs/roadmap/infrastructure/mobile/shared-storage/)
roadmap project.
