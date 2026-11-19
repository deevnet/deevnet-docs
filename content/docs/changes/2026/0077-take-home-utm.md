---
title: "CHG-0077: A Take-Home Image for UTM on Apple Silicon"
weight: -77
---

# CHG-0077: A Take-Home Image for UTM on Apple Silicon

| | |
|---|---|
| **Date** | 2026-11-18 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-11-18.** The arm64 qcow2 builds by the same play, passes the self-test emulated as UTM boots it, and is in the tenant downloads with its sha256 matching |
| **Window** | 2026-11-18. Built and proven on the Builder; the publish crossed the core router throttled, 22:49 to 23:12 EST |
| **Site** | mobile |
| **Systems** | The Builder (an arm64 emulator and firmware added); the artifact server on the Builder; the take-home arm64 qcow2; the tenant downloads on `dv02obs001v01` |
| **Automation** | `ansible-collection-deevnet.builder`, `deevnet-image-factory` |
| **Risk** | Low. Nothing changes on Deevnet's hosts but the Builder's packages, the artifact server and the tenant downloads. Most likely to go wrong: the push to the tenant downloads, which is throttled |
| **Related changes** | [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/) (the amd64 virtual machine image), [CHG-0076](/docs/changes/2026/0076-take-home-virtualbox-hyper-v/) (VirtualBox and Hyper-V), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/take-it-home/) |

---

## Summary

The take-home backend runs on a Raspberry Pi, as an amd64 virtual machine, from an installer ISO,
and in VirtualBox and Hyper-V. This change builds the same virtual machine for **arm64**, for
**UTM's QEMU backend on a Mac with Apple Silicon**. This is the fourth version of
[Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/). The image is built
from Debian's bookworm arm64 image by the same configuration play as the Pi image and the amd64
virtual machine, with the arm64 inputs the Pi image already uses.

## Goal

- One `make` target on the Builder builds an arm64 qcow2 and writes its sha256.
- In qemu on the Builder, it boots as UTM's QEMU backend boots it (the `virt` machine, UEFI,
  virtio disk and network): setup on the console, the root grown to fill the disk.
- It passes the self-test, every check.
- It is in the tenant downloads under `tenant/vm`, with a section for UTM in the tenant guide.

## Scope

**In scope:**
- **The Builder:** `qemu-system-aarch64` and an arm64 UEFI firmware, through
  `deevnet.builder`, to boot the arm64 machine emulated on x86.
- **The image:** an arm64 qcow2 from Debian's bookworm arm64 `nocloud` image, the same play, the
  Pi's arm64 kit, log bridge, silo and upstream releases.
- **Publish:** under `tenant/vm` with its sha256, and a guide section: a new machine in UTM's wizard
  (Virtualize, Linux, QEMU), the disk imported, and the Bridged network on the interface the owner
  picks.

**Out of scope:**
- A prebuilt `.utm` bundle: UTM's documentation does not describe its settings file.
- UTM's Apple Virtualization backend.
- A run in UTM on a real Mac, bridged on Wi-Fi: later. The image is proven on the Builder,
  emulated.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Installing the emulator changes the Builder's qemu | The Builder | A 27 MiB install; dnf lifts the installed qemu packages one patch release to match. Through `deevnet.builder`, by pull request |
| An arm64 input differs from the Pi's | The owner's Mac | The same pinned arm64 kit, log bridge, silo and upstream releases the Pi image is built from |
| Emulation is not UTM on a Mac | The proof | The machine is matched (the `virt` machine, UEFI, virtio); the CPU is emulated, so the proof is slow, and a real Mac stays Later |
| The push hangs the core router | Network | Throttled and detached, as the earlier take-home images were |

## Prerequisites

- [x] The take-home virtual machine image (CHG-0074)
- [x] The Pi image's arm64 inputs staged on the artifact server ([CHG-0072](/docs/changes/2026/0072-pi-metrics-and-alerting/), [CHG-0073](/docs/changes/2026/0073-pi-buckets/))

## Procedure

### Step 1: The Builder's emulator ✅

`qemu-system-aarch64` and `edk2-aarch64` added to the Builder's virtualization packages in
`deevnet.builder`, then applied to the Builder.

**Done 2026-11-18.** `qemu-system-aarch64-core` and `edk2-aarch64` went into the role's default
list and into the workstations' list in the inventory, which replaces it. Only the role's package
step was applied to the Builder: dnf installed both and lifted the installed qemu packages from
10.1.3 to 10.1.5. `libvirtd` was left as it was, enabled and not running.

### Step 2: Build the arm64 qcow2 ✅

A `make` target in `deevnet-image-factory` beside the amd64 one: Debian's bookworm arm64 image, the
configuration play with the arm64 inputs, the qcow2 and its sha256.

**Done 2026-11-18.** The virtual machine's build takes the architecture as a variable, and
`make vm-backend-arm64` builds it for arm64; the amd64 build and its file names are unchanged.
Debian's bookworm arm64 `nocloud` image, of the same dated build as the amd64 one and pinned by its
SHA512, was staged on the artifact server at 1.5 MB/s, with no ping to the core router missed. The
arm64 releases were already there, for the Pi image. The play ran unchanged, in the arm64 root
through `qemu-aarch64-static`: 52 tasks, none failed. The qcow2 is 1.3 GB, sha256 `d3334123…`.

### Step 3: Prove it on the Builder ✅

Under `qemu-system-aarch64`: the `virt` machine, the arm64 UEFI firmware, the disk and the network
on virtio, as UTM's QEMU backend gives them. Setup on the console, the root grown, the self-test.

**Done 2026-11-18.** The built qcow2 was booted twice, emulated, through a throwaway 24 GB
overlay: the `virt` machine with two emulated cores and 2 GB, edk2's arm64 UEFI, the disk on
virtio-blk and the network on virtio-net.

| | Display | First boot | Self-test |
|---|---|---|---|
| Run 1 | `ramfb` | setup answered on the console; the root grew to 24 GB; first boot took 3 min 29 s, emulated | 27 of 27 at first boot, and again by hand |
| Run 2 | `virtio-gpu-pci` | the same, with the setup prompt on the screen; 3 min 23 s | 27 of 27 at first boot, and again by hand |

**The console needs a virtio display.** A `ramfb` display alone shows the firmware and the boot
menu, then goes dark when Linux starts: Linux has no driver for it. UTM's QEMU backend offers
`virtio-ramfb`, which pairs it with virtio-gpu; `virtio-gpu-pci` is upstream qemu's nearest, and
with it the prompt shows. The VM signs in by key only once a key is given. A run in UTM on a real
Mac stays Later.

### Step 4: Publish ✅

Under `tenant/vm` in the tenant downloads, with its sha256, pushed throttled and detached, and the
tenant guide's UTM section.

**Done 2026-11-18.** `make vm-backend-arm64-publish` staged it on the Builder's artifact server. A
detached `rsync` at 1 MB/s carried it to `dv02obs001v01` in 23 minutes, with a watchdog pinging the
core router every second: 1,347 pings, none missed. The amd64 qcow2, the OVA and the VHDX beside
it were unchanged and were skipped. `sha256sum -c` passed on the observability store, and
`downloads.mobile.deevnet.net/vm/` serves the image's sha256 and its full size. The tenant guide's
[UTM section](/docs/runbook/tenant/take-it-home/) went in with this record.

## Verification

On the Builder:
- Under emulation, the image boots, asks for the user, the sign-in and the host name, grows its
  root to fill the disk, and `deevnet-kit selftest` passes every check.
- The published file's sha256 matches the one built.

## Undo

Remove the arm64 qcow2 from the tenant downloads. The build target is additive. The emulator
packages can stay on the Builder or be removed from `deevnet.builder`.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the Builder's emulator installed
- [x] Step 2: the arm64 qcow2 builds with its sha256
- [x] Step 3: proven on the Builder, emulated as UTM boots it
- [x] Step 4: published, with the guide section
