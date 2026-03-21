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

All secrets are encrypted with Ansible Vault in the inventory. Decrypt before starting the migration and re-encrypt when done:

```bash
cd ansible-inventory-deevnet
make unvault    # decrypt — run once before starting
# ... run migration steps ...
make vault      # re-encrypt when migration is complete
```

### Migration Artifact Capture

Migration logs (preflight, each migration step, postcheck) are automatically captured in `ansible-collection-deevnet.net/migration-logs/` with timestamps. Each `make` target produces a log file named `YYYYMMDD-HHMMSS-<target>.log`. No additional setup is required.

### Pre-Migration Checklist

- [ ] Vault decrypted: `cd ansible-inventory-deevnet && make unvault`
- [ ] Backup current switch config: `show running-config` and save output
- [ ] Backup current OPNsense config: System -> Configuration -> Backups -> Download
- [ ] Console/OOB access available (in case of connectivity loss during step 4)
- [ ] Collection dependencies installed: `cd ansible-collection-deevnet.net && make deps`

### Builder Connectivity

The builder (`provisioner-ph01`) hosts the Omada SDN controller, artifact server, and PXE/TFTP services. It must remain reachable throughout the migration. The builder's `eth1` (transit interface, DHCP) provides upstream/WAN connectivity — WiFi is disabled (`ip: null`). Do **not** rely on wireless for management connectivity.

- The builder **must** be connected via ethernet (`eth0`) to switch port `gi1/0/16`
- `eth1` (transit) must be connected to an upstream network and receiving a DHCP address — this is the builder's only path to the internet
- The Omada controller on the builder manages device adoption and monitoring (switch is managed via SSH/CLI during migration) — Omada adoption of devices happens post-migration in Step 12
- The builder's port is assigned to VLAN 99 (management) in the target inventory, with IP `10.20.99.95`

**Pre-flight checks:** Automated by `make preflight` (Step 1). The preflight playbook verifies builder service status, eth1 DHCP address, and internet connectivity.

### Physical Port Mapping

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

## Step 4: Trunk Uplink (Tagged VLANs)

Add all VLANs as tagged members on the uplink port. The PVID stays at 1 (the router's untagged traffic continues on VLAN 1). The PVID cutover to blackhole (999) happens in Step 9b — after OPNsense VLAN interfaces have IPs and the router is reachable via tagged VLANs.

**Run:**
```bash
make migration-switch-trunk
```

**Verify:**
```
show interface switchport gigabitEthernet 1/0/1
```
- All VLANs (10, 20, 25, 30, 31, 35, 40, 50, 51, 52, 99) are Tagged
- VLAN 999 is Untagged
- **PVID is still 1** (changes later in Step 9b)

Also verify you can still reach the router (`ping 192.168.10.1`) and the switch at `192.168.10.10`.

**Rollback:**
```
configure terminal
interface gigabitEthernet 1/0/1
  no switchport general allowed vlan 10,20,25,30,31,35,40,50,51,52,99,999
exit
end
copy running-config startup-config
```

---

## Step 5: Builder Cutover to Management VLAN

Move the builder (`provisioner-ph01`) from the flat network to VLAN 99 with a static IP. This eliminates the DHCP dependency — the builder's eth0 is configured with a static address before its port moves to the new VLAN. After this step, the builder has routed access to all VLANs for the rest of the migration.

**Prerequisites:**
- Step 4 complete (trunk uplink carrying VLAN 99)
- Configure the OPNsense VLAN 99 interface with gateway IP `10.20.99.1/24`:
  - OPNsense GUI -> Interfaces -> Assignments: assign the VLAN 99 device to an interface slot
  - Set IPv4 to static `10.20.99.1/24`, enable the interface, apply

**5a — Configure builder eth0 as static IP on the target network:**

```bash
cd ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit provisioner-ph01 \
  -i ../ansible-inventory-deevnet/dvntm-new
```

This configures eth0 with `10.20.99.95/24`, gateway `10.20.99.1` and **immediately reloads the interface**. The playbook will end with a connection error — this is expected. The builder's eth0 is now on `10.20.99.95` but its switch port is still on VLAN 1, so it is temporarily unreachable on either address.

**5b — Add VLAN 99 management IP to the switch:**

The switch management interface is on VLAN 1 (`192.168.10.10`). After the builder moves to VLAN 99, it can no longer reach the switch on VLAN 1 (VLAN 1 is not carried on the trunk). This step adds a second management IP on VLAN 99 so the switch is dual-homed and reachable from both VLANs during the transition.

```bash
cd ansible-collection-deevnet.net
make migration-switch-mgmt-ip
```

The switch is now reachable at both `192.168.10.10` (VLAN 1) and `10.20.99.10` (VLAN 99). The VLAN 1 address is removed in Step 11 after migration completes.

**5c — Move builder port (`gi1/0/16`) to VLAN 99:**

```bash
ANSIBLE_COLLECTIONS_PATH="./.ansible/collections:~/.ansible/collections" \
  ansible-playbook playbooks/migration/04-switch-test-port.yml \
  -e test_port_interface="gigabitEthernet 1/0/16" \
  -e test_port_vlan_id=99
```

Once the port moves to VLAN 99, the builder becomes reachable at `10.20.99.95`.

**Verify:**
1. Reconnect: `ssh a_autoprov@10.20.99.95`
2. `ping 10.20.99.1` (management gateway) — should succeed
3. `ping 8.8.8.8` — internet access works
4. Switch responds to SSH at new address: `ssh $SWITCH_USER@10.20.99.10`

**Rollback:**
1. Revert builder port to VLAN 1 via console:
   ```
   configure terminal
   interface gigabitEthernet 1/0/16
     switchport access vlan 1
   end
   copy running-config startup-config
   ```
2. Remove VLAN 99 management IP from switch:
   ```
   configure terminal
   no interface vlan 99
   end
   copy running-config startup-config
   ```
3. Re-run builder playbook with the current (dvntm) inventory to restore DHCP/original static config:
   ```bash
   cd ansible-collection-deevnet.builder
   ansible-playbook playbooks/site.yml --limit provisioner-ph01
   ```

---

## Step 6: Test Second Port

Test a non-builder port on a different VLAN to validate the trunk + VLAN path end-to-end.

**Run:**
```bash
cd ansible-collection-deevnet.net
# Default: port gi1/0/24 -> VLAN 10 (trusted)
make migration-switch-test-port
```

**Verify:**
1. Connect a device to `gi1/0/24`
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

## Step 7: DHCP for New Subnets

Configure Kea DHCP subnets and static reservations for the new VLAN subnets.

Ensure Kea DHCP subnets are created in OPNsense first (Services -> Kea DHCP -> Subnets) and `dhcp_subnet_uuid` is updated in `group_vars/routers/vars.yml` for each subnet.

{{< hint info >}}
**Note:** VLAN 99 already has its gateway IP configured from Step 5. The DHCP configuration here covers the remaining subnets. VLAN 99 devices (builder, switch) use static IPs and do not require DHCP reservations.
{{< /hint >}}

**Run:**
```bash
make migration-opnsense-dhcp
```

**Verify:**
1. OPNsense GUI -> Services -> Kea DHCP -> Subnets — new subnets visible
2. OPNsense GUI -> Services -> Kea DHCP -> Reservations — static mappings present
3. A device on the test port (Step 6) gets a correct DHCP lease

**Rollback:**
Delete DHCP subnets and reservations via OPNsense GUI -> Services -> Kea DHCP.

---

## Step 8: OPNsense Interface IPs

Assign gateway IP addresses to each remaining VLAN interface and enable them. After this step, the router can route traffic between VLAN subnets (subject to firewall policy).

{{< hint info >}}
**Note:** VLAN 99 was already configured with its gateway IP (`10.20.99.1/24`) in Step 5 as a prerequisite for the builder cutover.
{{< /hint >}}

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
3. From test port (Step 6): `ping 10.20.10.1` (trusted gateway) — should succeed

**Rollback:**
Remove IP assignments via OPNsense GUI -> Interfaces -> select each VLAN interface -> clear IP and disable.

---

## Step 9: Inter-VLAN Firewall Rules

Apply zone-based firewall policy (default-deny with explicit inter-zone allows). Rules are defined in `group_vars/all/firewall.yml` and managed via the OPNsense filter API.

**Prerequisites:**
- Step 8 complete (VLAN interfaces have IPs and are enabled)

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

## Step 9b: Trunk PVID Cutover to Blackhole

Set the trunk uplink PVID to 999 (blackhole). After this step, untagged traffic on the trunk goes to the blackhole VLAN. The router is now reachable only via tagged VLAN interfaces.

**Prerequisites:**
- Step 8 complete (OPNsense VLAN interfaces have IPs — the router is reachable via tagged VLANs)
- Verify the router is reachable via a VLAN IP before proceeding: `ping 10.20.99.1`

**Run:**
```bash
make migration-switch-trunk-pvid
```

**Verify:**
```
show interface switchport gigabitEthernet 1/0/1
```
- PVID: 999

**Rollback:**
```
configure terminal
interface gigabitEthernet 1/0/1
  switchport pvid 1
exit
end
copy running-config startup-config
```

---

## Step 10: Migrate Remaining Access Ports

Move all remaining switch ports to their assigned VLANs as defined in `host_vars/access-sw01.yml`.

{{< hint info >}}
**DNS:** New 10.20.x.x addresses will not resolve via DNS until post-migration (Step 11 / Post-Migration). This is expected — Ansible uses inventory IPs directly. Use IP addresses for any manual verification during this step.
{{< /hint >}}

{{< hint warning >}}
**Wireless clients:** AP SSID-to-VLAN mappings are not reconfigured in this step. When the AP's port moves to its target VLAN, wireless clients may lose connectivity. SSID configuration is handled in Step 13 after Omada adoption (Step 12).
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

## Step 11: Management Cutover (Manual)

After all ports are migrated and verified:

1. **Switch management VLAN** — remove the old VLAN 1 management interface. The switch already has a VLAN 99 management IP (`10.20.99.10`) from Step 5b.
   ```
   configure terminal
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

## Step 12: Omada Device Adoption

After management cutover, adopt the switch and AP into the Omada SDN controller. Treat this as a fresh Omada install — devices are on new IPs/VLANs and need to be discovered and adopted.

**Prerequisites:**
- Step 11 complete (switch on VLAN 99 management IP, inventory promoted)
- Builder reachable at `10.20.99.95`

**Run:**
1. Access the Omada controller at `https://10.20.99.95:8043`
2. Complete the initial setup wizard (fresh install)
3. Adopt `access-sw01` — it should appear as pending on VLAN 99 (management) at `10.20.99.10`
4. Adopt `ap01` — it should appear as pending on its assigned VLAN
5. If devices don't auto-discover, use manual adoption by IP

**Verify:**
1. Both devices show as "Connected" in the Omada dashboard
2. Switch and AP firmware/model info visible in Omada

**Rollback:**
Omada adoption is non-disruptive — devices continue to function without Omada management. Remove a device from Omada if needed and re-adopt later.

---

## Step 13: AP SSID Configuration

Configure SSID-to-VLAN mappings for wireless networks via the Omada controller.

**Prerequisites:**
- Step 12 complete (AP adopted in Omada)

**Run:**
1. In the Omada controller, configure SSID-to-VLAN mappings for each wireless network
2. Assign each SSID to its appropriate VLAN ID

**Verify:**
1. Wireless client connects to an SSID
2. Client receives a DHCP lease from the correct VLAN subnet
3. Client has internet access

**Rollback:**
Revert SSID settings in Omada, or factory reset the AP and re-adopt in Step 12.

---

## Post-Migration

After all steps complete and connectivity is verified:

1. **Run automated post-migration validation:**
   ```bash
   cd ansible-collection-deevnet.net
   make postcheck
   ```
   This runs against the `dvntm-new` inventory and validates:
   - OPNsense has all expected VLAN interfaces
   - Switch VLAN database and trunk uplink are correct
   - All devices (switch, AP, builder) are reachable at target IPs
   - All VLAN gateways are reachable (inter-VLAN routing works)
   - Builder services are active with correct interface addresses

   All checks should show `[PASS]`. Internet connectivity shows `[WARN]` if unreachable (non-fatal).

2. **Re-encrypt vault files:**
   ```bash
   cd ansible-inventory-deevnet
   make vault
   ```

3. **Run full DNS/DHCP roles** against `dvntm-new` inventory:
   ```bash
   make dns
   make dhcp
   ```

4. **Remove old network config:**
   - Delete 192.168.10.0/24 subnet from OPNsense
   - Remove any old static routes referencing 192.168.10.x

5. **Ongoing switch management** — use the `switch` target for day-2 operations:
   ```bash
   make switch
   ```

6. **Update documentation** — verify network-reference.md reflects the new state

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

### Builder lost connectivity during Step 5
- Verify ethernet cable is connected to `gi1/0/16` — do not rely on WiFi for substrate access
- Check port VLAN assignment: `show interface switchport gigabitEthernet 1/0/16`
- Verify VLAN 99 interface is enabled with IP `10.20.99.1` in OPNsense
- If the builder has the wrong static IP config, revert the port to VLAN 1 and re-run the builder playbook with the dvntm inventory
- If the builder is unreachable, Omada adoption (Step 12) cannot proceed — but the switch and AP continue to function independently
- Last resort: revert the builder port to VLAN 1 via console:
  ```
  configure terminal
  interface gigabitEthernet 1/0/16
    switchport access vlan 1
  end
  copy running-config startup-config
  ```

### Inter-VLAN routing not working
- Verify VLAN interfaces have IP addresses assigned in OPNsense
- Check OPNsense firewall rules for inter-VLAN traffic
- Verify routing table: OPNsense GUI -> System -> Routes
