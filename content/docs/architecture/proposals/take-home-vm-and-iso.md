---
title: "Take-Home VM and ISO"
---

# Proposal: Take-Home VM and ISO Images

| | |
|---|---|
| **Status** | Accepted 2026-11-17, not built: [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/) |
| **Date** | 2026-11-17 |
| **Where** | deevnet-image-factory builds it; tenant downloads on the observability store publish it |
| **Would extend** | [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/), [Convert a Tenant to a Pi Image](/docs/runbook/tenant/take-it-home/), CHG-0025 tenant downloads |

A tenant takes its backend home today on a Raspberry Pi, flashed from the `pi-backend` image. This
proposal adds the same backend on two more media: a **virtual machine image** for a hypervisor at
home or on your computer, and an **ISO** that installs it on hardware of your own. All three carry
one backend, one deevnet-kit, one self-test and one app contract. Only the medium differs.

## Why

**A tenant without a Pi has no way to take its project home.** A meetup attendee who has no Pi, or
doesn't want one, has nowhere to run the backend after leaving. Someone with a home lab or a spare
mini-PC already has a better place for it than an SD card.

## What it is

**The VM and the ISO carry the Pi's backend, unchanged, on a different medium.**

- **It is the Pi's backend on amd64.** The same Debian base, Mosquitto, Podman, VictoriaLogs,
  metrics, alerting, ntfy, Grafana, silo and deevnet-kit, built by the same offline configuration
  play. That play already works on a mounted root and runs nothing of the image's architecture.
- **The first boot asks on the console.** A VM disk has no boot partition to edit, so the VM and
  the installed system ask on the console for the user, the sign-in (password or SSH key) and the
  host name. deevnet-kit then generates the CA and the secrets, as on the Pi.
- **Bridged networking is required.** Devices reach the backend at `<hostname>.local`, so the VM
  needs its own address on your network. The guide says so plainly.
- **It is published beside the Pi image** in tenant downloads, under `tenant/vm` and `tenant/iso`
  with a sha256 beside each, so a meetup fetches it on site.

## What it is not

**The backend's design, its contract and its independence from Deevnet stay the Pi's.**

- **It is not a second backend design.** The app contract, the kit and the self-test stay the
  Pi's, and a change to them lands on every medium.
- **It is not a Deevnet host.** Like the Pi, it has no Deevnet account, key or route.
- **It does not do NAT or port forwarding.** Bridged networking only.
- **It does not use cloud-init.** The console prompt is the only first-boot path.

## The MVP

**The MVP is an amd64 qcow2 for Proxmox and KVM.** One `make` target builds it on the Builder,
it is proven there under qemu with the self-test passing, and it is published to tenant downloads.
On the first day, the owner imports it into a hypervisor, answers the console prompt, moves
`tdemo` across with its `kit.env`, and sees the tenant's devices and dashboards work.

## Versions

**Each version adds one medium, starting with the one easiest to build and prove.**

- **v1, the MVP:** an amd64 qcow2 for Proxmox and KVM, with a console first boot, the self-test
  passing, and the image published.
- **v2:** an ISO that installs the same amd64 system on your own hardware.
- **v3:** the VM on your computer, with OVA and VHDX (VirtualBox, Hyper-V) converted from the same
  amd64 disk, plus an arm64 image for UTM on Apple Silicon.
- **Later:** a guide section for each hypervisor, a NAT fallback if bridging proves too hard on
  some Wi-Fi adapters, and a live, run-from-USB mode for the ISO.

## Open questions

**These are decided or found out before the version that needs them.**

- **ISO shape:** an unattended wipe-and-install, or a live system with an optional install. The
  owner decides before v2.
- **amd64 builds:** the kit, the log bridge and silo ship for arm64 only today. Building silo for
  amd64 downloads its sources across the core router, so it needs the throttled path and the owner
  at the console.
- **Build method:** debootstrap into a raw disk and then the offline play, or Packer with qemu.
  Found out in v1. It needs an ADR if it changes how the factory builds images.
- **Base release:** settled on acceptance: bookworm, to match the Pi. All media move to trixie
  together, later.
- **Where it is proven:** on the Builder under qemu, never on a hypervisor.
- **ADR:** whether a new ADR records the VM and ISO as take-home media beside the Pi, or ADR-0041
  is extended.
