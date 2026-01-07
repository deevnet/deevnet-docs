---
title: "VyOS Router"
weight: 3
---

# VyOS Router

## Purpose

VyOS is the **target router/firewall/gateway platform** for Deevnet substrates, selected to replace OPNsense. VyOS provides routing, DNS forwarding, DHCP, firewall, and VLAN services with full automation support.

---

## Decision Rationale

### Why Replace OPNsense?

OPNsense has served well for production routing but has a critical limitation: **no automated installation support**. OPNsense lacks PXE boot capability and requires manual USB installation, creating an air-gap in the otherwise automated substrate provisioning workflow.

| Requirement | OPNsense | VyOS |
|-------------|----------|------|
| Automated install | No PXE, manual USB only | cloud-init + staged ISO |
| Air-gap recovery | Manual reinstall | Staged ISO, automated |
| Config-as-code | API-based (deevnet.net) | Native CLI + Ansible |
| Day-2 automation | Good (Ansible collections) | Excellent (vyos.vyos) |
| WebUI | Yes | No (CLI-centric) |

### Why VyOS?

1. **Automation-first design**: VyOS is built for network automation with native cloud-init support and an official Ansible collection.

2. **Air-gap capability**: VyOS rolling release ISOs can be staged on the artifact server and deployed without internet access, matching the existing Fedora/Proxmox provisioning model.

3. **Official Ansible support**: The [vyos.vyos collection](https://galaxy.ansible.com/vyos/vyos) (v6.0.0, July 2025) provides modules for firewall, interfaces, routing, and configuration management.

4. **CLI-centric operations**: While lacking a WebUI, VyOS's CLI is designed for network operations and integrates naturally with config-as-code workflows. All configuration is text-based and version-controllable.

5. **Mature platform**: VyOS is a fork of Vyatta, with a long history in enterprise and homelab environments. It runs on Debian and supports x86 hardware and VMs.

### Tradeoffs Accepted

- **No WebUI**: All management via CLI or Ansible. This aligns with config-as-code principles but requires comfort with CLI-based troubleshooting.

- **Rolling release**: LTS releases require a subscription. Rolling release is free and acceptable for homelab use, with the vyos.vyos collection tested against current rolling builds.

---

## Platform Comparison

### Alternatives Evaluated

| Platform | Automated Install | WebUI | Notes |
|----------|-------------------|-------|-------|
| **OPNsense** | No | Yes | Current platform, good but manual install |
| **pfSense** | No | Yes | Same FreeBSD base as OPNsense, same limitations |
| **NethSecurity** | Unlikely | Yes | OpenWRT-based, similar PXE challenges |
| **Fedora + Cockpit** | Yes (PXE) | Partial | Not purpose-built for routing |
| **VyOS** | Yes (cloud-init) | No | Selected - best automation support |

### Key Differentiator

VyOS is the only purpose-built router OS evaluated that supports automated deployment from staged artifacts. This closes the air-gap install gap that exists with OPNsense.

---

## Licensing

VyOS uses a dual licensing model:

| Release | Source Code | Pre-built Images | Cost |
|---------|-------------|------------------|------|
| **Rolling** | Public | Free nightlies | Free |
| **LTS** | Subscription only | Subscription only | Paid |

For Deevnet, **rolling release** is used:
- Download pre-built nightly ISOs
- Stage to artifact server
- Deploy from local artifacts
- Acceptable stability for homelab use

---

## Services Provided

VyOS will provide the same services currently handled by OPNsense:

### DNS

- **Forwarding**: Queries forwarded to upstream DNS servers
- **Local resolution**: Static host entries from inventory

### DHCP

- **Static mappings**: MAC-to-IP reservations for known hosts
- **Dynamic pools**: Address ranges for unknown clients

### Firewall

- **Zone-based**: Interfaces assigned to security zones
- **Stateful**: Connection tracking with default-deny
- **NAT**: Masquerading for outbound traffic

### Routing

- **Inter-VLAN**: Routing between substrate segments
- **Static routes**: Defined routes for specific destinations
- **Default gateway**: Routes substrate traffic to upstream

---

## Deployment Model

### dvntm (Mobile Substrate)

VyOS runs as a **Proxmox VM**:
- Virtualized for portability
- Two virtual NICs: WAN + LAN
- cloud-init for initial configuration

### dvnt (Home Substrate)

Future consideration:
- VM on Proxmox, or
- Dedicated x86 hardware

---

## Automation Stack

### Image Provisioning

```
Artifact Server → VyOS ISO → Proxmox VM → cloud-init config
```

1. VyOS rolling ISO staged on artifact server
2. Proxmox creates VM from ISO
3. cloud-init provides initial configuration
4. Ansible applies day-2 configuration

### Configuration Management

VyOS is configured via the `vyos.vyos` Ansible collection:

| Component | Module |
|-----------|--------|
| Interfaces | `vyos_interfaces` |
| Firewall rules | `vyos_firewall_rules` |
| System settings | `vyos_system`, `vyos_hostname` |
| Static routes | `vyos_static_routes` |
| Configuration | `vyos_config` |

### Collection Dependency

```yaml
# collections/requirements.yml
collections:
  - name: vyos.vyos
    version: ">=6.0.0"
```

---

## Migration Status

| Phase | Status |
|-------|--------|
| Platform evaluation | Complete |
| Manual testing (Proxmox VM) | Pending |
| cloud-init automation | Pending |
| Ansible roles | Pending |
| Production cutover | Pending |

Current router remains OPNsense until VyOS evaluation is complete.

---

## Resources

- [VyOS Documentation](https://docs.vyos.io/)
- [VyOS Nightly Builds](https://vyos.net/get/nightly-builds/)
- [vyos.vyos Ansible Collection](https://galaxy.ansible.com/vyos/vyos)
- [VyOS cloud-init](https://docs.vyos.io/en/latest/automation/cloud-init.html)
- [VyOS Proxmox Deployment](https://docs.vyos.io/en/latest/installation/virtual/proxmox.html)
