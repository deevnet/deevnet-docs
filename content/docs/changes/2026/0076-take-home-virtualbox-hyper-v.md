---
title: "CHG-0076: Take-Home Images for VirtualBox and Hyper-V"
weight: -76
---

# CHG-0076: Take-Home Images for VirtualBox and Hyper-V

| | |
|---|---|
| **Date** | 2026-11-18 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-11-18.** Both formats convert, compare equal and pass the self-test under qemu, and both are in the tenant downloads with their sha256s matching |
| **Window** | 2026-11-18. Converted and proven on the Builder; the publish crossed the core router throttled, 19:35 to 20:20 EST |
| **Site** | mobile |
| **Systems** | The artifact server on the Builder; the take-home OVA and VHDX; the tenant downloads on `dv02obs001v01` |
| **Automation** | `deevnet-image-factory` |
| **Risk** | Low. Nothing runs on Deevnet's hosts but the artifact server and the tenant downloads. Most likely to go wrong: the push to the tenant downloads, which is throttled |
| **Related changes** | [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/) (the virtual machine image they carry), [CHG-0075](/docs/changes/2026/0075-take-home-installer-iso/) (the installer ISO), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/take-it-home/) |

---

## Summary

The take-home backend runs on a Raspberry Pi, as a qcow2 virtual machine, and from an installer
ISO. This change puts the same virtual machine into the formats a Windows computer runs: an
**OVA for VirtualBox** and a **VHDX for a Hyper-V Generation 2 machine**. This is the third version
of [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/). Both carry the
virtual machine's disk unchanged, converted from the same build. Nothing is rebuilt.

## Goal

- One `make` target on the Builder converts the virtual machine build's disk into an OVA and a
  VHDX, each with its sha256.
- Each format's disk compares equal to the virtual machine's, and the OVA's descriptor and
  manifest check.
- Under qemu, each boots in the firmware its hypervisor gives it, and passes the self-test.
- Both are in the tenant downloads under `tenant/vm`, with a section each in the tenant guide.

## Scope

**In scope:**
- **The OVA:** a stream-optimized VMDK, an OVF descriptor for a 64-bit Debian machine with a
  bridged adapter, and a manifest of sha256s.
- **The VHDX:** a dynamic VHDX for a Generation 2 machine, which boots by UEFI.
- **Publish:** both under `tenant/vm`, with their sha256s, and guide sections: import, bridged
  networking (VirtualBox's bridged adapter, Hyper-V's external switch), and the Secure Boot template
  Hyper-V needs ("Microsoft UEFI Certificate Authority").

**Out of scope:**
- arm64 for UTM on Apple Silicon: v4.
- VMware Workstation and Fusion. The OVA may import there, unproven.
- A run on a real VirtualBox or Hyper-V host, bridged on Wi-Fi: later. Both formats are proven on
  the Builder under qemu.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A format's disk differs from the virtual machine's | The owner's computer | `qemu-img compare` against the virtual machine's raw disk, before publishing |
| The hypervisor's disk or network devices have no driver | The owner's computer | Debian's generic kernel and an initramfs with `MODULES=most` carry AHCI and the Hyper-V storage and network drivers; the network matches any Ethernet device |
| qemu is not VirtualBox or Hyper-V | The proof | The firmware is matched (BIOS for VirtualBox, UEFI with Secure Boot for Hyper-V); the devices are not, and a real host stays Later |
| The push hangs the core router | Network | Throttled and detached, as the virtual machine image and the ISO were |

## Prerequisites

- [x] The take-home virtual machine image (CHG-0074)

## Procedure

### Step 1: The formats ✅

The OVF descriptor (operating system type, firmware, disk controller, network adapter), and the
conversions, from the virtual machine build's raw disk.

**Done 2026-11-18.**

| | OVA, for VirtualBox | VHDX, for Hyper-V |
|---|---|---|
| Disk | stream-optimized VMDK, 1.39 GB | dynamic VHDX, 4.5 GB, zipped to 1.34 GB |
| Machine | OVF 1.0 descriptor: 64-bit Debian, 2 CPUs, 2 GB of memory | the owner makes it: Generation 2, 2 CPUs, 2 GB |
| Firmware | none named, so VirtualBox's default, BIOS | UEFI, Secure Boot with the "Microsoft UEFI Certificate Authority" template |
| Disk controller | SATA (AHCI) | SCSI, Hyper-V's for Generation 2 |
| Network | Intel PRO/1000, attached `Bridged` | the owner's external switch |

**The VHDX is shipped zipped.** Windows opens a zip itself, and the zip is a third of the VHDX's
size. Debian's generic kernel and an initramfs with `MODULES=most` carry the AHCI, `e1000` and
Hyper-V drivers, and the network configuration matches any Ethernet device. So the disk needs no
change for either hypervisor, and no ADR: ADR-0044's one way of making the system holds.

### Step 2: Convert and check ✅

A `make` target in `deevnet-image-factory` that writes the OVA and the VHDX, then compares each
disk with the virtual machine's and checks the OVA's manifest.

**Done 2026-11-18.** `make vm-formats` converts the raw disk the qcow2 was made from, in about four
minutes. `qemu-img compare` found both disks identical to it. The OVA check passed: its files in
the order OVF 1.0 asks (descriptor, manifest, disk), the manifest's sha256s matching each file, and
the descriptor naming the disk it carries at its size. The OVA's sha256 is `7ab2e240…`, the zipped
VHDX's `8b6961a1…`.

### Step 3: Prove it on the Builder ✅

Under qemu: the OVA's disk under SeaBIOS, as VirtualBox boots it; the VHDX under OVMF with Secure
Boot, as a Generation 2 machine boots it. Each: setup on the console, the root grown, the
self-test.

**Done 2026-11-18.** Each disk was taken out of the built file itself, the OVA unpacked and the zip
extracted, and booted through a throwaway 24 GB overlay.

| | Firmware and devices | First boot | Self-test |
|---|---|---|---|
| OVA | SeaBIOS; the disk on AHCI, an e1000 adapter, as VirtualBox gives them | setup asked on the console; the root grew to 24 GB | 27 of 27 at first boot, and again by hand |
| VHDX | OVMF with Secure Boot on and Microsoft's keys; the disk on SCSI | the same; `SecureBoot enabled` | 27 of 27 at first boot, and again by hand |

The devices are qemu's. VirtualBox's and Hyper-V's own, and a bridged run on a real computer, are
still to prove (Later).

### Step 4: Publish ✅

Both under `tenant/vm` in the tenant downloads, with their sha256s, and the tenant guide's
sections.

**Done 2026-11-18.** `make vm-formats-publish` staged both on the Builder's artifact server. A
detached `rsync` at 1 MB/s carried them to `dv02obs001v01` in 45 minutes, with a watchdog pinging
the core router every second: 2,640 pings, none missed. The v1 qcow2 beside them was unchanged and
was skipped. `sha256sum -c` passed on the observability store, and
`downloads.mobile.deevnet.net/vm/` serves each file's sha256 and its full size. The tenant guide's
[VirtualBox and Hyper-V sections](/docs/runbook/tenant/take-it-home/) went in with this
record.

## Verification

On the Builder:
- `qemu-img compare` finds each format's disk equal to the virtual machine's.
- The OVA's manifest matches its files, and its descriptor names the disk it carries.
- Under qemu, each boots, asks for the user, the sign-in and the host name, grows its root to fill
  the disk, and `deevnet-kit selftest` passes every check.
- The published files' sha256s match the ones built.

## Undo

Remove the OVA and the VHDX from the tenant downloads. The build target is additive.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the formats chosen and recorded
- [x] Step 2: both convert, and their disks compare equal
- [x] Step 3: proven on the Builder in each hypervisor's firmware
- [x] Step 4: published, with the guide sections
