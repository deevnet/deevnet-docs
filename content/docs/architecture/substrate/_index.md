---
title: "Substrate"
weight: 1
bookCollapseSection: true
---

# Substrate Architecture

A **substrate** is an infrastructure environment—a self-contained network with its own compute, storage, and management plane.

---

## Substrate Definitions

| Substrate | Purpose |
|-----------|---------|
| **dvntm** | Mobile/portable lab for development, testing, and demos |
| **dvnt** | Production home infrastructure (always-on, stable) |

Each substrate:
- Has its own IP address space and routing
- Operates independently (can function without the other)
- Contains a complete infrastructure stack (management plane, network, compute)
- Has its own DNS zone (`dvntm.deevnet.net`, `dvnt.deevnet.net`)

The same physical bootstrap node can move between substrates—it provisions whichever environment it's connected to.

---

## Infrastructure Layers

```
┌─────────────────────────────────────────────────────────┐
│              Substrate Infrastructure                   │
├─────────────────────────────────────────────────────────┤
│  Management Plane │ Bootstrap node (provisioning,      │
│                   │ artifacts, PXE/TFTP)               │
├───────────────────┼─────────────────────────────────────┤
│  Network          │ Core Router (gateway, firewall,    │
│                   │ DNS, DHCP), switches, APs          │
├───────────────────┼─────────────────────────────────────┤
│  Compute          │ Proxmox hypervisors, Raspberry Pis,│
│                   │ embedded devices                   │
└───────────────────┴─────────────────────────────────────┘
```

### Management Plane

The management plane consists of out-of-band provisioning and centralized services:

**Bootstrap Node** — Out-of-band provisioning for initial substrate setup:
- Hosts artifact server (nginx) for images, ISOs, packages
- Runs PXE/TFTP for bare-metal provisioning
- Provides DNS/DHCP during initial bootstrap
- Configures all other substrate components via Ansible

**Management Plane Node** — Hypervisor-based centralized services:
- Secrets management
- Centralized logging and metrics
- Automation runners and CI/CD

See [Builder](builder/) for the bootstrap node architecture.
See [Management Plane](management-plane/) for the virtual management services.

### Network

The **Core Router** is the production network authority:
- Firewall and NAT gateway
- Authoritative DNS for substrate zone
- DHCP with static mappings
- Inter-segment routing with VLAN isolation

See [Networking](networking/) for the network segmentation model.

### Compute

**Proxmox hypervisors** host virtualized workloads:
- Management-plane VMs (observability, automation, access)
- Tenant application VMs

**Raspberry Pis and embedded devices** handle edge workloads:
- SDR, IoT gateways, sensors

---

## Authority Modes

Substrate provisioning uses **explicit authority transitions**:

| Mode | DNS/DHCP Authority | When |
|------|-------------------|------|
| **Bootstrap-authoritative** | Bootstrap node (dnsmasq) | During initial provisioning |
| **Router-authoritative** | Core Router | Production operation |

The transition is explicit—once the Core Router is configured and validated, the bootstrap node stops serving DNS/DHCP and becomes a regular admin host.

See [Management Plane](management-plane/) for details on authority models.

---

## Child Documents

- [Networking](networking/) — Network segmentation and VLAN model
- [Management Plane](management-plane/) — Infrastructure management, DNS authority, and VM-based services
- [Builder](builder/) — Bootstrap node and provisioning architecture
