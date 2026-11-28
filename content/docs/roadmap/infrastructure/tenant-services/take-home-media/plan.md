---
title: "Take-Home Media: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 42
tasks_in_progress: 5
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

- [x] deevnet-kit, the log bridge and silo are built for amd64 and staged on the artifact server, each with its sha256 {{< added "2026-11-17" >}}
- [x] One `make` target on the Builder builds the qcow2 from the same configuration play as the Pi image {{< added "2026-11-17" >}}
- [x] Its first boot asks on the console for the user, the sign-in (password or SSH key) and the host name, then deevnet-kit makes the CA and the secrets {{< added "2026-11-17" >}}
- [x] The self-test passes every check under qemu on the Builder {{< added "2026-11-17" >}}
- [x] `tdemo` moves across with its `kit.env`: a test client publishes, and its log shows in Grafana {{< added "2026-11-17" >}}
- [x] The image is in the tenant downloads under `tenant/vm` with its sha256, and the tenant guide has a section for it {{< added "2026-11-17" >}}

It is proven on the Builder under qemu only, never on the lab's hypervisors. A bridged run on a
real hypervisor comes with v3, or the first time someone imports it.

**Not in v1:** the ISO (v2); OVA, VHDX and arm64 for UTM (v3); trixie (all media move together, later).

### v2, the installer ISO (done 2026-11-17)

An ISO that installs the same amd64 system as v1 on an owner's own hardware, wired.

**Done when:**

- [x] One `make` target builds a hybrid ISO, bootable on UEFI and BIOS, that carries the v1 system image from the same build {{< added "2026-11-17" >}}
- [x] In qemu on the Builder, the ISO boots under BIOS and under UEFI, lists the disks, and writes the system only to the disk the owner names and confirms, never to the stick it booted from {{< added "2026-11-17" >}}
- [x] The installed system boots from its own disk, the ISO removed, under both firmwares, and its first boot is the VM's: `deevnet-kit setup` on the console, and the root grown to fill the disk {{< added "2026-11-17" >}}
- [x] The installed system passes the self-test, every check {{< added "2026-11-17" >}}
- [x] The ISO is in the tenant downloads under `tenant/iso` with its sha256, and the tenant guide has a section for it: write it to a USB stick, boot, install, wired {{< added "2026-11-17" >}}

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

- [x] One `make` target converts the v1 build's disk, unchanged, into an OVA for VirtualBox and a VHDX for a Hyper-V Generation 2 machine, each with its sha256; nothing is rebuilt {{< added "2026-11-18" >}}
- [x] Each format's disk compares equal to the v1 disk (`qemu-img compare`), and the OVA's manifest and descriptor check {{< added "2026-11-18" >}}
- [x] In qemu on the Builder, each boots in the firmware its hypervisor gives it, and its first boot is the VM's: `deevnet-kit setup` on the console, and the root grown to fill the disk {{< added "2026-11-18" >}}
- [x] Each passes the self-test, every check {{< added "2026-11-18" >}}
- [x] Both are in the tenant downloads under `tenant/vm` with their sha256s, and the tenant guide has a section for each: import, bridged networking (VirtualBox's bridged adapter, Hyper-V's external switch), and the Secure Boot template Hyper-V needs {{< added "2026-11-18" >}}

**v3 is proven under qemu on the Builder only** (the owner's choice, 2026-11-18). VirtualBox and
Hyper-V themselves, and the bridged run on a real computer that v1 put off to v3, move to Later.

**Not in v3:** arm64 for UTM on Apple Silicon (v4); VMware; a run on a real VirtualBox or Hyper-V
host, bridged on Wi-Fi (Later).

### v4, UTM on Apple Silicon (done 2026-11-18)

The virtual machine on a Mac with Apple Silicon: an arm64 qcow2 of the same backend, built by the
same play, for UTM's QEMU backend.

**Done when:**

- [x] One `make` target builds an arm64 qcow2 from Debian's bookworm arm64 image by the same configuration play as the Pi image and v1, with the Pi's arm64 inputs, and writes its sha256 {{< added "2026-11-18" >}}
- [x] In qemu on the Builder, it boots as UTM's QEMU backend boots it (the `virt` machine, UEFI, virtio disk and network), and its first boot is the VM's: `deevnet-kit setup` on the console, and the root grown to fill the disk {{< added "2026-11-18" >}}
- [x] It passes the self-test, every check {{< added "2026-11-18" >}}
- [x] It is in the tenant downloads under `tenant/vm` with its sha256, and the tenant guide has a section for UTM: a new virtual machine (Virtualize, Linux, QEMU), the disk imported, and the Bridged network on the interface the owner picks {{< added "2026-11-18" >}}

**The choices, the owner's, 2026-11-18.** A qcow2 and the guide, not a prebuilt `.utm` bundle:
UTM's documentation does not describe the bundle's settings file, but it does describe making a
machine in its wizard. UTM's QEMU backend, not Apple Virtualization: it takes a qcow2 and offers
bridging, and the Builder can boot what it boots. Proven on the Builder, the arm64 machine emulated
on x86, which needs `qemu-system-aarch64` and an arm64 UEFI firmware installed there.

**Not in v4:** a `.utm` bundle; the Apple Virtualization backend; a run in UTM on a real Mac,
bridged on Wi-Fi (Later).

### v5, the owner's names (current)

The backend's own tool and files carry a name that is the owner's, not Deevnet's: `deevnet-kit`
becomes `tenant2backend`, and its files take the plain noun `backend`, on every medium.

**Done when:**

- [x] The kit is `tenant2backend`, with `/etc/backend`, `/opt/backend`, the `backend-*` units, the `backend` group, `backend.txt` on the card and `backend-ca.pem`; `deevnet-kit` still works for one release, and says it is now `tenant2backend` {{< added "2026-11-19" >}}
- [ ] Every image, the Pi's, the virtual machine for amd64 and arm64, the OVA, the VHDX and the ISO, is rebuilt with it and passes the self-test, every check {{< added "2026-11-19" >}}
- [ ] EdS's backend image builds on the new Pi image {{< added "2026-11-19" >}}
- [ ] Every image is in the tenant downloads with its sha256, and the tenant guide and Deevnet Software name `tenant2backend` {{< added "2026-11-19" >}}

**The choices, the owner's, 2026-11-19.** The name is `tenant2backend`: every subcommand configures
or checks the backend, and the name says what the move makes of a tenant. Only names an owner
meets change. The app contract keeps Deevnet's names (`DEEVNET_TENANT`, `X-Deevnet-Partition`, the
data source UIDs), so an app still moves with one `kit.env`. Images already flashed keep
`deevnet-kit`: there is no upgrade in place.

**2026-11-19, the owner: the Pi image is proven on the new production EdS Pi.** Its run on real
hardware, and with it the Pi image's publish, waits for that Pi, which the owner builds next; v5
closes when it has run. The other images are proven and published without waiting. No point above
changed.

**Not in v5:** the log bridge's and the PKI tools' names (`deevnet-log-bridge`, `deevnet-pki-*`),
which come from other repositories (Later); dropping the `deevnet-kit` alias (the release after).

### Later

- VMware Workstation and Fusion: the OVA may import there, unproven
- A run on a real VirtualBox, Hyper-V or UTM host, bridged on Wi-Fi
- A prebuilt `.utm` bundle that opens with its settings made, if UTM documents its format
- UTM's Apple Virtualization backend, from a raw disk
- A NAT fallback, if bridging proves too hard on some Wi-Fi adapters
- A live, run-from-USB mode for the ISO
- Wi-Fi on the installed system: setup asks for the network when no cable is found
- A keyboard layout chosen at setup, for every medium
- Secure Boot proven on real hardware (v2 proved it in qemu)
- The ISO installed on a real machine
- Every medium moved to trixie together
- The log bridge and the PKI tools renamed like the kit, if the owner wants them to be
- The `deevnet-kit` alias dropped, one release after v5
- A DHCP server's host name no longer replaces the one set at setup (seen in qemu, whose DHCP sends one)
- One `make` target that builds every take-home image, and one that boots each and runs its self-test unattended, with the test harness kept in `deevnet-image-factory`: a change to the backend is then one build, one proof and one push

---

## Records ✅

- ✅ [ADR-0044](/docs/architecture/decisions/tenant-model/0044-take-home-media/), Accepted 2026-11-17: one backend on several media, each from its vendor's image by the same play {{< added "2026-11-17" >}}
- ✅ [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/), Complete 2026-11-17: building and publishing the virtual machine image {{< added "2026-11-17" >}}

## amd64 inputs ✅

- ✅ deevnet-kit and the log bridge built for amd64 and staged at their pinned versions {{< added "2026-11-17" >}}
- ✅ silo for amd64 taken from the amd64 image Deevnet runs, built from the same release, so no build crosses the core router {{< added "2026-11-17" >}}
- ✅ The upstream amd64 releases (VictoriaLogs, vmutils, Grafana and its plugin, the alerting and notification services) staged with pinned sha256 {{< added "2026-11-17" >}}

## The image ✅

- ✅ Build method chosen, 2026-11-17: Debian 12's official `nocloud` image, mounted, then the configuration play, as the Pi image starts from Raspberry Pi OS {{< added "2026-11-17" >}}
- ✅ The configuration play takes the architecture and the medium as variables, with the Pi-only steps (boot partition files) kept to the Pi {{< added "2026-11-17" >}}
- ✅ A `make` target builds a bookworm amd64 qcow2 {{< added "2026-11-17" >}}

## First boot ✅

- ✅ `deevnet-kit setup`, a console prompt for the user, password or SSH key, and the host name, which runs before deevnet-kit's first boot {{< added "2026-11-17" >}}

## Proof ✅

- ✅ The self-test passes every check under qemu on the Builder {{< added "2026-11-17" >}}
- ✅ `tdemo` across with its `kit.env`: a test client publishes and its log shows in Grafana {{< added "2026-11-17" >}}

## Publish ✅

- ✅ A publish target puts the image under `tenant/vm` with its sha256, pushed throttled to the observability store {{< added "2026-11-17" >}}
- ✅ A section in the tenant guide: import, bridged networking, the first-boot prompt {{< added "2026-11-17" >}}

---

## v2 records ✅

- ✅ [CHG-0075](/docs/changes/2026/0075-take-home-installer-iso/), Complete 2026-11-17: building and publishing the installer ISO {{< added "2026-11-17" >}}
- ✅ No ADR: the ISO writes the virtual machine's disk unchanged, so ADR-0044's one way of making the system holds {{< added "2026-11-17" >}}

## v2 installer ✅

- ✅ Boot design chosen, 2026-11-17: everything from the v1 disk, its kernel with an installer initramfs made by its `initramfs-tools`, its GRUB for BIOS, and Debian's signed shim and CD GRUB for UEFI; the v1 disk carried compressed, and nothing downloaded {{< added "2026-11-17" >}}
- ✅ The installer lists the disks, refuses the one it booted from, asks the owner to type the chosen disk's name, writes the system and checks what it wrote, then asks to remove the stick and reboots {{< added "2026-11-17" >}}
- ✅ A hybrid ISO, bootable on UEFI and BIOS, through Debian's signed shim and GRUB {{< added "2026-11-17" >}}
- ✅ One `make` target builds the ISO from the v1 build's disk {{< added "2026-11-17" >}}

## v2 proof ✅

- ✅ BIOS: the ISO installs to a blank virtual disk in qemu, and the installed system boots alone {{< added "2026-11-17" >}}
- ✅ UEFI: the same with OVMF {{< added "2026-11-17" >}}
- ✅ The installed system's first boot asks on the console, grows its root, and passes the self-test {{< added "2026-11-17" >}}
- ✅ Secure Boot tried with OVMF's Secure Boot firmware: the ISO and the installed system boot with it on, and the self-test passes {{< added "2026-11-17" >}}

## v2 publish ✅

- ✅ A publish target puts the ISO under `tenant/iso` with its sha256, pushed throttled and detached to the observability store {{< added "2026-11-17" >}}
- ✅ A section in the tenant guide: write the stick, boot, choose the disk, then setup as on the VM {{< added "2026-11-17" >}}

---

## v3 records ✅

- ✅ [CHG-0076](/docs/changes/2026/0076-take-home-virtualbox-hyper-v/), Complete 2026-11-18: the VirtualBox and Hyper-V images converted, proven and published {{< added "2026-11-18" >}}

No ADR is expected: the formats carry the v1 disk unchanged, so ADR-0044 holds. One is written only
if a format needs the system itself changed.

## v3 formats ✅

- ✅ One `make` target converts the v1 build's disk: an OVA (a stream-optimized VMDK, an OVF descriptor with a bridged adapter, and a manifest of sha256s) and a VHDX for a Hyper-V Generation 2 machine, shipped zipped {{< added "2026-11-18" >}}
- ✅ Each disk compared with the v1 disk, and the OVA's descriptor and manifest checked {{< added "2026-11-18" >}}

## v3 proof ✅

- ✅ The OVA's disk boots in qemu in VirtualBox's firmware for it: setup, root grown, self-test every check {{< added "2026-11-18" >}}
- ✅ The VHDX boots in qemu under OVMF with Secure Boot, as a Generation 2 machine does: setup, root grown, self-test every check {{< added "2026-11-18" >}}

## v3 publish ✅

- ✅ A publish target puts both under `tenant/vm` with their sha256s, pushed throttled and detached to the observability store {{< added "2026-11-18" >}}
- ✅ Tenant guide sections for VirtualBox and Hyper-V: import, the bridged adapter or external switch, and Hyper-V's Secure Boot template {{< added "2026-11-18" >}}

## v4 records ✅

- ✅ [CHG-0077](/docs/changes/2026/0077-take-home-utm/), Complete 2026-11-18: the arm64 build for UTM, its proof and its publish {{< added "2026-11-18" >}}

No ADR is expected: the arm64 build is the same system by the same play, as ADR-0044 decided for
every medium. One is written only if arm64 needs the system itself changed.

## v4 builder ✅

- ✅ `qemu-system-aarch64` and an arm64 UEFI firmware on the Builder, through `deevnet.builder` {{< added "2026-11-18" >}}

## v4 build ✅

- ✅ A `make` target builds the arm64 qcow2 from Debian's bookworm arm64 image, with the Pi's arm64 inputs and the same play, and writes its sha256 {{< added "2026-11-18" >}}

## v4 proof ✅

- ✅ It boots in qemu as UTM's QEMU backend boots it: setup, root grown, self-test every check {{< added "2026-11-18" >}}

## v4 publish ✅

- ✅ Under `tenant/vm` with its sha256, pushed throttled and detached to the observability store {{< added "2026-11-18" >}}
- ✅ A tenant guide section for UTM: the wizard, the disk imported, and the Bridged network {{< added "2026-11-18" >}}

## v5 records 🔄

- 🔄 [ADR-0045](/docs/architecture/decisions/tenant-model/0045-take-home-tool-owners-name/), Proposed 2026-11-19: the take-home tool carries the owner's name, and the app contract keeps Deevnet's {{< added "2026-11-19" >}}
- 🔄 [CHG-0078](/docs/changes/2026/0078-take-home-tenant2backend/), In progress: the rename, the rebuilt images and their publish {{< added "2026-11-19" >}}

## v5 kit ✅

- ✅ `tenant2backend` in `deevnet-provisioning-api`, with its `backend` files, reading an old card's `deevnet-kit.txt`, released and staged (v0.28.0) {{< added "2026-11-19" >}}
- ✅ `deevnet-kit` kept as an alias that works and says the new name {{< added "2026-11-19" >}}

## v5 images 🔄

- ✅ The configuration play installs `tenant2backend`, its units, paths and group, and the alias; every image target pins the new release {{< added "2026-11-19" >}}
- 🔄 EdS's backend build accepts the new names (EdS #123, a draft until the new Pi image has run) {{< added "2026-11-19" >}}

## v5 proof 🔄

- 🔄 Every image rebuilt passes the self-test: the virtual machines and the ISO in qemu on the Builder, the Pi image on a Pi of the Pi lab {{< added "2026-11-19" >}}

## v5 publish 🔄

- 🔄 Every image under `tenant/` with its sha256, pushed throttled and detached to the observability store: five of six on 2026-11-19, the Pi image after the EdS Pi {{< added "2026-11-19" >}}
- ✅ The tenant guide and Deevnet Software name `tenant2backend`, with a note for older images {{< added "2026-11-19" >}}
