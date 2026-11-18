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
| **Status** | In progress |
| **Window** | Unscheduled. The images are converted and proven on the Builder; only their publish crosses the core router, throttled |
| **Site** | mobile |
| **Systems** | The artifact server on the Builder; the take-home OVA and VHDX; the tenant downloads on `dv02obs001v01` |
| **Automation** | `deevnet-image-factory` |
| **Risk** | Low. Nothing runs on Deevnet's hosts but the artifact server and the tenant downloads. Most likely to go wrong: the push to the tenant downloads, which is throttled |
| **Related changes** | [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/) (the virtual machine image they carry), [CHG-0075](/docs/changes/2026/0075-take-home-installer-iso/) (the installer ISO), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/tenant-to-pi-image/) |

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

### Step 1: The formats

The OVF descriptor (operating system type, firmware, disk controller, network adapter), and the
conversions, from the virtual machine build's raw disk.

### Step 2: Convert and check

A `make` target in `deevnet-image-factory` that writes the OVA and the VHDX, then compares each
disk with the virtual machine's and checks the OVA's manifest.

### Step 3: Prove it on the Builder

Under qemu: the OVA's disk under SeaBIOS, as VirtualBox boots it; the VHDX under OVMF with Secure
Boot, as a Generation 2 machine boots it. Each: setup on the console, the root grown, the
self-test.

### Step 4: Publish

Both under `tenant/vm` in the tenant downloads, with their sha256s, and the tenant guide's
sections.

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

- [ ] Step 1: the formats chosen and recorded
- [ ] Step 2: both convert, and their disks compare equal
- [ ] Step 3: proven on the Builder in each hypervisor's firmware
- [ ] Step 4: published, with the guide sections
