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
- **Disposable authority** — Hands off control to OPNsense once the substrate is running

"Bring one box, provision everything."

---

## Physical Model

The bootstrap node is typically a small x86 PC:

| Attribute | Requirement |
|-----------|-------------|
| **Form factor** | Mini PC, NUC-style, or small 1U |
| **NICs** | Dual-NIC minimum (upstream + substrate) |
| **Storage** | Sufficient for artifacts (~500GB recommended) |
| **OS** | Fedora with `deevnet.builder` collection applied |

The same physical device can be moved between substrates:
- **dvntm** — Mobile/portable lab
- **dvnt** — Home infrastructure

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

During initial provisioning, the bootstrap node may NAT traffic for substrate hosts. Once OPNsense is configured, routing authority transitions.

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
| **PXE/TFTP** | dnsmasq | Network boot for bare-metal hosts |
| **DNS** | dnsmasq | Name resolution during bootstrap |
| **DHCP** | dnsmasq | IP assignment during bootstrap |

All infrastructure Git repositories are checked out locally.

---

## Services Configured (Not Hosted)

The bootstrap node **configures** these services, which run on separate devices:

| Target | Collection | Purpose |
|--------|------------|---------|
| **OPNsense** | `deevnet.net` | Firewall, router, production DNS/DHCP |
| **Omada controller** | `deevnet.builder` | TP-Link switch and AP management |
| **Proxmox** | `deevnet.builder` | Hypervisor for VMs |
| **Substrate hosts** | `deevnet.builder` | Admin nodes, compute, storage |

The bootstrap node is the automation source; the services themselves run elsewhere.

---

## Authority Modes

Per the [Correctness Standard](/docs/standards/correctness/#52-authority-modes-are-explicit), provisioning operates in one of two modes:

### Bootstrap-Authoritative

During initial substrate provisioning:
- Bootstrap node provides DNS, DHCP, and gateway services
- All substrate hosts depend on the bootstrap node for network identity
- OPNsense is not yet configured (or is being provisioned)

### OPNsense-Authoritative

After OPNsense is running:
- OPNsense provides DNS, DHCP, and gateway services
- Bootstrap node's dnsmasq is disabled or restricted
- Bootstrap node becomes a regular admin host

**The transition between modes is explicit, not automatic.**

---

## Provisioning Workflow

1. **Connect upstream**: Bootstrap node plugs into host network, gets internet access
2. **Activate downstream**: Bootstrap node's substrate interface comes up with static IP
3. **Start services**: dnsmasq (DHCP/DNS/TFTP) and nginx (artifacts) start
4. **PXE boot targets**: Bare-metal hosts boot from bootstrap node
5. **Provision OPNsense**: OPNsense VM is installed and configured via Ansible
6. **Transition authority**: DHCP/DNS moves to OPNsense
7. **Bootstrap becomes admin**: dnsmasq stops; bootstrap node is now just another host

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

- **[Artifacts Server](artifacts-server/)** — nginx-based artifact hosting for air-gapped provisioning
- **[Workstation](workstation-role/)** — Developer tools, users, and environment setup
- **[Omada Controller](omada-controller-role/)** — TP-Link network controller management

---

## Summary

The bootstrap node is the entry point for substrate provisioning:

1. **One device** contains all automation and artifacts
2. **Dual-homed** between upstream network and substrate
3. **Temporarily authoritative** for DNS/DHCP during bootstrap
4. **Configures** OPNsense, Omada, and all substrate hosts
5. **Transitions** to regular admin role once substrate is running
