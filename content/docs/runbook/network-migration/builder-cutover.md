---
title: "Builder Cutover"
weight: 3
---

# Builder Cutover to Management VLAN

Move the builder (`provisioner-ph01`) from the flat network to VLAN 99 with a static IP. This eliminates the DHCP dependency — the builder's eth0 is configured with a static address before its port moves to the new VLAN. After this step, the builder has routed access to all VLANs for the rest of the migration.

**Prerequisites:**
- [Step 4](../vlan-foundation/#step-4-trunk-uplink-tagged-vlans) complete (trunk uplink carrying tagged VLANs)

---

## 5a — Assign and configure OPNsense VLAN interfaces

Assign all VLAN devices to OPNsense interface slots and configure gateway IPs. The OPNsense API does not support interface assignment ([GitHub #7324](https://github.com/opnsense/core/issues/7324)), so the playbook will pause and prompt you to complete a manual GUI step before continuing with automated IP configuration.

{{< hint warning >}}
**Manual Steps Required:** OPNsense (as of 25.7) has no API for interface assignment OR setting interface IPs. Both must be done via the GUI. If the builder is headless, use an SSH tunnel: `ssh -L 8443:192.168.10.1:443 a_autoprov@<builder-ip>` then open `https://localhost:8443`.
{{< /hint >}}

**Step 1 — Apply VLAN devices:** Go to **Interfaces → Devices → VLAN**. Click the **Apply** button at the bottom. This activates the VLAN devices on the OS — without this, they won't appear for assignment.

**Step 2 — Assign each VLAN device to an interface slot:** Go to **Interfaces → Assignments**. Use the **"New interface"** dropdown at the bottom to add each VLAN device (vlan01 through vlan012) one at a time. Click **+** (Add) after each. Click **Save** when done.

**Step 3 — Configure IPs on each VLAN interface:** The playbook will show which interfaces need IPs. For each one, go to **Interfaces → [OPT name]** and set **IPv4 Configuration Type** to Static IPv4, enter the gateway IP shown by the playbook (e.g., `10.20.99.1/24`), check **Enable Interface**, and click **Save**. After all interfaces are configured, click **Apply changes**.

```bash
cd ansible-collection-deevnet.net
make migration-opnsense-assign
```

The playbook checks which VLAN devices are unassigned, pauses for the manual GUI step above, then automatically configures all gateway IPs and enables the interfaces.

After this step, all VLAN gateways (including `10.20.99.1` for management) are active.

---

## 5a2 — Temporary firewall rules for VLAN interfaces

OPNsense default-denies all traffic on new OPT interfaces. This adds temporary pass-all rules via the firewall API so traffic flows during migration. [Step 9](../services-and-routing/#step-9-inter-vlan-firewall-rules) replaces these with proper zone-based policy.

{{< hint info >}}
**Note:** This step runs AFTER the builder is on VLAN 99 and uses the VLAN 99 gateway IP (`10.20.99.1`) to reach OPNsense. If running during initial setup (builder still on VLAN 1), the playbook will need the `opnsense_api_url` overridden.
{{< /hint >}}

```bash
make migration-opnsense-temp-fw
```

---

## 5b — Add VLAN 99 management IP to the switch

Add a second management IP on VLAN 99 to the switch while the builder can still reach it on VLAN 1. This must happen **before** the builder's IP changes — otherwise the builder and switch are on different subnets and cannot communicate.

```bash
cd ansible-collection-deevnet.net
make migration-switch-mgmt-ip
```

The switch is now reachable at both `192.168.10.10` (VLAN 1) and `10.20.99.10` (VLAN 99). The VLAN 1 address is removed in [Step 11](../port-migration/#step-11-management-cutover) after migration completes.

---

## 5c — Configure builder eth0 as static IP on the target network

{{< hint info >}}
**Chicken-and-egg:** The `dvntm-new` inventory resolves `ansible_host` to the target IP (`10.20.99.95`), which doesn't exist yet. The `BUILDER_CURRENT_IP` variable tells the Makefile to connect via the current IP instead.
{{< /hint >}}

```bash
make rebuild
make migration-builder-network BUILDER_CURRENT_IP=192.168.10.95
```

This runs only the `base` role (network config) against the builder. It configures eth0 with `10.20.99.95/24`, gateway `10.20.99.1` and **immediately reloads the interface**. The playbook will end with a timeout after the interface reload — this is expected. The builder's eth0 is now on `10.20.99.95` but its switch port is still on VLAN 1, so it is temporarily unreachable on either address.

---

## 5d — Move builder port (`gi1/0/16`) to VLAN 99

The builder's IP changed but its port is still on VLAN 1. The builder and switch are on different subnets on the same VLAN, so the playbook temporarily adds the old IP as a secondary address to reach the switch, moves the port, then cleans up.

```bash
make migration-builder-port-move
```

Once the port moves to VLAN 99, the builder becomes reachable at `10.20.99.95` on the management VLAN.

---

## Verify

1. Reconnect: `ssh a_autoprov@10.20.99.95`
2. `ping 10.20.99.1` (management gateway) — should succeed
3. `ping 8.8.8.8` — internet access works
4. Switch responds to SSH at new address: `ssh $SWITCH_USER@10.20.99.10`

## Rollback

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
