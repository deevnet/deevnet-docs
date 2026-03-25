---
title: "Prerequisites & Preflight"
weight: 1
---

# Prerequisites & Preflight

## Vault

All secrets are encrypted with Ansible Vault in the inventory. Decrypt before starting the migration and re-encrypt when done:

```bash
cd ansible-inventory-deevnet
make unvault    # decrypt — run once before starting
# ... run migration steps ...
make vault      # re-encrypt when migration is complete
```

## Migration Artifact Capture

Migration logs (preflight, each migration step, postcheck) are automatically captured in `ansible-collection-deevnet.net/migration-logs/` with timestamps. Each `make` target produces a log file named `YYYYMMDD-HHMMSS-<target>.log`. No additional setup is required.

## Pre-Migration Checklist

- [ ] Vault decrypted: `cd ansible-inventory-deevnet && make unvault`
- [ ] Backup current switch config: `show running-config` and save output
- [ ] Backup current OPNsense config: System -> Configuration -> Backups -> Download
- [ ] Console/OOB access available (in case of connectivity loss during step 4)
- [ ] Collection dependencies installed: `cd ansible-collection-deevnet.net && make deps`

## Builder Connectivity

The builder (`provisioner-ph01`) hosts the Omada SDN controller, artifact server, and PXE/TFTP services. It must remain reachable throughout the migration. The builder's `eth1` (transit interface, DHCP) provides upstream/WAN connectivity — WiFi is disabled (`ip: null`). Do **not** rely on wireless for management connectivity.

- The builder **must** be connected via ethernet (`eth0`) to switch port `gi1/0/16`
- `eth1` (transit) must be connected to an upstream network and receiving a DHCP address — this is the builder's only path to the internet
- The Omada controller on the builder manages device adoption and monitoring (switch is managed via SSH/CLI during migration) — Omada adoption of devices happens post-migration in [Step 12](../port-migration/#step-12-omada-device-adoption)
- The builder's port is assigned to VLAN 99 (management) in the target inventory, with IP `10.20.99.95`

**Pre-flight checks:** Automated by `make preflight` (Step 1). The preflight playbook verifies builder service status, eth1 DHCP address, and internet connectivity.

## Physical Port Mapping

Verify that every device is physically connected to its intended switch port before making any logical changes. The port-to-VLAN assignments in `host_vars/access-sw01.yml` assume specific physical cabling — if a device is on the wrong port, it will land in the wrong VLAN after migration.

1. Open `host_vars/access-sw01.yml` and review the `switch_ports` mapping
2. Physically trace or label each cable at the switch to confirm it matches the intended port assignment
3. Relocate any mis-cabled devices to their correct ports

The MAC address table output in Step 1 (preflight) serves as verification that cabling is correct.

---

## Step 1: Preflight Check

Run the automated preflight playbook to verify connectivity and readiness before starting any migration steps. This validates:

- OPNsense API reachable (replaces manual `curl` check)
- Switch SSH connectivity (replaces manual SSH check) and MAC address table for port mapping verification
- AP reachable via ping
- Builder: Omada controller active, eth1 has DHCP address, internet connectivity

**Run:**
```bash
cd ansible-collection-deevnet.net
make preflight
```

**Verify:**
All checks show `[PASS]`. Internet connectivity from the builder shows `[WARN]` if unreachable — this is informational and not a hard failure.

Review the MAC address table output and confirm each device's MAC appears on its expected port (per the Physical Port Mapping prerequisite above).

**Rollback:**
Read-only — no changes made.
