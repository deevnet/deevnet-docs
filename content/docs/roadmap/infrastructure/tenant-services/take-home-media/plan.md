---
title: "Take-Home Media: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 1
tasks_in_progress: 1
tasks_planned: 11
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
- An amd64 virtual machine image, then an installer ISO, then the formats for an owner's computer
- A first boot that asks on the console for the user, the sign-in and the host name
- Publishing each beside the Pi image in the tenant downloads

**Out of Scope**
- A second backend design: a change to the contract, the kit or the self-test lands on every medium
- NAT or port forwarding: the virtual machine needs bridged networking
- cloud-init: the console prompt is the only first-boot path

---

## Versions

### v1, the MVP (current)

An amd64 qcow2 of the tenant backend for Proxmox and KVM, on Debian bookworm like the Pi image.

**Done when:**

- [ ] deevnet-kit, the log bridge and silo are built for amd64 and staged on the artifact server, each with its sha256
- [ ] One `make` target on the Builder builds the qcow2 from the same configuration play as the Pi image
- [ ] Its first boot asks on the console for the user, the sign-in (password or SSH key) and the host name, then deevnet-kit makes the CA and the secrets
- [ ] The self-test passes every check under qemu on the Builder
- [ ] `tdemo` moves across with its `kit.env`: a test client publishes, and its log shows in Grafana
- [ ] The image is in the tenant downloads under `tenant/vm` with its sha256, and the tenant guide has a section for it

It is proven on the Builder under qemu only, never on the lab's hypervisors. A bridged run on a
real hypervisor comes with v3, or the first time someone imports it.

**Not in v1:** the ISO (v2); OVA, VHDX and arm64 for UTM (v3); trixie (all media move together, later).

### v2 (next)

An ISO that installs the same amd64 system on an owner's own hardware. Its shape, an unattended
wipe-and-install or a live system with an optional install, is decided before v2 starts.

### v3

The virtual machine on an owner's computer: OVA and VHDX (VirtualBox, Hyper-V) converted from the
v1 disk, and an arm64 image for UTM on Apple Silicon from the Pi's arm64 inputs.

### Later

- A tenant guide section for each hypervisor
- A NAT fallback, if bridging proves too hard on some Wi-Fi adapters
- A live, run-from-USB mode for the ISO
- Every medium moved to trixie together

---

## Records ⏳

- ⏳ An ADR that records the virtual machine and the ISO as take-home media beside the Pi, or extends ADR-0041
- 🔄 [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/): building and publishing the virtual machine image

## amd64 inputs ⏳

- ⏳ deevnet-kit and the log bridge built for amd64 and staged at their pinned versions
- ⏳ silo for amd64 taken from the amd64 image Deevnet runs, built from the same release, so no build crosses the core router
- ⏳ The upstream amd64 releases (VictoriaLogs, vmutils, Grafana and its plugin, the alerting and notification services) staged with pinned sha256

## The image ⏳

- ✅ Build method chosen, 2026-11-17: Debian 12's official `nocloud` image, mounted, then the configuration play, as the Pi image starts from Raspberry Pi OS
- ⏳ The configuration play takes the architecture and the medium as variables, with the Pi-only steps (boot partition files) kept to the Pi
- ⏳ A `make` target builds a bookworm amd64 qcow2

## First boot ⏳

- ⏳ `deevnet-kit setup`, a console prompt for the user, password or SSH key, and the host name, which runs before deevnet-kit's first boot

## Proof ⏳

- ⏳ The self-test passes every check under qemu on the Builder
- ⏳ `tdemo` across with its `kit.env`: a test client publishes and its log shows in Grafana

## Publish ⏳

- ⏳ A publish target puts the image under `tenant/vm` with its sha256, pushed throttled to the observability store
- ⏳ A section in the tenant guide: import, bridged networking, the first-boot prompt
