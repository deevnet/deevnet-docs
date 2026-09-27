---
title: "Build Network"
weight: 10
aliases:
  - /docs/runbook/building-recovery/build-network/
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
3. Apply configuration from the `deevnet.net` collection (see [Applying Configuration](#applying-configuration)):
   ```bash
   cd ansible-collection-deevnet.net
   make opnsense
   ```

### Future Options

- USB installer with embedded config.xml
- Alternative whitebox solution

---

## Applying Configuration

Every managed network device is configured from the `deevnet.net` collection. Run the targets from the collection root:

| Device | Target | Playbook | How it reaches the device |
|--------|--------|----------|---------------------------|
| Core Router | `make opnsense` | `playbooks/opnsense.yml` | OPNsense REST API |
| Access Switch | `make switch` | `playbooks/switch-vlans.yml` | SSH CLI (`switch_vlans`), standalone only |
| Wireless AP | `make wireless` | `playbooks/omada-wireless.yml` | Omada controller Open API |
| Edge Router | — | — | Not managed by automation |

### Core Router

`playbooks/opnsense.yml` runs one role per service, in dependency order: VLAN interfaces, firewall rules and aliases, DNS (Unbound), DHCP (Kea), then gateways and routes.

- **Interface IPs have no API** (as of OPNsense 25.7). The VLAN role pauses while you set them in the GUI; continue once they are saved.
- **Firewall writes are opt-in.** The firewall role reports drift and only writes with `-e firewall_apply=true`.

### Access Switch

`make switch` applies VLANs, trunks and access ports over the CLI to a **standalone** switch. Once a switch is adopted into the Omada controller the role refuses to run without `-e switch_vlans_break_glass=true`. Adoption is [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/), on hold.

### Wireless

`make wireless` applies the LAN networks, PPSK profiles, SSIDs and the AP's name and address from inventory.

- By default it **plans without writing**.
- `APPLY=1` writes.
- `ADOPT=1` writes and also adopts a pending AP.

Change wireless configuration only this way, never in the controller UI. Tenant Wi-Fi keys are the exception: the Deevnet API issues them per tenant.

**The controller's event log records device events, not client associations.** It tells you that an AP connected or dropped, but not whether a client briefly lost its association. If that matters for a change, watch a client directly while `make wireless` runs.

---

## Network Segmentation

After the Core Router is installed and reachable, build the segmented VLAN network. The detailed procedure is the one the mobile site was migrated with, recorded in the [CHG-0001: Flat Network → VLANs](/docs/changes/2026/0001-flat-network-to-vlans/) change record. A greenfield build follows the same phases; that record's [Outcome](/docs/changes/2026/0001-flat-network-to-vlans/#outcome) lists where execution departed from the plan.

The sequence for a greenfield build:

### 1. VLAN Foundation

Create VLAN sub-interfaces on OPNsense and VLANs in the switch database. Non-disruptive.

See [VLAN Foundation](/docs/changes/2026/0001-flat-network-to-vlans/vlan-foundation/) for detailed steps.

```bash
cd ansible-collection-deevnet.net
make migration-opnsense-vlans    # OPNsense VLAN interfaces
make migration-switch-vlans      # Switch VLAN database
make migration-switch-trunk      # Trunk uplink with tagged VLANs
```

### 2. Builder Cutover

Move the builder from the flat/default network to the management VLAN. Highest-risk phase.

See [Builder Cutover](/docs/changes/2026/0001-flat-network-to-vlans/builder-cutover/) for detailed steps, and [Undo](/docs/changes/2026/0001-flat-network-to-vlans/undo/#undo-step-5) for backing it out.

### 3. Services and Routing

Configure DHCP, firewall rules, and inter-VLAN routing.

See [Services & Routing](/docs/changes/2026/0001-flat-network-to-vlans/services-and-routing/) for detailed steps.

```bash
make migration-opnsense-dhcp       # Kea DHCP subnets and reservations
make migration-opnsense-firewall   # Zone-based firewall policy
```

### 4. Port Assignment and Wireless

Move switch ports to their assigned VLANs and configure AP SSIDs.

See [Port Migration & Wireless](/docs/changes/2026/0001-flat-network-to-vlans/port-migration/) for detailed steps.

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
cd ansible-collection-deevnet.builder
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
dig artifacts.mobile.deevnet.net
```

---

## Validation

Run the post-network verification checks:

See [Post-Migration](/docs/changes/2026/0001-flat-network-to-vlans/post-migration/) for the full validation procedure, or proceed to [Verify Site](/docs/runbook/substrate/building-recovery/build-verification/) after the management plane is built.
