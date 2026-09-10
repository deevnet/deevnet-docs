---
title: "Undo Procedure"
weight: 7
---

# Undo Procedure

How to back the migration out, step by step, **in reverse order**. Back out only as far as the
fault requires. Each block returns the network to where it was before that step ran.

These are the rollbacks written into the plan, collected in one place. Where the plan had
none, this page says so rather than supplying one.

{{< hint danger >}}
**Step 11 is where undo stops being practical, and it has no written undo.** Step 11 removes
the switch's VLAN 1 management interface and promotes the new inventory. After it, the old
network can no longer be reached the way the earlier undos assume.
{{< /hint >}}

Every switch block ends in `copy running-config startup-config`. Without it, the undo lasts
only until the next reboot.

---

## Undo Step 13

AP SSID configuration. Factory reset the AP and reconfigure the SSIDs.

## Undo Step 12

Omada adoption. Adoption was treated as non-disruptive: remove the device from Omada and adopt
it again later.

## Undo Step 11

Management cutover. **The plan has no undo for this step.**

## Undo Step 10

Access ports. Move the ports back to VLAN 1 (SG2218 General mode):

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

## Undo Step 9b

Trunk PVID. Put the uplink's native VLAN back to 1:

```
configure
interface gigabitEthernet 1/0/1
  switchport pvid 1
exit
end
copy running-config startup-config
```

## Undo Step 9

Firewall policy. In the OPNsense GUI, go to **Firewall → Automation → Filter**, delete the rules
prefixed `ansible:`, then apply.

## Undo Step 8

Interface IPs. In the OPNsense GUI, go to **Interfaces**, and for each VLAN interface clear the
IP and disable it.

## Undo Step 7

DHCP. In the OPNsense GUI, go to **Services → Kea DHCP** and delete the new subnets and
reservations.

## Undo Step 6

Test port. Return the test port to VLAN 1:

```
configure
interface gigabitEthernet 1/0/24
  switchport access vlan 1
end
copy running-config startup-config
```

## Undo Step 5

Builder cutover, covering 5b–5d. The plan has no undo for 5a (interface assignment) or 5a2
(temporary firewall rules).

1. Revert the builder port to VLAN 1 from the console (SG2218 General mode):
   ```
   configure
   interface gigabitEthernet 1/0/16
     switchport general allowed vlan 1 untagged
     switchport pvid 1
   exit
   end
   copy running-config startup-config
   ```
2. Remove the switch's VLAN 99 management IP:
   ```
   configure
   no interface vlan 99
   end
   copy running-config startup-config
   ```
3. Re-run the builder playbook with the current (`dvntm`) inventory, to restore the builder's
   original network configuration:
   ```bash
   cd ansible-collection-deevnet.builder
   ansible-playbook playbooks/site.yml --limit dv00bld001p01
   ```

If the builder cannot be reached at all, see
[builder lost connectivity](/docs/changes/2026/2026-03-21-flat-network-to-vlans/troubleshooting/#builder-lost-connectivity-during-step-5).

## Undo Step 4

Trunk tagging. Remove the tagged VLANs from the uplink:

```
configure
interface gigabitEthernet 1/0/1
  no switchport general allowed vlan 10,20,25,30,31,35,40,50,51,52,99,999
exit
end
copy running-config startup-config
```

## Undo Step 3

Switch VLAN database. Delete the VLANs:

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

## Undo Step 2

OPNsense VLAN devices. In the OPNsense GUI, go to **Interfaces → Devices → VLAN** and delete
each entry.

## Undo Step 1

Preflight. Nothing to undo; it is read-only.
