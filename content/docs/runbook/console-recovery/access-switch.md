---
title: "Access Switch"
weight: 3
---

# Access Switch

Recovering `dv02acc001p01` when it can no longer be reached at 10.20.99.10 — by discarding
its configuration and rebuilding it from inventory.

The switch's whole configuration is declared: VLAN database, trunks, access ports, hostname
and default gateway all come from `host_vars/dv02acc001p01.yml` and are applied by one
playbook. That makes a factory reset a legitimate recovery tool rather than a last resort —
there is nothing on the switch worth preserving that is not already in git.

{{< hint danger >}}
**A factory reset takes the whole site down until the playbook has run.** Every port returns
to default VLAN 1, which means the uplink trunk to `dv02cor002p01` is gone, inter-VLAN
routing stops, and every host on this switch loses its segment. Do this deliberately, with
time set aside — not as a quick thing to try.
{{< /hint >}}

## Try this first

If the switch still responds on a console cable, fixing the specific fault is faster and far
less disruptive than a reset. The usual culprit after a trunk change is a native VLAN
mismatch on the uplink — see
[troubleshooting](/docs/runbook/network-migration/troubleshooting/#lost-switch-access-after-trunk-configuration),
which covers reverting a port from the console.

Reset only when the switch is unreachable by every route, or its configuration is unknown.

---

## What you need

| | |
|---|---|
| **Access** | Physical, to press and hold the reset button. |
| **A laptop** | To reach the switch on its factory address before it is back on the network. |
| **A patch cable** | Direct into any switch port. |

| | |
|---|---|
| Device | `dv02acc001p01`, TP-Link Omada managed switch |
| Managed address | 10.20.99.10, gateway 10.20.99.1 |
| Uplink to router | `gigabitEthernet 1/0/1`, native VLAN 999 |
| Builder port | `gigabitEthernet 1/0/16`, access VLAN 99 |
| Declared by | `switch_ports` in `mobile/host_vars/dv02acc001p01.yml` |
| Applied by | `ansible-collection-deevnet.net`, `playbooks/switch-vlans.yml` |

---

## 1. Reset

Press and hold the reset button until the switch restarts into factory defaults.

---

## 2. Bootstrap it back onto the network

This is the step automation cannot do for you. Ansible reaches the switch at the address
derived from inventory (10.20.99.10), and a factory-reset switch is not there yet.

Connect your laptop directly to a switch port and give yourself an address on the switch's
default subnet — the same manoeuvre the
[AP procedure](/docs/runbook/console-recovery/wireless-ap/) uses:

```bash
sudo ip addr add 192.168.0.2/24 dev <iface>
```

{{< hint warning >}}
**Confirm the factory address on the device label before assuming it.** TP-Link Omada
switches commonly return to `192.168.0.1/24` with `admin`/`admin`, but this varies by model
and firmware. Once confirmed for this switch, record it in this table so the next person does
not have to guess.
{{< /hint >}}

In the switch's web UI or CLI, set just enough for Ansible to take over:

- the management IP `10.20.99.10/24` on the management VLAN
- the default gateway `10.20.99.1`
- the uplink port `gigabitEthernet 1/0/1` trunking to the router

Everything else is left alone — the playbook writes it.

---

## 3. Reapply the declared configuration

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/switch-vlans.yml
```

This restores the VLAN database, the trunk ports and their native VLANs, the access port
assignments, the hostname and the default gateway, and commits to flash via the
`write memory` handler.

{{< hint info >}}
**`--check` is not useful here.** `ansible.netcommon.cli_command` accepts only `show`
commands in check mode, so a dry run fails on every configuration line rather than previewing
it. See [Change Management](/docs/runbook/change-management/).
{{< /hint >}}

---

## 4. Verify

From the switch:

```
show vlan brief
show interface switchport gigabitEthernet 1/0/1
show running-config
```

From the builder:

```bash
ping -c1 10.20.99.10        # the switch itself
ping -c1 10.20.99.1         # the router, through the restored trunk
ping -c1 10.20.30.11        # a host on another segment
```

Every VLAN in [the network reference](/docs/runbook/network-reference/) should be present,
and `gigabitEthernet 1/0/1` should be trunking with native VLAN 999.

---

## 5. Re-adopt in Omada

A factory reset drops the switch out of the Omada controller. Re-adopt it at
`https://10.20.99.95:8043`, following
[Omada device adoption](/docs/runbook/network-migration/port-migration/#step-12-omada-device-adoption).

Adoption is management only — the switch forwards traffic correctly whether or not Omada has
claimed it, so this is the last step rather than a prerequisite.

---

## Related

- [Access switch platform](/docs/platforms/network/access-switch/) — what the device is and how it is wired
