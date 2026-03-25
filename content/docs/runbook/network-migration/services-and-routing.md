---
title: "Services & Routing"
weight: 4
---

# Services & Routing

Configure DHCP, interface IPs, firewall rules, and trunk PVID. After this phase, all VLANs are fully routed and served.

{{< hint info >}}
**Post-cutover inventory:** All `make` targets from this point forward automatically use the `dvntm-new` inventory (target IPs on the new VLAN subnets). The builder is on VLAN 99 and can only reach devices at their new addresses. No manual `-i` overrides are needed.
{{< /hint >}}

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

## Step 7: DHCP for New Subnets

Configure Kea DHCP subnets and static reservations for the new VLAN subnets.

Ensure Kea DHCP subnets are created in OPNsense first (Services -> Kea DHCP -> Subnets) and `dhcp_subnet_uuid` is updated in `group_vars/routers/vars.yml` for each subnet.

{{< hint info >}}
**Note:** VLAN 99 already has its gateway IP configured from [Step 5](../builder-cutover/). The DHCP configuration here covers the remaining subnets. VLAN 99 devices (builder, switch) use static IPs and do not require DHCP reservations.
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
**Note:** VLAN 99 was already configured with its gateway IP (`10.20.99.1/24`) in [Step 5](../builder-cutover/) as a prerequisite for the builder cutover.
{{< /hint >}}

**Prerequisites:**
- [Step 2](../vlan-foundation/#step-2-opnsense-vlan-interfaces) complete (VLAN sub-interfaces exist on OPNsense)
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
