---
title: "Build Network"
weight: 10
---

# Build Network

Configure network infrastructure: Core Router, VLANs, and wireless access points.

**Collection:** `deevnet.net`

---

## Components

| Component | Role |
|-----------|------|
| Core Router | Firewall, DHCP, DNS, routing |
| Switch/VLANs | Network segmentation |
| Wireless AP | SSIDs, guest networks |

---

## Prerequisites

- Inventory seeded with network device definitions
- Physical network cabling in place

---

## Core Router

### Current Status

No automated install exists. Manual USB install required.

### Procedure

1. Create bootable USB with OPNsense/pfSense image
2. Boot from USB and complete installer
3. Apply configuration via `deevnet.net` Ansible collection:
   ```bash
   cd ~/dvnt/ansible-collection-deevnet.net
   ansible-playbook playbooks/site.yml --limit routers
   ```

### Future Options

- USB installer with embedded config.xml
- Alternative whitebox solution

---

## VLANs

Configure VLAN tagging on switch and define segments.

*TBD - Switch configuration details*

---

## Wireless

Set up SSIDs, guest networks, and VLAN assignments on Omada AP.

*TBD - AP configuration details*

---

## Verification

```bash
# Verify Core Router services
ping gateway.dvntm.deevnet.net
dig +short @192.168.10.1 hv01.dvntm.deevnet.net

# Verify VLAN connectivity
# Verify wireless SSIDs broadcast
```
