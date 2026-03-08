---
title: "Network Reference"
weight: 6
---

# Network Reference

Quick reference for VLAN assignments and network configuration across Deevnet substrates.

---

## dvntm VLAN Assignments

| Segment | VLAN ID | Subnet | Gateway | DHCP |
|---------|---------|--------|---------|------|
| Trusted | 10 | 10.20.10.0/24 | 10.20.10.1 | .100-.200 |
| Storage | 20 | 10.20.20.0/24 | 10.20.20.1 | Static only |
| Platform | 25 | 10.20.25.0/24 | 10.20.25.1 | Static only |
| IoT | 30 | 10.20.30.0/24 | 10.20.30.1 | .100-.200 |
| IoT Vendor | 31 | 10.20.31.0/24 | 10.20.31.1 | .100-.200 |
| IoT Backend | 35 | 10.20.35.0/24 | 10.20.35.1 | Static only |
| Guest | 40 | 10.20.40.0/24 | 10.20.40.1 | .50-.250 |
| Tenant 1 | 50 | 10.20.50.0/24 | 10.20.50.1 | Per-tenant |
| Tenant 2 | 51 | 10.20.51.0/24 | 10.20.51.1 | Per-tenant |
| Tenant 3 | 52 | 10.20.52.0/24 | 10.20.52.1 | Per-tenant |
| Management | 99 | 10.20.99.0/24 | 10.20.99.1 | Static only |

---

## dvnt VLAN Assignments

| Segment | VLAN ID | Subnet | Gateway | DHCP |
|---------|---------|--------|---------|------|
| Trusted | 10 | 10.10.10.0/24 | 10.10.10.1 | .100-.200 |
| Storage | 20 | 10.10.20.0/24 | 10.10.20.1 | Static only |
| Platform | 25 | 10.10.25.0/24 | 10.10.25.1 | Static only |
| IoT | 30 | 10.10.30.0/24 | 10.10.30.1 | .100-.200 |
| IoT Vendor | 31 | 10.10.31.0/24 | 10.10.31.1 | .100-.200 |
| IoT Backend | 35 | 10.10.35.0/24 | 10.10.35.1 | Static only |
| Guest | 40 | 10.10.40.0/24 | 10.10.40.1 | .50-.250 |
| Tenant 1 | 50 | 10.10.50.0/24 | 10.10.50.1 | Per-tenant |
| Tenant 2 | 51 | 10.10.51.0/24 | 10.10.51.1 | Per-tenant |
| Tenant 3 | 52 | 10.10.52.0/24 | 10.10.52.1 | Per-tenant |
| Management | 99 | 10.10.99.0/24 | 10.10.99.1 | Static only |

---

## Segment Purpose Summary

| Segment | Trust Level | Purpose |
|---------|-------------|---------|
| Management | High | Infrastructure management plane (provisioners, hypervisor mgmt, switches, IPMI) |
| Trusted | High | User devices (workstations, laptops, personal devices) |
| Storage | High | Dedicated storage traffic (NAS, backup targets) |
| Platform | High | Shared infrastructure services (DNS, NTP, artifact mirrors, reverse proxy) |
| Tenant | Medium | Per-tenant workload isolation |
| IoT Backend | Medium | IoT application backends (MQTT, Home Assistant, data pipelines) |
| IoT Vendor | Very Low | Vendor-managed IoT containment zone (cloud-dependent, unauditable) |
| IoT | Medium | Custom-developed embedded devices with controlled firmware (Pis, sensors) |
| Guest | Untrusted | Transient visitor access (internet only) |

---

## Canonical Source

VLAN definitions are maintained in Ansible inventory:

```
ansible-inventory-deevnet/dvntm-new/group_vars/all/vlans.yml
ansible-inventory-deevnet/dvnt/group_vars/all/vlans.yml
```

For segment design rationale and trust hierarchy, see the architecture documentation.
