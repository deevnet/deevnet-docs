---
title: "Take-Home Media: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 32
tasks_in_progress: 0
tasks_planned: 0
---

# Take-Home Media: Project Plan

The tenant backend that goes home on a Raspberry Pi, on two more media: a virtual machine image,
then an ISO for an owner's own hardware. The
[proposal](/docs/architecture/proposals/take-home-vm-and-iso/) shaped it, and the owner accepted
it on 2026-11-17.

**Roadmap item:** [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

**Every medium carries one backend.** The Debian base, Mosquitto, Podman, the log, metrics,
alerting, notification, dashboard and bucket services, deevnet-kit and its self-test are the Pi
image's, built by the same configuration play. Only the medium differs.

**In Scope**
- An amd64 virtual machine image, then an installer ISO, then the formats an owner's computer runs
- A first boot that asks on the console for the user, the sign-in and the host name
- Publishing each beside the Pi image in the tenant downloads

**Out of Scope**
- A second backend design: a change to the contract, the kit or the self-test lands on every medium
- NAT or port forwarding: the virtual machine needs bridged networking
- cloud-init: the console prompt is the only first-boot path

---

## Versions

### v1, the MVP (done 2026-11-17)

An amd64 qcow2 of the tenant backend for Proxmox and KVM, on Debian bookworm like the Pi image.

**Done when:**

- [x] deevnet-kit, the log bridge and silo are built for amd64 and staged on the artifact server, each with its sha256
- [x] One `make` target on the Builder builds the qcow2 from the same configuration play as the Pi image
- [x] Its first boot asks on the console for the user, the sign-in (password or SSH key) and the host name, then deevnet-kit makes the CA and the secrets
- [x] The self-test passes every check under qemu on the Builder
- [x] `tdemo` moves across with its `kit.env`: a test client publishes, and its log shows in Grafana
- [x] The image is in the tenant downloads under `tenant/vm` with its sha256, and the tenant guide has a section for it

It is proven on the Builder under qemu only, never on the lab's hypervisors. A bridged run on a
real hypervisor comes with v3, or the first time someone imports it.

**Not in v1:** the ISO (v2); OVA, VHDX and arm64 for UTM (v3); trixie (all media move together, later).

### v2, the installer ISO (done 2026-11-17)

An ISO that installs the same amd64 system as v1 on an owner's own hardware, wired.

**Done when:**

- [x] One `make` target builds a hybrid ISO, bootable on UEFI and BIOS, that carries the v1 system image from the same build
- [x] In qemu on the Builder, the ISO boots under BIOS and under UEFI, lists the disks, and writes the system only to the disk the owner names and confirms, never to the stick it booted from
- [x] The installed system boots from its own disk, the ISO removed, under both firmwares, and its first boot is the VM's: `deevnet-kit setup` on the console, and the root grown to fill the disk
- [x] The installed system passes the self-test, every check
- [x] The ISO is in the tenant downloads under `tenant/iso` with its sha256, and the tenant guide has a section for it: write it to a USB stick, boot, install, wired

**Secure Boot was a goal, not a point, and v2 reached it in qemu.** Most machines ship with it on,
and the system's disk already carries Debian's signed shim and GRUB. The ISO and the installed
system both boot with it on under OVMF's Secure Boot firmware, and the self-test passes. So the
guide says it can stay on, and to turn it off only if the computer refuses the stick. Real hardware
is still to prove it (Later).

**Not in v2:** Wi-Fi on the installed system, a keyboard layout other than US, and the live mode
(Later); a run on real hardware (the first owner's, or Later); OVA, VHDX and UTM (v3).

### v3, VirtualBox and Hyper-V (done 2026-11-18)

The v1 virtual machine, unchanged, in the formats a Windows computer runs: an OVA for VirtualBox and
a VHDX for Hyper-V.

**Done when:**

- [x] One `make` target converts the v1 build's disk, unchanged, into an OVA for VirtualBox and a VHDX for a Hyper-V Generation 2 machine, each with its sha256; nothing is rebuilt
- [x] Each format's disk compares equal to the v1 disk (`qemu-img compare`), and the OVA's manifest and descriptor check
- [x] In qemu on the Builder, each boots in the firmware its hypervisor gives it, and its first boot is the VM's: `deevnet-kit setup` on the console, and the root grown to fill the disk
- [x] Each passes the self-test, every check
- [x] Both are in the tenant downloads under `tenant/vm` with their sha256s, and the tenant guide has a section for each: import, bridged networking (VirtualBox's bridged adapter, Hyper-V's external switch), and the Secure Boot template Hyper-V needs

**v3 is proven under qemu on the Builder only** (the owner's choice, 2026-11-18). VirtualBox and
Hyper-V themselves, and the bridged run on a real computer that v1 put off to v3, move to Later.

**Not in v3:** arm64 for UTM on Apple Silicon (v4); VMware; a run on a real VirtualBox or Hyper-V
host, bridged on Wi-Fi (Later).

### v4, UTM on Apple Silicon (next)

The virtual machine on a Mac with Apple Silicon: an arm64 build of the backend by the same play,
from Debian's arm64 image and the Pi's arm64 inputs, shipped as a zipped `.utm` bundle with its
settings made. The owner picks the bridged interface, which differs from Mac to Mac.

### Later

- VMware Workstation and Fusion: the OVA may import there, unproven
- A run on a real VirtualBox, Hyper-V or UTM host, bridged on Wi-Fi
- A NAT fallback, if bridging proves too hard on some Wi-Fi adapters
- A live, run-from-USB mode for the ISO
- Wi-Fi on the installed system: setup asks for the network when no cable is found
- A keyboard layout chosen at setup, for every medium
- Secure Boot proven on real hardware (v2 proved it in qemu)
- The ISO installed on a real machine
- Every medium moved to trixie together

---

## Records ✅

- ✅ [ADR-0044](/docs/architecture/decisions/tenant-model/0044-take-home-media/), Accepted 2026-11-17: one backend on several media, each from its vendor's image by the same play
- ✅ [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/), Complete 2026-11-17: building and publishing the virtual machine image

## amd64 inputs ✅

- ✅ deevnet-kit and the log bridge built for amd64 and staged at their pinned versions
- ✅ silo for amd64 taken from the amd64 image Deevnet runs, built from the same release, so no build crosses the core router
- ✅ The upstream amd64 releases (VictoriaLogs, vmutils, Grafana and its plugin, the alerting and notification services) staged with pinned sha256

## The image ✅

- ✅ Build method chosen, 2026-11-17: Debian 12's official `nocloud` image, mounted, then the configuration play, as the Pi image starts from Raspberry Pi OS
- ✅ The configuration play takes the architecture and the medium as variables, with the Pi-only steps (boot partition files) kept to the Pi
- ✅ A `make` target builds a bookworm amd64 qcow2

## First boot ✅

- ✅ `deevnet-kit setup`, a console prompt for the user, password or SSH key, and the host name, which runs before deevnet-kit's first boot

## Proof ✅

- ✅ The self-test passes every check under qemu on the Builder
- ✅ `tdemo` across with its `kit.env`: a test client publishes and its log shows in Grafana

## Publish ✅

- ✅ A publish target puts the image under `tenant/vm` with its sha256, pushed throttled to the observability store
- ✅ A section in the tenant guide: import, bridged networking, the first-boot prompt

---

## v2 records ✅

- ✅ [CHG-0075](/docs/changes/2026/0075-take-home-installer-iso/), Complete 2026-11-17: building and publishing the installer ISO
- ✅ No ADR: the ISO writes the virtual machine's disk unchanged, so ADR-0044's one way of making the system holds

## v2 installer ✅

- ✅ Boot design chosen, 2026-11-17: everything from the v1 disk, its kernel with an installer initramfs made by its `initramfs-tools`, its GRUB for BIOS, and Debian's signed shim and CD GRUB for UEFI; the v1 disk carried compressed, and nothing downloaded
- ✅ The installer lists the disks, refuses the one it booted from, asks the owner to type the chosen disk's name, writes the system and checks what it wrote, then asks to remove the stick and reboots
- ✅ A hybrid ISO, bootable on UEFI and BIOS, through Debian's signed shim and GRUB
- ✅ One `make` target builds the ISO from the v1 build's disk

## v2 proof ✅

- ✅ BIOS: the ISO installs to a blank virtual disk in qemu, and the installed system boots alone
- ✅ UEFI: the same with OVMF
- ✅ The installed system's first boot asks on the console, grows its root, and passes the self-test
- ✅ Secure Boot tried with OVMF's Secure Boot firmware: the ISO and the installed system boot with it on, and the self-test passes

## v2 publish ✅

- ✅ A publish target puts the ISO under `tenant/iso` with its sha256, pushed throttled and detached to the observability store
- ✅ A section in the tenant guide: write the stick, boot, choose the disk, then setup as on the VM

---

## v3 records ✅

- ✅ [CHG-0076](/docs/changes/2026/0076-take-home-virtualbox-hyper-v/), Complete 2026-11-18: the VirtualBox and Hyper-V images converted, proven and published

No ADR is expected: the formats carry the v1 disk unchanged, so ADR-0044 holds. One is written only
if a format needs the system itself changed.

## v3 formats ✅

- ✅ One `make` target converts the v1 build's disk: an OVA (a stream-optimized VMDK, an OVF descriptor with a bridged adapter, and a manifest of sha256s) and a VHDX for a Hyper-V Generation 2 machine, shipped zipped
- ✅ Each disk compared with the v1 disk, and the OVA's descriptor and manifest checked

## v3 proof ✅

- ✅ The OVA's disk boots in qemu in VirtualBox's firmware for it: setup, root grown, self-test every check
- ✅ The VHDX boots in qemu under OVMF with Secure Boot, as a Generation 2 machine does: setup, root grown, self-test every check

## v3 publish ✅

- ✅ A publish target puts both under `tenant/vm` with their sha256s, pushed throttled and detached to the observability store
- ✅ Tenant guide sections for VirtualBox and Hyper-V: import, the bridged adapter or external switch, and Hyper-V's Secure Boot template
