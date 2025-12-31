---
title: "OPNsense Router"
weight: 2
---

# OPNsense Router

## Purpose

OPNsense is the **production router/firewall/gateway** for each Deevnet substrate. After initial provisioning, it takes over as the authoritative source for DNS, DHCP, and network services.

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│    Upstream     │◄────►│    OPNsense      │◄────►│  Substrate Hosts    │
│                 │      │  Router/Firewall │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

| Substrate | Upstream Connection |
|-----------|---------------------|
| **dvntm** | Travel router (portable WAN) |
| **dvnt** | ISP router (home internet) |

---

## Services Provided

### DNS

OPNsense provides DNS for the substrate:

- **Authoritative** for the substrate zone:
  - `dvntm.deevnet.net` (mobile substrate)
  - `dvnt.deevnet.net` (home substrate)
- **Forwarder** for all other queries (upstream DNS servers)

Host records are managed as config-as-code in inventory and pushed via Ansible.

### DHCP

| Mode | Description |
|------|-------------|
| **Dynamic pool** | Address range for unknown/temporary clients |
| **Static mappings** | MAC → IP reservations for known hosts |

Static mappings ensure deterministic identity per the [Correctness Standard](/docs/standards/correctness/#31-host-identity-is-declarative).

### Firewall

- **NAT**: Substrate hosts access upstream via masquerading
- **Inter-subnet rules**: Control traffic between network segments
- **Future**: Inter-VLAN isolation for tenant networks

### Gateway

OPNsense is the default gateway for all substrate hosts:
- Routes traffic to upstream (internet or travel router)
- Handles return traffic routing

### Wake-on-LAN

OPNsense provides WoL services for:
- **Startup sequences**: Power on hosts in order during substrate boot
- **Power management**: Remote wake capability for automation

---

## Authority Mode

Per the [Correctness Standard](/docs/standards/correctness/#52-authority-modes-are-explicit):

### Bootstrap-Authoritative → OPNsense-Authoritative

1. During initial provisioning, the bootstrap node provides DNS/DHCP
2. OPNsense is provisioned and configured via Ansible
3. Authority explicitly transitions to OPNsense
4. Bootstrap node's dnsmasq is disabled
5. OPNsense becomes the production DNS/DHCP server

**This transition is explicit, not automatic.**

---

## Configuration Management

OPNsense is configured via the `deevnet.net` Ansible collection:

| Component | Management |
|-----------|------------|
| **DNS records** | Pushed from inventory |
| **DHCP static mappings** | Pushed from inventory |
| **Firewall rules** | Defined in playbooks |
| **WoL targets** | Defined in inventory |

All configuration is **config-as-code** — no manual changes in the OPNsense UI for production settings.

---

## Future: VLAN Support

When tenant networking is implemented:

- **VLAN interfaces**: OPNsense will have interfaces for each tenant VLAN
- **Inter-VLAN routing**: Controlled routing between tenants (or isolation)
- **Per-tenant firewall rules**: Tenant-specific ingress/egress policies
- **DHCP per VLAN**: Each tenant VLAN gets its own DHCP scope

---

## Deployment

### dvntm (Mobile Substrate)

OPNsense runs as a **VM on Proxmox**:
- Virtualized firewall for portability
- Two virtual NICs: WAN (to travel router) + LAN (to substrate)

### dvnt (Home Substrate)

OPNsense may run as:
- VM on Proxmox, or
- Dedicated hardware appliance

---

## Relationship to Other Docs

| Document | Relationship |
|----------|--------------|
| [Bootstrap Node](/docs/architecture/bootstrap-node/) | Hands off DNS/DHCP authority to OPNsense |
| [Correctness: Authority Modes](/docs/standards/correctness/#52-authority-modes-are-explicit) | Defines explicit authority transition |
| [Naming Standard](/docs/standards/naming/) | OPNsense hosts the substrate DNS zone |
| [Roadmap: Tenant Networking](/docs/roadmap/#9--proxmox-tenant-networking) | VLAN routing through OPNsense |

---

## Summary

OPNsense is the production network authority for each substrate:

1. **DNS**: Authoritative for substrate zone, forwarder for everything else
2. **DHCP**: Static mappings for known hosts, pool for dynamic clients
3. **Firewall**: NAT, inter-subnet rules, future VLAN isolation
4. **Gateway**: Routes substrate traffic to upstream
5. **WoL**: Startup sequences and power management
6. **Config-as-code**: Managed via `deevnet.net` Ansible collection
