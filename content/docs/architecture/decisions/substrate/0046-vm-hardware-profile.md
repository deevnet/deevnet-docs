---
title: "ADR-0046: One Hardware Profile for Every VM"
weight: -46
---

# ADR-0046: Every VM Deevnet Builds Has One Declared Hardware Profile

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-11-21 |
| **Scope** | The virtual hardware of every VM Deevnet builds on a Proxmox hypervisor: the substrate's service VMs and tenant workloads. Not a VM's size (cores, memory, disk), which each VM declares; not the take-home images, which run on hypervisors Deevnet does not own ([ADR-0044](/docs/architecture/decisions/tenant-model/0044-take-home-media/)) |
| **Related** | [ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/) (the service VMs), [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §12 (tenant workloads), [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) (rebuilt from code), [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/), [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) |

---

## Context

**No one chose the VMs' hardware.** The first VMs were built with whatever worked, and most
of it came from defaults. The Fedora template's Packer build names a SCSI disk but no controller,
so it takes the default, and Proxmox's own guide says what that is: *"Proxmox VE emulates by
default a LSI 53C895A controller."* Every clone inherits it. As of 2026-11-21:

| Where | VMs | Controller | Firmware |
|---|---|---|---|
| `dv02hyp001p01` | the template and 7 service VMs | `lsi` | SeaBIOS |
| `dv02hyp001p01` | `dv02bld002v01`, built by PXE | `virtio-scsi-single` (its code says `virtio-scsi-pci`) | OVMF, q35 |
| `dv02hyp002p02` | the template and 5 tenant workloads, among them EdS's | `lsi` | SeaBIOS |

**Three builders make VMs, and each sets hardware its own way.** The template build sets what
every clone starts with. `proxmox_vm` clones service VMs from it, and builds a PXE VM with
hardware of its own. The Deevnet API clones tenant workloads from it and sets cores, memory and
the guest agent. Nothing compares the result with anything.

**The default has now cost an outage.** In
[INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/), the API VM's kernel panicked in its LSI
driver while a backup and a restore loaded the disk it shares with every service VM. Proxmox's
guide recommends the other controller for exactly that load: *"A SCSI controller of type VirtIO
SCSI single and enabling the IO Thread setting for the attached disks is recommended if you aim
for performance. This is the default for newly created Linux VMs since Proxmox VE 7.3."* With IO
Thread on, it says, one benefit is *"reduced latency (hangs) in the guest for very I/O-intensive
host workloads, since neither the main thread nor a vCPU thread can be blocked by disk I/O."*
[INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) showed the same symptoms on
another VM with the same controller, without a console capture to name the cause.

**A tenant now depends on it.** EdS runs its services on a tenant workload. The hardware under a
workload is part of what Deevnet gives a tenant, and it should be chosen, written down and the same
for every tenant.

## Options considered

**A. Leave the defaults.** Nothing to do, and every new VM still gets the controller that
panicked. Rejected.

**B. Fix the controller where each builder sets hardware.** Quick, but it leaves three places that
can disagree again, as `proxmox_vm`'s PXE path already disagrees with its own VM. Rejected.

**C. One declared profile, applied by every builder, with drift reported.** The choice is made
once, in one place, and a VM that differs is found rather than discovered in an incident.
**Chosen.**

**Within C, VirtIO SCSI rather than VirtIO Block.** VirtIO Block is as fast, but its disks are
`/dev/vda` instead of `/dev/sda`. Anything that names a disk by device, cloud-init's growpart among
them, would change. VirtIO SCSI keeps the names, so an existing VM can move in place.

## Decision

### 1. One profile, declared once

Every VM Deevnet builds on a Proxmox hypervisor has the same virtual hardware, declared once in
inventory for every site:

| Part | Profile | Why |
|---|---|---|
| Disk controller | `virtio-scsi-single` | Proxmox's recommendation; one controller per disk, so IO Thread applies per disk |
| Disk options | `iothread=1`, `discard=on`, `cache=none` | IO Thread keeps disk I/O off the vCPU threads; Discard returns freed blocks to the thin pools; no host cache, as today |
| Network | `virtio` | Already on every VM. Proxmox: *"the VirtIO paravirtualized NIC should be used if you aim for maximum performance"* |
| CPU type | `host` | Already on every VM. No VM live-migrates: each hypervisor is its own cluster |
| Firmware and machine | SeaBIOS, Proxmox's default machine type | Proxmox: *"In most cases you want to switch from the default SeaBIOS to OVMF only if you plan to use PCIe passthrough"* |
| Guest agent | `enabled=1` | Already set by every builder |

A VM's size stays its own: cores, memory and disk size are declared per VM, as today.

### 2. An exception is declared, with its reason

A VM that needs different hardware declares the difference in its own inventory entry, with the
reason beside it. `dv02bld002v01` is the one known case: it is a UEFI PXE test target, so it needs
OVMF and q35. An undeclared difference is drift.

### 3. Every builder applies it

- **The template build** sets the controller and the disk options, so every clone starts on the
  profile.
- **`proxmox_vm`** sets the profile on every VM it makes, by clone or by PXE, and never relies on
  what a clone inherited.
- **The Deevnet API** sets the profile's controller and disk options when it makes a tenant
  workload, as it already sets the guest agent.

### 4. Drift is reported

A check lists every VM on every hypervisor whose hardware differs from the profile and its declared
exceptions, the way the VM identity check lists VMIDs. It reports; it does not change a running VM.

### 5. Existing VMs move by a change

The template is rebuilt on the profile first. Then each VM moves, in a change record:

- **Service VMs** are rebuilt from code where [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)
  allows, or changed in place.
- **Tenant workloads** move only in a window agreed with their tenant: the change restarts their VM.
- **In place, the guest must carry the driver first.** Fedora's initramfs is built for the hardware
  it was installed on, so a VM installed on `lsi` may not include `virtio_scsi`. The change adds it
  to the initramfs before switching the controller, keeps the old setting to switch back to, and
  moves one VM and checks it boots before the rest.

## Consequences

**Good:**

- The controller that panicked is gone from every VM, and IO Thread keeps a busy host disk from
  stalling a guest's vCPUs.
- A tenant's workload has the same hardware as every other tenant's, written down.
- A VM built by any path matches the others, and one that doesn't is found by a check.

**Bad:**

- Every existing VM restarts once to move, the tenant workloads in windows their tenants agree to.
- A VM changed in place risks not booting until its initramfs carries the driver; the change has to
  handle it VM by VM.
- Three builders in three repositories carry the same values from one declaration, and the template
  build has to read inventory, which it does not do today.

## To accept

- [ ] The profile's values agreed, including the firmware
- [ ] The template rebuilt on the profile, and one service VM built from it
- [ ] `proxmox_vm` and the Deevnet API set the profile
- [ ] The drift check built, reporting only declared exceptions
- [ ] Every existing VM moved, by change record

## Open questions

- **Where the template build reads the profile from.** The image factory takes its Proxmox settings
  from its own variables, not inventory.
- **SeaBIOS or OVMF for everything.** SeaBIOS is Proxmox's advice and what nearly every VM has.
  OVMF with Secure Boot would match the take-home images and `dv02bld002v01`, at the cost of
  rebuilding every VM rather than changing it in place.
