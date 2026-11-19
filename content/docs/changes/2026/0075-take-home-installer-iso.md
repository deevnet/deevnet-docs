---
title: "CHG-0075: A Take-Home Installer ISO"
weight: -75
---

# CHG-0075: A Take-Home Installer ISO

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete** |
| **Window** | Unscheduled. The ISO is built and proven on the Builder; only its publish crosses the core router, throttled |
| **Site** | mobile |
| **Systems** | The artifact server on the Builder; the take-home installer ISO; the tenant downloads on `dv02obs001v01` |
| **Automation** | `deevnet-image-factory` |
| **Risk** | Low. Nothing runs on Deevnet's hosts but the artifact server and the tenant downloads. Most likely to go wrong: the push to the tenant downloads, which is throttled |
| **Related changes** | [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/) (the virtual machine image it carries), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/take-it-home/) |

---

## Summary

The take-home backend runs on a Raspberry Pi and as a virtual machine. This change builds an
**installer ISO** that puts the same system on an owner's own amd64 computer, wired, the second
version of [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/). The
ISO carries the virtual machine's disk, compressed, and writes it to the disk the owner names.
The installed system's first boot is the virtual machine's: `deevnet-kit setup` on the console,
and the root grown to fill the disk.

## Goal

- One `make` target on the Builder builds a hybrid ISO, bootable on UEFI and BIOS, from the
  virtual machine build's disk.
- Under qemu, the ISO installs only to the disk the owner confirms, and the installed system boots
  alone under both firmwares and passes the self-test.
- The ISO is in the tenant downloads, with a section in the tenant guide.

## Scope

**In scope:**
- **The installer:** it lists the disks, refuses the one it booted from, asks the owner to type
  the chosen disk's name, writes the system, checks what it wrote, and reboots.
- **The ISO:** built from the virtual machine's disk alone: its kernel, its signed shim and GRUB,
  and the disk itself, so the backend is built once for both media and nothing new is downloaded.
- **Publish:** `tenant/iso`, with its sha256, and a guide section.

**Out of scope:**
- Wi-Fi, a keyboard layout other than US, and a live mode: later.
- A run on real hardware. The ISO is proven on the Builder under qemu.
- Secure Boot as a condition of done. It is tried, and the result recorded.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The installer writes over the wrong disk | The owner's computer | It refuses the disk it booted from, and writes only after the owner types the chosen disk's name |
| The written system differs from the image | The owner's computer | The installer reads back what it wrote and compares the sha256 before it reboots |
| The push hangs the core router | Network | Throttled and detached, as the virtual machine image was |

## Prerequisites

- [x] The take-home virtual machine image (CHG-0074)

## Procedure

### Step 1: The boot design ✅

How the ISO starts its installer, from what the virtual machine's disk already holds.

**Done 2026-11-17.** The virtual machine's disk already holds everything the ISO needs: Debian's
generic kernel, `initramfs-tools`, GRUB for BIOS, and Debian's signed shim and GRUB for CDs. Its
root is mounted read-only under an overlay that is thrown away, and from it come:

- the kernel, and an initramfs made by its `initramfs-tools` with the installer in it. GRUB starts
  the kernel with `boot=deevnet-install`, so the installer runs where a root file system would be
  mounted;
- GRUB for BIOS as an El Torito image;
- an EFI system partition with the signed shim and the signed CD GRUB, which finds the ISO by
  `/.disk/info` and reads the same menu as BIOS.

The ISO carries the virtual machine's raw disk compressed (1.16 GB), with its sha256. The disk is
identical to the published virtual machine image. Nothing is downloaded, and the backend is built
once for both media, so no ADR is needed: ADR-0044's one way of making the system holds.

### Step 2: The installer and the ISO ✅

The installer, and a `make` target in `deevnet-image-factory` that builds the ISO.

**Done 2026-11-17.** `make iso-backend` builds `debian-bookworm-mobile-backend-installer.iso`
(1.2 GB), hybrid for BIOS and UEFI, on an optical drive or a USB stick.

### Step 3: Prove it on the Builder ✅

Under qemu, with SeaBIOS and with OVMF: install to a blank disk, boot it alone, answer the prompt,
run the self-test. Try Secure Boot with OVMF's Secure Boot firmware.

**Done 2026-11-17, all on one build of the ISO.** Each run used the ISO as a USB stick, a blank
24 GB disk, and an 8 GB disk too small for the system.

| Firmware | Installer | Installed system, booted alone |
|---|---|---|
| SeaBIOS | Listed only the 24 GB disk. Refused the stick's name, the small disk's, and a wrong confirmation. Wrote 16 GiB in 30 s, and the read-back matched | Setup asked on the console; the root grew to 24 GB; self-test 27 of 27 |
| OVMF | The same | Booted by the removable path, with no boot entry for the disk; self-test 27 of 27 |
| OVMF, Secure Boot on, Microsoft's keys | The same; the kernel in lockdown | Booted with Secure Boot on; self-test 27 of 27 |

**Secure Boot works in qemu**, through Debian's signed shim, GRUB and kernel, on the ISO and on the
installed system. It is not yet proven on real hardware.

### Step 4: Publish ✅

The ISO under `tenant/iso` in the tenant downloads, with its sha256, and a section in the tenant
guide.

**Done 2026-11-17.** `make iso-backend-publish` put it on the Builder. It went to
`dv02obs001v01` by rsync at 1 MB/s, detached, in 20 minutes, with a ping watchdog on the core
router: 1,176 pings, none missed. rsync checked the file's checksum on arrival. The site serves the
ISO at its full size, and its sha256 `9de58e58…`, the one the build made and the proof used.
The tenant guide's section is
[Or a computer of your own](/docs/runbook/tenant/take-it-home/your-own-computer/).
**Secure Boot can stay on**, it says, and it says to turn Secure Boot off if the computer refuses
the stick.

## Verification

On the Builder, under qemu, with each firmware:
- The installer refuses the ISO's own disk and writes only to the one named.
- The installed system boots with the ISO removed, asks for the user, the sign-in and the host
  name, and grows its root to fill the disk.
- `deevnet-kit selftest` passes every check.
- The published ISO's sha256 matches the one built.

## Undo

Remove the ISO from the tenant downloads. The build target is additive.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the boot design chosen and recorded
- [x] Step 2: the ISO builds
- [x] Step 3: proven on the Builder under BIOS and UEFI, and Secure Boot's result recorded
- [x] Step 4: published, with the guide section
