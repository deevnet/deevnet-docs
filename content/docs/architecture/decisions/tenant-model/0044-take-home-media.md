---
title: "ADR-0044: Take-Home Media"
weight: -44
---

# ADR-0044: The Take-Home Backend Is One Backend on Several Media, Each Built From Its Vendor's Image by the Same Play

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-11-17 |
| **Scope** | How the take-home backend reaches a medium other than a Raspberry Pi card: what every medium shares, what each may differ in, what each starts from, and how an owner sets one up with no boot partition to edit. Not what the backend runs (the [take-home Pi image](/docs/runbook/tenant/tenant-to-pi-image/)), not its certificates ([ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/)) |
| **Related** | [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/) and its [proposal](/docs/architecture/proposals/take-home-vm-and-iso/), [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/), [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) |

---

## Context

**A tenant takes its backend home on a Raspberry Pi**, flashed from the `pi-backend` image: broker,
log and metrics stores, alerting, buckets and Grafana on one card, with `deevnet-kit` doing what
the API does on a site. The image is built from Raspberry Pi OS by one configuration play, and the
owner sets the card up by editing its boot partition before the first boot.

**Take-Home Media adds other media**: an amd64 virtual machine image first, then an ISO for an
owner's own hardware, then the formats for a computer's hypervisors. Each needs a base, a build and
a way for the owner to set it up. A second backend for each would drift from the first, and the
contract an app moves across with is the point of taking it home.

**CHG-0074 built the virtual machine** and proved it on the Builder under qemu, which is where
these choices were tested.

## Decision

### 1. One backend, whatever the medium

**Every medium carries the same backend**: the same services at the same versions, the same
`deevnet-kit`, the same app contract and the same self-test. They are built by **one configuration
play**, `pi-backend-config.yml`, with the medium as a parameter. The parameter covers only what the
medium decides: how the owner's settings arrive, what the base image lacks or leaves open, and the
hardware's own needs, such as a Pi's clock. A change to the backend lands on every medium.

### 2. Each medium starts from its vendor's own image, pinned

**A medium's base is its vendor's published image, at a dated build, checked against the vendor's
checksum**, then configured offline by the play. The Pi starts from Raspberry Pi OS Lite; the
virtual machine starts from Debian's `nocloud` image. No medium runs an installer to make its
image, and none uses cloud-init.

**What a base image leaves open is closed by the play, and the build fails if it is not.** Raspberry
Pi OS gains the build's automation user from the shared Packer step, which the play removes.
Debian's `nocloud` image lets root sign in with no password, which the play locks.

### 3. Without a boot partition, the console asks

**A medium the owner cannot edit before its first boot asks on its console, once**, through
`deevnet-kit setup`, for what a Pi's owner writes on the card: the tenant, its index and the host
name, and the owner's login, with a password and optionally an SSH key. With a key, SSH takes keys
only. Setup writes the settings where first boot reads them, and first boot then runs as on a Pi.
The image has no user of its own, so until setup has run, nothing can sign in.

### 4. Bridged networking only

**A medium that runs under a hypervisor takes its own address on the owner's network.** Devices
connect to the backend, so it cannot sit behind the hypervisor's NAT. A NAT fallback is not
offered.

### 5. One base release across media

**Every medium uses the same Debian release**, today bookworm, so that the packages beneath the
backend, such as Mosquitto and Podman, are the same on every medium. The media move to a new
release together.

## Consequences

- **An app moves to any medium with the same `kit.env` shape**, and a fix to `deevnet-kit` or the
  play reaches every medium at its next build.
- **Each medium needs its architecture's binaries.** The Pi needs arm64 builds and the virtual
  machine amd64 builds of every input, staged once per version, and the pins carry a checksum for
  each.
- **A medium may lack what another has.** The virtual machine has no Wi-Fi of its own and no
  boot-partition README; the Pi has no console prompt. The guide says where they differ.
- **The console's keyboard is a US layout**, because the base image configures none. An owner whose
  password needs other characters types it as a US keyboard would.

## Alternatives considered

- **A separate build for each medium**, such as Packer with Debian's installer for the virtual
  machine: more control over partitioning, but a second build style and a second place for the
  backend to drift. Rejected in favor of the vendor's image and the same play.
- **cloud-init for the virtual machine's settings**: native on Proxmox, but awkward on the
  hypervisors of a computer, and a second first-boot path to keep. Rejected; the console works on
  every hypervisor and on the ISO's installed system.
- **NAT with port forwarding**: works where bridging is hard, but every device and app would need
  the host's address and forwarded ports. Left for later, if bridging proves too hard on some Wi-Fi
  adapters.

## To accept

**This record is accepted when every item below is done.**

- [x] Built by change records: [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/) (the virtual machine).
- [x] Proven on the Builder under qemu: the console prompt, a self-test passing every check, and a tenant moved across with its `kit.env` (CHG-0074, Step 5).
- [ ] The virtual machine image in the tenant downloads (CHG-0074, Step 6).
