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
configure
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
configure
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
- Step 4 complete (trunk uplink carrying tagged VLANs)

**5a — Assign and configure OPNsense VLAN interfaces:**

Assign all VLAN devices to OPNsense interface slots and configure gateway IPs. The OPNsense API does not support interface assignment ([GitHub #7324](https://github.com/opnsense/core/issues/7324)), so the playbook will pause and prompt you to complete a manual GUI step before continuing with automated IP configuration.

{{< hint warning >}}
**Manual Steps: OPNsense GUI — Interface Assignment and IP Configuration**

OPNsense (as of 25.7) has no API for interface assignment OR setting interface IPs. Both must be done via the GUI. If the builder is headless, use an SSH tunnel from your desktop: `ssh -L 8443:192.168.10.1:443 a_autoprov@<builder-ip>`, then open `https://localhost:8443`.

1. **Apply VLAN devices:** Go to **Interfaces → Devices → VLAN**. Click the **Apply** button at the bottom. This activates the VLAN devices on the OS — without this, they won't appear for assignment.

2. **Assign each VLAN device to an interface slot:** Go to **Interfaces → Assignments**. Use the **"New interface"** dropdown at the bottom to add each VLAN device (vlan01 through vlan012) one at a time. Click **+** (Add) after each. Click **Save** when done.

3. **Configure IPs on each VLAN interface:** The playbook will show which interfaces need IPs. For each one, go to **Interfaces → [OPT name]**, set:
   - **IPv4 Configuration Type:** Static IPv4
   - **IPv4 address:** the gateway IP shown by the playbook (e.g., `10.20.99.1/24`)
   - **Check "Enable Interface"**
   - Click **Save**

   After all interfaces are configured, click **Apply changes**.
{{< /hint >}}

```bash
cd ansible-collection-deevnet.net
make migration-opnsense-assign
```

The playbook checks which VLAN devices are unassigned, pauses for the manual GUI step above, then automatically configures all gateway IPs and enables the interfaces.

After this step, all VLAN gateways (including `10.20.99.1` for management) are active.

**5a2 — Temporary firewall rules for VLAN interfaces:**

OPNsense default-denies all traffic on new OPT interfaces. This adds temporary pass-all rules via the firewall API so traffic flows during migration. Step 9 replaces these with proper zone-based policy.

{{< hint info >}}
**Note:** This step runs AFTER the builder is on VLAN 99 and uses the VLAN 99 gateway IP (`10.20.99.1`) to reach OPNsense. If running during initial setup (builder still on VLAN 1), the playbook will need the `opnsense_api_url` overridden.
{{< /hint >}}

```bash
make migration-opnsense-temp-fw
```

**5b — Add VLAN 99 management IP to the switch:**

Add a second management IP on VLAN 99 to the switch while the builder can still reach it on VLAN 1. This must happen **before** the builder's IP changes — otherwise the builder and switch are on different subnets and cannot communicate.

```bash
cd ansible-collection-deevnet.net
make migration-switch-mgmt-ip
```

The switch is now reachable at both `192.168.10.10` (VLAN 1) and `10.20.99.10` (VLAN 99). The VLAN 1 address is removed in Step 11 after migration completes.

**5c — Configure builder eth0 as static IP on the target network:**

{{< hint info >}}
**Chicken-and-egg:** The `dvntm-new` inventory resolves `ansible_host` to the target IP (`10.20.99.95`), which doesn't exist yet. The `BUILDER_CURRENT_IP` variable tells the Makefile to connect via the current IP instead.
{{< /hint >}}

```bash
make rebuild
make migration-builder-network BUILDER_CURRENT_IP=192.168.10.95
```

This runs only the `base` role (network config) against the builder. It configures eth0 with `10.20.99.95/24`, gateway `10.20.99.1` and **immediately reloads the interface**. The playbook will end with a timeout after the interface reload — this is expected. The builder's eth0 is now on `10.20.99.95` but its switch port is still on VLAN 1, so it is temporarily unreachable on either address.

**5d — Move builder port (`gi1/0/16`) to VLAN 99:**

The builder's IP changed but its port is still on VLAN 1. The builder and switch are on different subnets on the same VLAN, so the playbook temporarily adds the old IP as a secondary address to reach the switch, moves the port, then cleans up.

```bash
make migration-builder-port-move
```

Once the port moves to VLAN 99, the builder becomes reachable at `10.20.99.95` on the management VLAN.

**Verify:**
1. Reconnect: `ssh a_autoprov@10.20.99.95`
2. `ping 10.20.99.1` (management gateway) — should succeed
3. `ping 8.8.8.8` — internet access works
4. Switch responds to SSH at new address: `ssh $SWITCH_USER@10.20.99.10`

**Rollback:**
1. Revert builder port to VLAN 1 via console (SG2218 General mode):
   ```
   configure
   interface gigabitEthernet 1/0/16
     switchport general allowed vlan 1 untagged
     switchport pvid 1
   exit
   end
   copy running-config startup-config
   ```
2. Remove VLAN 99 management IP from switch:
   ```
   configure
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
configure
interface gigabitEthernet 1/0/24
  switchport access vlan 1
end
copy running-config startup-config
```

---

{{< hint info >}}
**Post-cutover inventory:** All `make` targets from this point forward automatically use the `dvntm-new` inventory (target IPs on the new VLAN subnets). The builder is on VLAN 99 and can only reach devices at their new addresses. No manual `-i` overrides are needed.
{{< /hint >}}

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
configure
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
Move ports back to VLAN 1 (SG2218 General mode):
```
configure
interface gigabitEthernet 1/0/3
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/14
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/15
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/16
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
end
copy running-config startup-config
```

---

## Step 11: Management Cutover

After all ports are migrated and verified:

1. **Clean up VLAN 1 from migrated ports** — remove stale VLAN 1 membership from all ports that have been moved to new VLANs. On the SG2218, adding a new VLAN does not automatically remove VLAN 1. SSH to the switch and run:
   ```
   configure
   interface gigabitEthernet 1/0/3
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/4
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/14
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/15
   no switchport general allowed vlan 1
   exit
   end
   copy running-config startup-config
   ```

2. **Switch management VLAN** — remove the old VLAN 1 management interface. The switch already has a VLAN 99 management IP (`10.20.99.10`) from Step 5b.
   ```
   configure
   no interface vlan 1
   end
   copy running-config startup-config
   ```

3. **Promote inventory** — `dvntm-new` becomes the active `dvntm`. Use `git mv` to preserve file history:
   ```bash
   cd ansible-inventory-deevnet
   git mv dvntm dvntm-old
   git mv dvntm-new dvntm
   git commit -m "Promote dvntm-new to dvntm for management cutover"
   ```
   No `ansible.cfg` changes needed — it already points to `dvntm`.

4. **Verify Ansible connectivity** from each collection that uses the inventory:
   ```bash
   cd ansible-collection-deevnet.net
   # Switch (SSH/CLI)
   ansible switches -m ansible.netcommon.cli_command -a "command='show image-info'"
   # OPNsense (API only — SSH is not available for a_autoprov)
   ansible dns_servers -m uri -a "url='https://10.20.99.1/api/core/firmware/status' \
     url_username='{{ opnsense_api_key }}' url_password='{{ opnsense_api_secret }}' \
     force_basic_auth=true validate_certs=false"
   ```

5. **Clean up** — once stable, remove the old inventory:
   ```bash
   cd ansible-inventory-deevnet
   git rm -rf dvntm-old
   git commit -m "Remove pre-migration inventory (dvntm-old)"
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
  configure
  interface gigabitEthernet 1/0/16
    switchport access vlan 1
  end
  copy running-config startup-config
  ```

### Inter-VLAN routing not working
- Verify VLAN interfaces have IP addresses assigned in OPNsense
- Check OPNsense firewall rules for inter-VLAN traffic
- Verify routing table: OPNsense GUI -> System -> Routes

---

## To Do

Automation gaps and improvements identified during the initial migration run.

- [ ] **Automate OPNsense interface assignment and IP config:** OPNsense (as of 25.7) has no API for interface assignment ([GitHub #7324](https://github.com/opnsense/core/issues/7324)) OR setting interface IPs (`setInterface` does not exist in the `OverviewController`). Step 5a requires two manual GUI steps: assigning VLAN devices and configuring IPs. Fix: enable SSH access for `a_autoprov` on OPNsense, write a playbook that edits `/conf/config.xml` to add assignments and IPs, then call `configctl interface reconfigure`.
- [ ] **OPNsense firewall rules for new VLAN interfaces:** New OPT interfaces have a default-deny policy with no rules. Each VLAN interface needs at least a temporary pass-all rule before any traffic flows. The Step 5a GUI instructions should include adding pass rules per interface, or Step 9 (firewall automation) should run immediately after interface assignment. Consider automating temp pass rules via the OPNsense filter API as part of Step 5a.
- [ ] **Fix builder port VLAN membership bug:** The `no switchport general allowed vlan 1` command on SG2218 does not reliably leave VLAN 99 as a member. The 05d-builder-port-move playbook must explicitly add VLAN 99 untagged AND remove VLAN 1 in the correct order. Verify the playbook matches what worked manually: `switchport general allowed vlan 99 untagged` first, then `no switchport general allowed vlan 1`.
- [ ] **Remove VLAN 1 from trunk after migration:** VLAN 1 (System-VLAN) remains as an untagged member on the trunk uplink after migration. It is harmless (PVID 999 takes precedence) but should be cleaned up for hygiene.
- [ ] **Verify `cli_config` idempotency on TP-Link SG2218:** The `cli_config` module does not detect existing config on SG2218 due to the minimal cliconf plugin. All switch tasks use `cli_command` with `changed_when: true` (always reports changed). Investigate implementing `get_config` parsing in the cliconf plugin for proper idempotency.
- [ ] **Add pi03, pi04, hv02 port assignments:** These devices were removed from `switch_ports` because they were not connected during migration. Re-add when physically cabled.
- [ ] **Add `builder` group to inventories:** The `builder` group was missing from both `dvntm` and `dvntm-new` inventories, causing the `base` role play in `site.yml` to skip. Added during migration — verify this is the correct long-term grouping.
- [ ] **Switch inventory after builder cutover:** After the builder moves to VLAN 99, the `dvntm` inventory still resolves the switch `ansible_host` to `192.168.10.10` (unreachable from VLAN 99). All post-cutover switch steps must either use the `dvntm-new` inventory (`-i ../ansible-inventory-deevnet/dvntm-new`) or override `ansible_host`. Consider promoting the inventory earlier or adding a migration-phase inventory override to the Makefile.
- [ ] **Fix test-port default port number:** The `04-switch-test-port.yml` playbook defaults to `gigabitEthernet 1/0/24`, but the SG2218 only has 18 ports. Update the default to a valid unused port (e.g., `gigabitEthernet 1/0/18`).
- [ ] **Step 6 verify assumes DHCP before Step 7:** The Step 6 verification expects a DHCP lease on the test VLAN, but DHCP for new subnets is not configured until Step 7. Update Step 6 verify to only check gateway reachability (ping), not DHCP.
