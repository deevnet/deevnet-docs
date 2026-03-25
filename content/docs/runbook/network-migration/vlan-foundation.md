---
title: "VLAN Foundation"
weight: 2
---

# VLAN Foundation

Create the VLAN infrastructure on the router and switch. All steps in this phase are non-disruptive — no existing traffic is affected.

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

Add all VLANs as tagged members on the uplink port. The PVID stays at 1 (the router's untagged traffic continues on VLAN 1). The PVID cutover to blackhole (999) happens in [Step 9b](../services-and-routing/#step-9b-trunk-pvid-cutover-to-blackhole) — after OPNsense VLAN interfaces have IPs and the router is reachable via tagged VLANs.

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
