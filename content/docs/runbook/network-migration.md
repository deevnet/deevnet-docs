---
title: "Network Migration"
weight: 8
---

# Network Migration: Flat to Segmented VLANs

Migrate the dvntm substrate from a flat 192.168.10.0/24 network to segmented 10.20.x.0/24 VLANs.

This is a semi-automated migration: run a playbook, verify, proceed. Each step is a discrete `make` target. Do not skip steps or run them out of order.

---

## Prerequisites

### Vault

All secrets (OPNsense API credentials, switch credentials) are encrypted with Ansible Vault in the inventory:

- `group_vars/routers/vault.yml` — OPNsense API key and secret
- `group_vars/switches/vault.yml` — switch user, password, and enable password

Decrypt the vault files before starting the migration and re-encrypt when done:

```bash
cd ansible-inventory-deevnet
make unvault    # decrypt — run once before starting
# ... run migration steps ...
make vault      # re-encrypt when migration is complete
```

### Pre-Migration Checklist

- [ ] SSH to switch verified: `ssh $SWITCH_USER@access-sw01`
- [ ] Vault decrypted: `cd ansible-inventory-deevnet && make unvault`
- [ ] OPNsense API verified: confirm credentials in `../ansible-inventory-deevnet/dvntm-new/group_vars/routers/vault.yml`, then `curl -u "KEY:SECRET" https://core-rt02/api/core/firmware/status`
- [ ] Backup current switch config: `show running-config` and save output
- [ ] Backup current OPNsense config: System -> Configuration -> Backups -> Download
- [ ] Console/OOB access available (in case of connectivity loss during step 4)
- [ ] Collection dependencies installed: `cd ansible-collection-deevnet.net && make deps`

### Builder Connectivity

The builder (`provisioner-ph01`) hosts the Omada SDN controller, artifact server, and PXE/TFTP services. It must remain reachable throughout the migration. Its WiFi interface provides WAN/upstream — do **not** rely on it for management connectivity, as AP reconfiguration during the migration may disrupt wireless.

- The builder **must** be connected via ethernet (`eth0`) to switch port `gi1/0/4`
- The Omada controller on the builder manages `access-sw01` and `ap01` — if the builder loses switch connectivity, Omada management is lost
- The builder's port is assigned to VLAN 99 (management) in the target inventory, with IP `10.20.99.95`

**Pre-flight checks:**
- [ ] Builder ethernet cable confirmed on `gi1/0/4` (not WiFi for substrate connectivity)
- [ ] Omada UI accessible and showing `access-sw01` and `ap01` as connected
- [ ] Builder currently reachable at `192.168.10.95`

---

## Step 1: Physical Port Mapping

Verify that every device is physically connected to its intended switch port before making any logical changes. The port-to-VLAN assignments in `host_vars/access-sw01.yml` assume specific physical cabling — if a device is on the wrong port, it will land in the wrong VLAN after migration.

**Run:**
1. Open `host_vars/access-sw01.yml` and review the `switch_ports` mapping
2. Physically trace or label each cable at the switch to confirm it matches the intended port assignment
3. Relocate any mis-cabled devices to their correct ports

**Verify:**
```
ssh $SWITCH_USER@access-sw01
show mac address-table
```
Confirm each device's MAC address appears on the expected port.

**Rollback:**
No logical changes — this step is purely physical. Move cables back if needed.

---

## Step 2: OPNsense VLAN Interfaces

Create VLAN sub-interfaces on OPNsense. This step is non-disruptive — it only adds new interfaces without affecting existing traffic.

**Run:**
```bash
cd ansible-collection-deevnet.net
make migration-opnsense-vlans
```

**Verify:**
1. OPNsense GUI -> Interfaces -> Devices -> VLAN
2. Confirm 11 VLANs created on the correct parent interface
3. Each VLAN shows the correct tag (10, 20, 25, 30, 31, 35, 40, 50, 51, 52, 99)

**Rollback:**
Delete VLAN interfaces via OPNsense GUI -> Interfaces -> Devices -> VLAN -> delete each entry.

---

## Step 3: Switch VLAN Database

Create VLANs in the switch VLAN database. Non-disruptive — VLANs are created but no ports are assigned yet.

**Run:**
```bash
make migration-switch-vlans
```

**Verify:**
```
ssh $SWITCH_USER@access-sw01
show vlan brief
```
Confirm all VLANs (10, 20, 25, 30, 31, 35, 40, 50, 51, 52, 99) appear with correct names.

**Rollback:**
```
configure terminal
no vlan 10
no vlan 20
no vlan 25
no vlan 30
no vlan 31
no vlan 35
no vlan 40
no vlan 50
no vlan 51
no vlan 52
no vlan 99
end
copy running-config startup-config
```

---

## Step 4: Trunk Uplink

Configure the switch uplink port as a trunk carrying all VLANs with blackhole (VLAN 999) as native.

**WARNING:** If the native VLAN is misconfigured, you will lose switch access over the network. Ensure console/OOB access is available before proceeding.

**Run:**
```bash
make migration-switch-trunk
```

**Verify:**
```
show interface switchport gigabitEthernet 1/0/1
```
- Uplink port shows mode: trunk
- Native VLAN: 999
- Allowed VLANs include all configured VLANs

Also verify you can still reach the switch at its current management IP (192.168.10.10). The switch management IP moves to 10.20.99.10 in Step 8.

**Rollback:**
Via console if network access is lost:
```
configure terminal
interface gigabitEthernet 1/0/1
  switchport mode access
  no switchport trunk allowed vlan
  no switchport trunk native vlan
end
copy running-config startup-config
```

---

## Step 5: Test Ports (Builder First)

Migrate the builder's port first to validate VLAN 99 end-to-end. This puts the builder on the management segment early, giving it routed access to all VLANs for the rest of the migration. Then test a second port on a different VLAN.

**5a — Builder port (`gi1/0/4`) to VLAN 99:**

```bash
ANSIBLE_COLLECTIONS_PATH="./.ansible/collections:~/.ansible/collections" \
  ansible-playbook playbooks/migration/04-switch-test-port.yml \
  -e test_port_interface="gigabitEthernet 1/0/4" \
  -e test_port_vlan_id=99
```

**Verify (5a):**
1. Builder's IP changes from `192.168.10.95` to `10.20.99.95` — you will lose the current SSH session
2. Reconnect: `ssh a_autoprov@10.20.99.95`
3. `ping 10.20.99.1` (management gateway) — should succeed
4. `ping 8.8.8.8` — internet access works
5. Omada UI still shows `access-sw01` and `ap01` as connected

**5b — Second test port (`gi1/0/24`) on VLAN 10:**

```bash
# Default: port gi1/0/24 -> VLAN 10 (trusted)
make migration-switch-test-port
```

**Verify (5b):**
1. Connect a device to `gi1/0/24`
2. Device receives DHCP lease from 10.20.10.x subnet
3. `ping 10.20.10.1` (VLAN gateway) — should succeed
4. `ping 8.8.8.8` — internet access works
5. `ping 10.20.99.10` — inter-VLAN routing to switch management works (if firewall allows)

**Rollback:**
```
configure terminal
interface gigabitEthernet 1/0/4
  switchport access vlan 1
interface gigabitEthernet 1/0/24
  switchport access vlan 1
end
copy running-config startup-config
```

---

## Step 6: DHCP for New Subnets

Configure Kea DHCP subnets and static reservations for the new VLAN subnets.

Ensure Kea DHCP subnets are created in OPNsense first (Services -> Kea DHCP -> Subnets) and `dhcp_subnet_uuid` is updated in `group_vars/routers/vars.yml` for each subnet.

**Run:**
```bash
make migration-opnsense-dhcp
```

**Verify:**
1. OPNsense GUI -> Services -> Kea DHCP -> Subnets — new subnets visible
2. OPNsense GUI -> Services -> Kea DHCP -> Reservations — static mappings present
3. A device on the test port (Step 5) gets a correct DHCP lease

**Rollback:**
Delete DHCP subnets and reservations via OPNsense GUI -> Services -> Kea DHCP.

---

## Step 7: OPNsense Interface IPs

Assign gateway IP addresses to each VLAN interface and enable them. After this step, the router can route traffic between VLAN subnets (subject to firewall policy).

**Prerequisites:**
- Step 2 complete (VLAN sub-interfaces exist on OPNsense)
- VLAN devices assigned to interface slots in OPNsense (Interfaces -> Assignments)

**Run:**
```bash
cd ansible-collection-deevnet.net
make migration-opnsense-interfaces
```

**Verify:**
1. OPNsense GUI -> Interfaces -> each VLAN interface shows its gateway IP with /24 mask
2. Each interface shows status: enabled
3. From test port (Step 5): `ping 10.20.10.1` (trusted gateway) — should succeed

**Rollback:**
Remove IP assignments via OPNsense GUI -> Interfaces -> select each VLAN interface -> clear IP and disable.

---

## Step 8: Inter-VLAN Firewall Rules

Apply zone-based firewall policy (default-deny with explicit inter-zone allows). Rules are defined in `group_vars/all/firewall.yml` and managed via the OPNsense filter API.

**Prerequisites:**
- Step 7 complete (VLAN interfaces have IPs and are enabled)

**Run:**
```bash
make migration-opnsense-firewall
```

**Verify:**
1. OPNsense GUI -> Firewall -> Automation -> Filter — all rules prefixed with `ansible:` are present
2. From management VLAN: `ping 10.20.10.1` (trusted gateway) — should succeed
3. From guest VLAN: `ping 10.20.10.1` (trusted gateway) — should be denied
4. From any VLAN: `ping 8.8.8.8` (internet) — should succeed for zones in `firewall_internet_zones`

**Rollback:**
Delete managed rules via OPNsense GUI -> Firewall -> Automation -> Filter -> delete rules prefixed with `ansible:`, then apply.

---

## Step 9: Migrate Remaining Access Ports

Move all remaining switch ports to their assigned VLANs as defined in `host_vars/access-sw01.yml`.

{{< hint info >}}
**DNS:** New 10.20.x.x addresses will not resolve via DNS until post-migration (Step 10 / Post-Migration). This is expected — Ansible uses inventory IPs directly. Use IP addresses for any manual verification during this step.
{{< /hint >}}

{{< hint warning >}}
**Wireless clients:** AP SSID-to-VLAN mappings are not reconfigured in this migration. When the AP's port moves to its target VLAN, wireless clients may lose connectivity. AP SSID reconfiguration is a separate post-migration task.
{{< /hint >}}

**Run:**
```bash
make migration-switch-access-ports
```

**Verify:**
1. `show vlan brief` — each port in correct VLAN
2. Each device gets correct VLAN IP via DHCP or static
3. Spot-check: SSH to a management host, ping across VLANs (where firewall permits)

**Rollback:**
Move ports back to VLAN 1 (default):
```
configure terminal
interface range gigabitEthernet 1/0/2 - 24
  switchport access vlan 1
end
copy running-config startup-config
```

---

## Step 10: Management Cutover (Manual)

After all ports are migrated and verified:

1. **Switch management VLAN** — move the switch management interface to VLAN 99:
   ```
   configure terminal
   interface vlan 99
     ip address 10.20.99.10 255.255.255.0
   no interface vlan 1
   end
   copy running-config startup-config
   ```

2. **Promote inventory** — `dvntm-new` becomes the active `dvntm`:
   ```bash
   cd ansible-inventory-deevnet
   mv dvntm dvntm-old
   mv dvntm-new dvntm
   ```
   No `ansible.cfg` changes needed — it already points to `dvntm`.

3. **Verify Ansible connectivity** from each collection that uses the inventory:
   ```bash
   cd ansible-collection-deevnet.net
   ansible switches -m ansible.netcommon.cli_command -a "command='show image-info'"
   ansible dns_servers -m ping
   ```

4. **Clean up** — once stable, remove the old inventory:
   ```bash
   rm -rf ansible-inventory-deevnet/dvntm-old
   ```

---

## Post-Migration

After all steps complete and connectivity is verified:

1. **Re-encrypt vault files:**
   ```bash
   cd ansible-inventory-deevnet
   make vault
   ```

2. **Run full DNS/DHCP roles** against `dvntm-new` inventory:
   ```bash
   make dns
   make dhcp
   ```

3. **Remove old network config:**
   - Delete 192.168.10.0/24 subnet from OPNsense
   - Remove any old static routes referencing 192.168.10.x

4. **Ongoing switch management** — use the `switch` target for day-2 operations:
   ```bash
   make switch
   ```

5. **Update documentation** — verify network-reference.md reflects the new state

---

## Troubleshooting

### Lost switch access after trunk configuration
- Connect via console cable
- Check `show interface switchport gigabitEthernet 1/0/1` for native VLAN mismatch
- Revert to access mode on uplink if needed

### Device not getting DHCP lease
- Verify port VLAN assignment: `show vlan brief`
- Verify DHCP subnet exists in OPNsense for that VLAN
- Check OPNsense firewall rules allow DHCP on VLAN interface
- Check `show mac address-table` to confirm device is on expected port

### Builder lost connectivity during migration
- Verify ethernet cable is connected to `gi1/0/4` — do not rely on WiFi for substrate access
- Check port VLAN assignment: `show interface switchport gigabitEthernet 1/0/4`
- Verify VLAN 99 interface is enabled with IP `10.20.99.1` in OPNsense
- Check Omada controller status: if the builder is unreachable, Omada cannot manage the switch or AP
- Last resort: revert the builder port to VLAN 1 via console:
  ```
  configure terminal
  interface gigabitEthernet 1/0/4
    switchport access vlan 1
  end
  copy running-config startup-config
  ```

### Inter-VLAN routing not working
- Verify VLAN interfaces have IP addresses assigned in OPNsense
- Check OPNsense firewall rules for inter-VLAN traffic
- Verify routing table: OPNsense GUI -> System -> Routes
