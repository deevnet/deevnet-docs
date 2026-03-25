---
title: "Network Migration"
weight: 8
bookCollapseSection: true
---

# Network Migration: Flat to Segmented VLANs

Migrate the dvntm substrate from a flat 192.168.10.0/24 network to segmented 10.20.x.0/24 VLANs.

This is a semi-automated migration: run a playbook, verify, proceed. Each step is a discrete `make` target. Do not skip steps or run them out of order.

{{< hint info >}}
**Migration completed 2026-03-25.** This runbook is retained for the full site rebuild event and as operational reference.
{{< /hint >}}

---

## Migration Flow

{{< mermaid >}}
flowchart TD
    A["<b>Prerequisites & Preflight</b><br/>Vault, backups, connectivity checks"]
    B["<b>VLAN Foundation</b><br/>OPNsense VLANs, switch database, trunk uplink"]
    C["<b>Builder Cutover</b><br/>OPNsense interfaces, switch dual-mgmt,<br/>builder IP & port move"]:::critical
    D["<b>Services & Routing</b><br/>DHCP, firewall rules, trunk PVID"]
    E["<b>Port Migration & Wireless</b><br/>Access ports, management cutover,<br/>Omada adoption, SSIDs"]
    F["<b>Post-Migration</b><br/>Validation, DNS refresh, cleanup"]

    A --> B --> C --> D --> E --> F

    classDef default fill:#2d333b,stroke:#539bf5,color:#adbac7
    classDef critical fill:#3d1f00,stroke:#d29922,color:#e6c068
{{< /mermaid >}}

---

## Phases

### [Prerequisites & Preflight](prerequisites/)
Decrypt vault, verify backups, confirm physical port mapping, and run automated preflight checks (OPNsense API, switch SSH, AP ping, builder services).

### [VLAN Foundation](vlan-foundation/)
Create VLAN sub-interfaces on OPNsense, create VLANs in the switch database, and configure the trunk uplink with tagged VLANs. All non-disruptive — no traffic is affected.

### [Builder Cutover](builder-cutover/)
The highest-risk phase. Assign OPNsense VLAN interfaces (manual GUI step), add temporary firewall rules, dual-home the switch on VLAN 99, change the builder's static IP, and move its port to the management VLAN. After this, the builder operates from the new network.

### [Services & Routing](services-and-routing/)
Configure DHCP for new subnets, assign remaining OPNsense interface IPs, apply zone-based firewall policy, and set the trunk PVID to blackhole (999). After this, all VLANs are fully routed and served.

### [Port Migration & Wireless](port-migration/)
Move remaining switch ports to their assigned VLANs, perform the management cutover (remove VLAN 1, promote inventory), adopt devices in Omada, and configure AP SSIDs with VLAN tagging.

### [Post-Migration](post-migration/)
Run automated validation (`make postcheck`), refresh DNS/DHCP, re-encrypt vault, clean up old network config, reconfigure devices with old static IPs, and reference the SSH tunnel table for management access.

### [Troubleshooting](troubleshooting/)
Common issues encountered during migration (lost switch access, DHCP failures, AP adoption problems, inter-VLAN routing) and the automation improvement backlog.
