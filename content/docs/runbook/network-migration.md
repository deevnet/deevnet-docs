---
title: "Network Migration"
weight: 8
---

# Network Migration: Flat to Segmented VLANs

Migrate the dvntm substrate from a flat 192.168.10.0/24 network to segmented 10.20.x.0/24 VLANs.

This is a semi-automated migration: run a playbook, verify, proceed. Each phase is a discrete `make` target. Do not skip phases or run them out of order.

---

## Prerequisites

### Vault Password

All secrets (OPNsense API credentials, switch credentials) are encrypted with Ansible Vault in the inventory:

- `group_vars/routers/vault.yml` — OPNsense API key and secret
- `group_vars/switches/vault.yml` — switch user, password, and enable password

Every `make` target that touches routers or switches will prompt for the vault password automatically (`--ask-vault-pass`). No environment variable exports are needed.

### Pre-Migration Checklist

- [ ] SSH to switch verified: `ssh $SWITCH_USER@access-sw01`
- [ ] OPNsense API verified: `ansible-vault view ../ansible-inventory-deevnet/dvntm-new/group_vars/routers/vault.yml` to confirm credentials, then `curl -u "KEY:SECRET" https://core-rt02/api/core/firmware/status`
- [ ] Backup current switch config: `show running-config` and save output
- [ ] Backup current OPNsense config: System -> Configuration -> Backups -> Download
- [ ] Console/OOB access available (in case of connectivity loss during phase 3)
- [ ] Port mapping confirmed: verify `switch_ports` in `host_vars/access-sw01.yml` matches physical cabling
- [ ] Collection dependencies installed: `cd ansible-collection-deevnet.net && make deps`

---

## Phase 1: OPNsense VLAN Interfaces

Create VLAN sub-interfaces on OPNsense. This phase is non-disruptive — it only adds new interfaces without affecting existing traffic.

**Run:**
```bash
cd ansible-collection-deevnet.net
make migration-opnsense-vlans
```

**Verify:**
1. OPNsense GUI -> Interfaces -> Other Types -> VLAN
2. Confirm 11 VLANs created on the correct parent interface
3. Each VLAN shows the correct tag (10, 20, 25, 30, 31, 35, 40, 50, 51, 52, 99)

**Rollback:**
Delete VLAN interfaces via OPNsense GUI -> Interfaces -> Other Types -> VLAN -> delete each entry.

---

## Phase 2: Switch VLAN Database

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

## Phase 3: Trunk Uplink

Configure the switch uplink port as a trunk carrying all VLANs with management (VLAN 99) as native.

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
- Native VLAN: 99
- Allowed VLANs include all configured VLANs

Also verify you can still reach the switch at its current management IP (192.168.10.10). The switch management IP moves to 10.20.99.10 in Phase 7.

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

## Phase 4: Test One Port

Move a single access port to a test VLAN to validate end-to-end connectivity before migrating all ports.

**Run:**
```bash
# Default: port gi1/0/24 -> VLAN 10 (trusted)
make migration-switch-test-port

# Or specify a different port/VLAN:
ANSIBLE_COLLECTIONS_PATH="./.ansible/collections:~/.ansible/collections" \
  ansible-playbook playbooks/migration/04-switch-test-port.yml --ask-vault-pass \
  -e test_port_interface="gigabitEthernet 1/0/24" \
  -e test_port_vlan_id=10
```

**Verify:**
1. Connect a device to the test port
2. Device receives DHCP lease from 10.20.10.x subnet
3. `ping 10.20.10.1` (VLAN gateway) — should succeed
4. `ping 8.8.8.8` — internet access works
5. `ping 10.20.99.10` — inter-VLAN routing to switch management works (if firewall allows)

**Rollback:**
```
configure terminal
interface gigabitEthernet 1/0/24
  switchport access vlan 1
end
copy running-config startup-config
```

---

## Phase 5: DHCP for New Subnets

Configure Kea DHCP subnets and static reservations for the new VLAN subnets.

Ensure Kea DHCP subnets are created in OPNsense first (Services -> Kea DHCP -> Subnets) and `dhcp_subnet_uuid` is updated in `group_vars/routers/vars.yml` for each subnet.

**Run:**
```bash
make migration-opnsense-dhcp
```

**Verify:**
1. OPNsense GUI -> Services -> Kea DHCP -> Subnets — new subnets visible
2. OPNsense GUI -> Services -> Kea DHCP -> Reservations — static mappings present
3. A device on the test port (Phase 4) gets a correct DHCP lease

**Rollback:**
Delete DHCP subnets and reservations via OPNsense GUI -> Services -> Kea DHCP.

---

## Phase 6: Migrate Remaining Access Ports

Move all remaining switch ports to their assigned VLANs as defined in `host_vars/access-sw01.yml`.

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

## Phase 7: Management Cutover (Manual)

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

After all phases complete and connectivity is verified:

1. **Run full DNS/DHCP roles** against `dvntm-new` inventory:
   ```bash
   make dns
   make dhcp
   ```

2. **Remove old network config:**
   - Delete 192.168.10.0/24 subnet from OPNsense
   - Remove any old static routes referencing 192.168.10.x

3. **Ongoing switch management** — use the `switch` target for day-2 operations:
   ```bash
   make switch
   ```

4. **Update documentation** — verify network-reference.md reflects the new state

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

### Inter-VLAN routing not working
- Verify VLAN interfaces have IP addresses assigned in OPNsense
- Check OPNsense firewall rules for inter-VLAN traffic
- Verify routing table: OPNsense GUI -> System -> Routes
