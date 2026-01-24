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

## Transition PXE to Core Router

After Core Router is configured with DHCP/DNS, transition the bootstrap node to TFTP-only mode:

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make core-auth
```

This disables dnsmasq and masquerading on the bootstrap node. Core Router now handles DNS/DHCP; bootstrap node provides TFTP only.

### Verify the transition

```bash
# dnsmasq should be stopped
systemctl status dnsmasq

# TFTP should be running
systemctl status tftp.socket

# DNS should resolve via Core Router
dig artifacts.dvntm.deevnet.net
```

---

## VLANs

Configure VLAN tagging on switch and define segments.

*TBD - Switch configuration details*

---

## Wireless

Set up SSIDs, guest networks, and VLAN assignments on Omada AP.

*TBD - AP configuration details*

