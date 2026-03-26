---
title: "Build Network"
weight: 10
---

# Build Network

Configure network infrastructure: Core Router, VLANs, firewall, DHCP, and wireless access points.

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

Before the automated build-network procedures begin, the following manual steps must be completed:

| Prerequisite | Method | Notes |
|--------------|--------|-------|
| Core Router | Fresh OPNsense install from USB | Manual installer; no PXE support |
| Access Switch | Factory reset to default state | Clears any prior VLAN/port config |
| Wireless AP | Factory reset to default state | Clears any prior SSID/network config |

Additionally:

- Inventory seeded with network device definitions
- Physical network cabling in place

---

## Core Router

### Current Status

No automated install exists. Manual USB install required.

### Procedure

1. Create bootable USB with OPNsense image
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

## Network Segmentation

After the Core Router is installed and reachable, build the segmented VLAN network. These procedures are documented in detail under [Network Segmentation](/docs/runbook/network-migration/).

The sequence for a greenfield build:

### 1. VLAN Foundation

Create VLAN sub-interfaces on OPNsense and VLANs in the switch database. Non-disruptive.

See [VLAN Foundation](/docs/runbook/network-migration/vlan-foundation/) for detailed steps.

```bash
cd ~/dvnt/ansible-collection-deevnet.net
make migration-opnsense-vlans    # OPNsense VLAN interfaces
make migration-switch-vlans      # Switch VLAN database
make migration-switch-trunk      # Trunk uplink with tagged VLANs
```

### 2. Builder Cutover

Move the builder from the flat/default network to the management VLAN. Highest-risk phase.

See [Builder Cutover](/docs/runbook/network-migration/builder-cutover/) for detailed steps and rollback procedures.

### 3. Services and Routing

Configure DHCP, firewall rules, and inter-VLAN routing.

See [Services & Routing](/docs/runbook/network-migration/services-and-routing/) for detailed steps.

```bash
make migration-opnsense-dhcp       # Kea DHCP subnets and reservations
make migration-opnsense-firewall   # Zone-based firewall policy
```

### 4. Port Assignment and Wireless

Move switch ports to their assigned VLANs and configure AP SSIDs.

See [Port Migration & Wireless](/docs/runbook/network-migration/port-migration/) for detailed steps.

### 5. DNS, DHCP, and WoL Finalization

Apply DNS host overrides, finalize DHCP configuration, and register Wake-on-LAN entries:

```bash
ansible-playbook playbooks/dns.yml --ask-vault-pass
ansible-playbook playbooks/dhcp.yml --ask-vault-pass
ansible-playbook playbooks/wol.yml --ask-vault-pass
```

The WoL playbook registers all hosts with `wol: true` in their inventory interface definitions into the OPNsense WoL dashboard. Requires the `os-wol` plugin to be installed on OPNsense.

---

## Transition PXE to Core Router

After the network is segmented and Core Router is handling DNS/DHCP, transition the bootstrap node to TFTP-only mode:

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make core-auth
```

This:
- Discovers the WAN interface from inventory (`bootstrap_wan_interface_key`)
- Disables masquerading and removes the WAN interface from the public firewall zone
- Disables IP forwarding
- Stops and disables dnsmasq
- Installs standalone tftpd for PXE boot file serving
- Swaps the management interface IP from the gateway address back to the reserved address
- Restores the default gateway to the core router

The IP swap is the last step — it drops the SSH connection. All configuration completes first while connectivity is stable. Reconnect at the reserved IP to verify.

Core Router now handles DNS/DHCP; bootstrap node provides TFTP only.

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

## Validation

Run the post-network verification checks:

See [Post-Migration](/docs/runbook/network-migration/post-migration/) for the full validation procedure, or proceed to [Verify Site](../build-verification/) after the management plane is built.
