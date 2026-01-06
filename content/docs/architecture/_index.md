---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

System-level design intent and contracts between layers.

---

## Substrate and Tenant Model

Deevnet uses a **two-layer architecture** that separates infrastructure environments from application workloads.

### Substrates

A **substrate** is an infrastructure environment—a self-contained network with its own compute, storage, and control plane.

| Substrate | Purpose |
|-----------|---------|
| **dvntm** | Mobile/portable lab for development, testing, and demos |
| **dvnt** | Production home infrastructure (always-on, stable) |

Each substrate:
- Has its own IP address space and routing
- Operates independently (can function without the other)
- Contains a complete infrastructure stack (control plane, network, compute)
- Has its own DNS zone (`dvntm.deevnet.net`, `dvnt.deevnet.net`)

The same physical bootstrap node can move between substrates—it provisions whichever environment it's connected to.

### Tenants

A **tenant** is a logical workload namespace representing an application or service domain.

Examples: `grooveiq`, `vintronics`, `moneyrouter`

Tenants:
- Live **on** substrates, not defining them
- May be deployed to one or more substrates
- Express **intent** (what's running), not **identity** (what the host is)
- Use DNS pattern: `service.tenant.substrate.deevnet.net`

**Example:** `api.grooveiq.dvntm.deevnet.net` — the API service for grooveiq tenant running on the dvntm substrate.

---

## Infrastructure Layers

```
┌─────────────────────────────────────────────────────────┐
│                  Tenants (Workloads)                    │
│         grooveiq, vintronics, moneyrouter, etc.         │
└────────────────────────┬────────────────────────────────┘
                         │ runs on
┌────────────────────────▼────────────────────────────────┐
│              Substrate Infrastructure                   │
├─────────────────────────────────────────────────────────┤
│  Control Plane    │ Bootstrap node (provisioning,      │
│                   │ artifacts, PXE/TFTP)               │
├───────────────────┼─────────────────────────────────────┤
│  Network          │ OPNsense (gateway, firewall,       │
│                   │ DNS, DHCP), switches, APs          │
├───────────────────┼─────────────────────────────────────┤
│  Compute          │ Proxmox hypervisors, Raspberry Pis,│
│                   │ embedded devices                   │
└───────────────────┴─────────────────────────────────────┘
```

### Control Plane

The **bootstrap node** is the entry point for standing up a substrate:
- Hosts artifact server (nginx) for images, ISOs, packages
- Runs PXE/TFTP for bare-metal provisioning
- Provides DNS/DHCP during initial bootstrap
- Configures all other substrate components via Ansible

### Network

**OPNsense** is the production network authority:
- Firewall and NAT gateway
- Authoritative DNS for substrate zone
- DHCP with static mappings
- Inter-segment routing with VLAN isolation

See [Substrate Networking](substrate-networking/) for the network segmentation model.

### Compute

**Proxmox hypervisors** host virtualized workloads:
- Infrastructure VMs (OPNsense, test environments, CI runners)
- Tenant application VMs

**Raspberry Pis and embedded devices** handle edge workloads:
- SDR, IoT gateways, sensors

---

## Authority Modes

Substrate provisioning uses **explicit authority transitions**:

| Mode | DNS/DHCP Authority | When |
|------|-------------------|------|
| **Bootstrap-authoritative** | Bootstrap node (dnsmasq) | During initial provisioning |
| **OPNsense-authoritative** | OPNsense router | Production operation |

The transition is explicit—once OPNsense is configured and validated, the bootstrap node stops serving DNS/DHCP and becomes a regular admin host.

---

## Design Principles

### Substrate Independence

Each substrate (dvntm, dvnt) must be operable independently. No cross-substrate dependencies for core functionality.

### Identity vs Intent

Hosts have **stable identity** (hostname, MAC, IP) that doesn't change when workloads change. Workloads express **intent** and can move between hosts via DNS CNAMEs.

See [Inventory vs Intent](../inventory/inventory-vs-intent/) for details.

### Air-Gapped Provisioning

Substrate infrastructure can be provisioned without upstream internet access. The artifact server hosts all required images, packages, and configurations.

### Config-as-Code

All infrastructure configuration lives in version-controlled repositories:
- `ansible-inventory-deevnet` — Host identity and variables
- `ansible-collection-deevnet.builder` — Provisioning roles
- `ansible-collection-deevnet.net` — Network configuration
- `deevnet-image-factory` — OS image builds

