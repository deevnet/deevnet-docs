---
title: "Bootstrap Node"
weight: 1
bookCollapseSection: true
---

# Bootstrap Node

## Purpose

The bootstrap node is the **control plane** for standing up a Deevnet substrate. It's a single, portable device that contains everything needed to provision and configure an entire environment from scratch.

Goals:
- **Self-contained** — All automation, artifacts, and services on one device
- **Portable** — Move between substrates (dvntm, dvnt) as needed
- **Air-gapped capable** — Can provision without upstream internet once artifacts are staged
- **Disposable authority** — Hands off control to Core Router once the substrate is running

"Bring one box, provision everything."

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | Developer workstation | Portable laptop with dual-NIC capability |
| **dvnt** | Developer workstation | Desktop or mini PC (NUC-style) |

### Selection Rationale

The bootstrap node requires:

| Attribute | Requirement | Rationale |
|-----------|-------------|-----------|
| **Form factor** | Portable | Must move between substrates |
| **NICs** | Dual-NIC minimum | Upstream + substrate connectivity |
| **Storage** | ~500GB+ | Artifacts (ISOs, images, packages) |
| **RAM** | 16GB+ | Ansible execution, artifact serving |
| **CPU** | Modern x86_64 | Packer builds, general automation |

The same physical device can serve both substrates:
- **dvntm** — Mobile/portable lab
- **dvnt** — Home infrastructure

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | Fedora Workstation |
| **Version** | Fedora 43+ |
| **Collection** | `deevnet.builder` applied |

### Automation Capability

- **PXE install**: Fedora supports fully automated kickstart installation via PXE
- **cloud-init**: Supported for VM deployments
- **Ansible**: Native Python support, no agent required
- **Air-gap**: OS and packages can be staged on artifact server

The bootstrap node is provisioned via PXE from another bootstrap node, or manually installed and then configured via Ansible self-application

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Host Network   │◄────►│  Bootstrap Node  │◄────►│  Substrate Network  │
│  (WAN/upstream) │      │   (dual-homed)   │      │    (dvntm/dvnt)     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

- **Upstream interface**: Connects to existing network (home, hotel, office) for internet access
- **Downstream interface**: Becomes the gateway for the substrate during bootstrap

During initial provisioning, the bootstrap node may NAT traffic for substrate hosts. Once Core Router is configured, routing authority transitions.

---

## Ansible Controller

The bootstrap node serves as the **Ansible controller** for the entire substrate. The `base` role provides:

- System hostname configuration
- Ansible installation
- Baseline packages (vim, curl, htop, python3, chrony, bind-utils, etc.)

All playbooks are executed from the bootstrap node, targeting substrate hosts via SSH.

---

## Services Hosted

The bootstrap node runs these services directly via the `bootstrap` role:

| Service | Implementation | Purpose |
|---------|----------------|---------|
| **Artifacts** | nginx | ISOs, images, netboot files, packages |
| **TFTP** | in.tftpd (systemd) | Network boot files (GRUB, kernel, initrd) |
| **Omada Controller** | Podman container | TP-Link switch and AP management (dvntm) |
| **UniFi Controller** | Podman container | Ubiquiti switch and AP management (dvnt) |

The network controllers are hosted on the bootstrap node because they must be available for initial switch and AP configuration before VLANs exist. See [Network Controllers](/docs/platforms/network/network-controllers/) for details.

In **Core Router-Authoritative** mode (normal operation), DHCP and DNS are provided by Core Router, not the bootstrap node. The bootstrap node only provides TFTP for PXE boot files.

See [PXE Boot Infrastructure](pxe-boot-infrastructure/) for details.

All infrastructure Git repositories are checked out locally.

---

## Services Configured (Not Hosted)

The bootstrap node **configures** these services, which run on separate devices:

| Target | Collection | Purpose |
|--------|------------|---------|
| **Core Router** | `deevnet.net` | Firewall, router, production DNS/DHCP |
| **Proxmox** | `deevnet.builder` | Hypervisor for VMs |
| **Substrate hosts** | `deevnet.builder` | Admin nodes, compute, storage |

The bootstrap node is the automation source; the services themselves run elsewhere.

---

## Authority Modes

Per the [Correctness Standard](/docs/standards/correctness/#52-authority-modes-are-explicit), provisioning operates in one of two modes:

### Bootstrap-Authoritative

During initial substrate provisioning (rare, greenfield only):
- Bootstrap node provides DNS, DHCP, and gateway services via dnsmasq
- All substrate hosts depend on the bootstrap node for network identity
- Core Router is not yet configured (or is being provisioned)

### Core Router-Authoritative (Normal Operation)

After Core Router is running (standard mode):
- Core Router (Kea) provides DNS and DHCP services
- Core Router provides gateway and routing
- Bootstrap node provides **TFTP only** for PXE boot
- Bootstrap node is a regular admin host

**Most PXE provisioning happens in Core Router-Authoritative mode** — Core Router Kea provides DHCP with PXE options (next-server, boot-file-name), and the bootstrap node serves boot files via TFTP.

**The transition between modes is explicit, not automatic.**

---

## Provisioning Workflow

### Core Router-Authoritative (Normal)

For adding new hosts to an existing substrate:

1. **Add DHCP reservation**: Create host entry in Core Router Kea with MAC, IP, and PXE options
2. **Add MAC config**: Add entry to `bootstrap_grub_mac_configs` in inventory
3. **Apply bootstrap role**: Generates MAC-specific GRUB config
4. **PXE boot host**: Host boots, gets DHCP from Core Router, TFTP from bootstrap node
5. **Automated install**: Kickstart completes without intervention

### Bootstrap-Authoritative (Greenfield)

For initial substrate buildout when Core Router doesn't exist:

1. **Connect upstream**: Bootstrap node plugs into host network, gets internet access
2. **Activate downstream**: Bootstrap node's substrate interface comes up with static IP
3. **Start services**: dnsmasq (DHCP/DNS/TFTP) and nginx (artifacts) start
4. **PXE boot targets**: Bare-metal hosts boot from bootstrap node
5. **Provision Core Router**: Core Router VM is installed and configured via Ansible
6. **Transition authority**: DHCP/DNS moves to Core Router, dnsmasq stops
7. **Bootstrap becomes admin**: Bootstrap node provides TFTP only

---

## Git Repository Layout

All Deevnet repositories are checked out to a standard location:

```
~/dvnt/
├── ansible-collection-deevnet.builder/   # Provisioning roles
├── ansible-collection-deevnet.net/       # Network device configuration
├── ansible-inventory-deevnet/            # Host inventory (dvnt, dvntm)
├── deevnet-image-factory/                # Packer image builds
└── deevnet-docs/                         # This documentation (submodule)
```

The inventory is substrate-specific. Running playbooks from the bootstrap node targets the connected substrate.

---

## Service Identity

Per the [Naming Standard](/docs/standards/naming/):

- `bootstrap.dvntm.deevnet.net` — The bootstrap node itself
- `artifacts.dvntm.deevnet.net` → `bootstrap.dvntm.deevnet.net` (CNAME)
- `pxe.dvntm.deevnet.net` → `bootstrap.dvntm.deevnet.net` (CNAME)

Per [Multihoming](/docs/standards/correctness/#33-multihoming-service-co-location), the bootstrap node hosts multiple services. This co-location is intentional and documented—blast radius is understood.

---

## Roles

The bootstrap node is configured using these `deevnet.builder` roles:

- **[PXE Boot Infrastructure](pxe-boot-infrastructure/)** — TFTP server and GRUB configs for network boot
- **[Artifacts Server](artifacts-server/)** — nginx-based artifact hosting for air-gapped provisioning
- **[Workstation](workstation-role/)** — Developer tools, users, and environment setup
- **[Omada Controller](omada-controller-role/)** — TP-Link network controller for dvntm
- **[UniFi Controller](unifi-controller-role/)** — Ubiquiti network controller for dvnt

---

## Summary

The bootstrap node is the entry point for substrate provisioning:

1. **One device** contains all automation and artifacts
2. **TFTP server** for PXE boot files (GRUB, kernel, initrd)
3. **Artifact server** for install media, kickstarts, and packages
4. **Network controllers** (Omada, UniFi) for switch and AP management
5. **Configures** Core Router and all substrate hosts via Ansible
6. **Core Router provides DHCP** with PXE options pointing to bootstrap node's TFTP
