---
title: "Network Reference"
weight: 6
---

# Network Reference

Quick reference for VLAN assignments and network configuration in dvntm substrate.

---

## VLAN Assignments

| Segment | VLAN ID | Subnet | Gateway | DHCP |
|---------|---------|--------|---------|------|
| Trusted | 10 | 192.168.10.0/24 | 192.168.10.1 | 192.168.10.100-200 |
| Storage | 20 | 192.168.20.0/24 | 192.168.20.1 | Static only |
| IoT | 30 | 192.168.30.0/24 | 192.168.30.1 | 192.168.30.100-200 |
| Guest | 40 | 192.168.40.0/24 | 192.168.40.1 | 192.168.40.50-250 |
| Management | 99 | 192.168.99.0/24 | 192.168.99.1 | Static only |

---

## Segment Purpose Summary

| Segment | Trust Level | Purpose |
|---------|-------------|---------|
| Management | High | Infrastructure control plane (provisioners, hypervisor mgmt, switches, IPMI) |
| Trusted | High | User devices (workstations, laptops, personal devices) |
| Storage | High | Dedicated storage traffic (NAS, backup targets) |
| IoT | Low | Embedded/untrusted devices (Pis, sensors, smart home) |
| Guest | Untrusted | Transient visitor access (internet only) |

---

## Canonical Source

VLAN definitions are maintained in Ansible inventory:

```
ansible-inventory-deevnet/dvntm/group_vars/all/vlans.yml
```

For segment design rationale and trust hierarchy, see the architecture documentation.
