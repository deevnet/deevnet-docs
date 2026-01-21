---
title: "Core Router"
weight: 2
bookCollapseSection: true
---

# Core Router

## Purpose

The core router is the **production network authority** for each Deevnet substrate. It provides routing, firewall, DNS, DHCP, and gateway services for all substrate hosts.

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | Proxmox VM | Virtualized for portability |
| **dvnt** | Proxmox VM or dedicated appliance | TBD based on performance needs |

### Selection Rationale

Running the core router as a VM on Proxmox provides:
- Portability for the mobile substrate
- Snapshot and backup capabilities
- Consistent deployment model across substrates

Dedicated hardware may be considered for dvnt if performance requirements exceed VM capabilities.

---

## Operating System

| Attribute | Current | Target |
|-----------|---------|--------|
| **OS** | OPNsense (FreeBSD-based) | VyOS (Debian-based) |
| **Version** | OPNsense 24.x | VyOS rolling release |

### Automation Capability

**OPNsense (Current)**:
- API-based configuration via `deevnet.net` collection
- **No PXE boot support** — requires manual USB installation
- Day-2 automation is good; initial provisioning is manual

**VyOS (Target)**:
- cloud-init support for automated initial configuration
- Official `vyos.vyos` Ansible collection
- CLI-centric, designed for automation
- ISO can be staged on artifact server for air-gap deployment

---

## VyOS Migration Evaluation

OPNsense has served well for production routing but has a critical limitation: **no automated installation support**. This creates an air-gap in the otherwise automated substrate provisioning workflow.

### Why VyOS?

| Requirement | OPNsense | VyOS |
|-------------|----------|------|
| Automated install | No PXE, manual USB only | cloud-init + staged ISO |
| Air-gap recovery | Manual reinstall | Staged ISO, automated |
| Config-as-code | API-based | Native CLI + Ansible |
| Day-2 automation | Good (Ansible) | Excellent (vyos.vyos) |
| WebUI | Yes | No (CLI-centric) |

### Tradeoffs Accepted

- **No WebUI**: All management via CLI or Ansible. Aligns with config-as-code principles.
- **Rolling release**: LTS requires subscription. Rolling is free and acceptable for homelab.

### Migration Status

| Phase | Status |
|-------|--------|
| Platform evaluation | Complete |
| Manual testing (Proxmox VM) | Pending |
| cloud-init automation | Pending |
| Ansible roles | Pending |
| Production cutover | Pending |

---

## Roles

The core router provides the following services (documented in sub-pages):

| Role | Description |
|------|-------------|
| **DNS** | Authoritative for substrate zone, forwarder for upstream |
| **DHCP** | Static mappings for known hosts, pool for dynamic clients |
| **Firewall** | NAT, inter-subnet rules, future VLAN isolation |
| **Gateway** | Default route for all substrate traffic |

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│    Upstream     │◄────►│   Core Router    │◄────►│  Substrate Hosts    │
│   (Edge Router) │      │                  │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

| Substrate | Upstream Connection |
|-----------|---------------------|
| **dvntm** | Travel router (portable WAN) |
| **dvnt** | ISP router (home internet) |

---

## Configuration Management

### OPNsense (Current)

Configured via the `deevnet.net` Ansible collection:

| Component | Management |
|-----------|------------|
| DNS records | Pushed from inventory |
| DHCP static mappings | Pushed from inventory |
| Firewall rules | Defined in playbooks |
| WoL targets | Defined in inventory |

### VyOS (Target)

Will be configured via the `vyos.vyos` Ansible collection:

| Component | Module |
|-----------|--------|
| Interfaces | `vyos_interfaces` |
| Firewall rules | `vyos_firewall_rules` |
| System settings | `vyos_system`, `vyos_hostname` |
| Static routes | `vyos_static_routes` |

---

## Authority Transition

Per the [Correctness Standard](/docs/standards/correctness/#52-authority-modes-are-explicit):

1. During initial provisioning, the bootstrap node provides DNS/DHCP
2. Core router is provisioned and configured via Ansible
3. Authority explicitly transitions to core router
4. Bootstrap node's dnsmasq is disabled
5. Core router becomes the production DNS/DHCP server

**This transition is explicit, not automatic.**
