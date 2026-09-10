---
title: "Access Switch"
weight: 3
aliases:
  - /docs/runbook/console-recovery/access-switch/
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
[troubleshooting](/docs/changes/2026/2026-03-21-flat-network-to-vlans/troubleshooting/#lost-switch-access-after-trunk-configuration),
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
| Device | `dv02acc001p01`, TP-Link Omada SG2218, hardware 1.20 |
| Firmware | `1.20.1 Build 20240115` as of 2026-09-10; `1.20.24` staged — see [firmware upgrade](#firmware-upgrade) |
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
[AP procedure](/docs/runbook/recovery/console-recovery/wireless-ap/) uses:

```bash
sudo ip addr add 192.168.0.2/24 dev <iface>
```

{{< hint warning >}}
**Confirm the factory address on the device label before assuming it.** TP-Link Omada
switches commonly return to `192.168.0.1/24`, but this varies by model and firmware. Once
confirmed for this switch, record it in this table so the next person does not have to guess.

**What a reset switch lets you in with depends on its firmware.** Up to 1.20.14 it is
`admin`/`admin`, as the label says. From 1.20.17 TP-Link removed the default username and
password, so expect first login to ask you to create an account instead — create it with
`vault_switch_user` / `vault_switch_password` from `group_vars/switches`, since that is the
account Ansible logs in with. From 1.20.4 standalone mode also starts with HTTP off: browse
`https://`.
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

Every VLAN in [the network reference](/docs/runbook/network/network-reference/) should be present,
and `gigabitEthernet 1/0/1` should be trunking with native VLAN 999.

---

## 5. Re-adopt in Omada

A factory reset drops the switch out of the Omada controller. Re-adopt it at
`https://10.20.99.95:8043`, following
[Omada device adoption](/docs/changes/2026/2026-03-21-flat-network-to-vlans/port-migration/#step-12-omada-device-adoption).

Adoption is management only — the switch forwards traffic correctly whether or not Omada has
claimed it, so this is the last step rather than a prerequisite.

If this is replacement hardware rather than the same switch, check its firmware before
adopting. A reset does not change firmware, but a new unit arrives on whatever it shipped
with — see [firmware upgrade](#firmware-upgrade).

---

## Firmware upgrade

This is not a recovery step. It is a planned change, made while the switch is reachable and its
configuration is intact. Nothing is reset, the configuration is kept, and the playbook does
not need to run.

| | |
|---|---|
| Hardware | SG2218 **1.20**, per `show system-info`. A label reading V1.26 takes the same firmware. |
| Running | `1.20.1 Build 20240115` in `image2.bin`, as of 2026-09-10. `image1.bin` holds the factory `1.1.3`. |
| Target | `1.20.24 Build 20260509` |
| Route | **One hop.** None of the eight V1.20 builds since declares a minimum prior version or is flagged irreversible. |
| File | `http://artifacts.mobile.deevnet.net/firmware/sg2218/`, pinned in `artifacts_to_fetch` |

Do this before the switch is adopted into Omada, not after. The controller-facing code is
what changed most: 1.20.14 is the first build TP-Link align with controller 6.x, and 1.20.17
fixed security vulnerabilities in the switch's interaction with the controller. 1.20.24
recommends controller 6.2.0 or later; this site's controller has run 6.3.0.45 since
2026-09-10.

{{< hint danger >}}
**The reboot takes down every wired path on the site, including the builder's.** The browser
you uploaded from, Ansible, the Omada controller and the route to every segment all go with it
until the switch is back. The hypervisors are not clustered, so nothing fences: guests keep
running, just unreachable. The AP loses its uplink. Set time aside, and have the console cable
to hand.
{{< /hint >}}

### 1. Record where it starts

From the builder (decrypt the vault first, or add `--ask-vault-pass`):

```bash
cd ansible-collection-deevnet.net
ansible dv02acc001p01 -m ansible.netcommon.cli_command -a "command='show system-info'"
ansible dv02acc001p01 -m ansible.netcommon.cli_command -a "command='show image-info'"
ansible dv02acc001p01 -m ansible.netcommon.cli_command -a "command='show running-config'" \
  > ~/dv02acc001p01-running-config-1.20.1.txt
```

The switch holds two images. `show image-info` shows which one boots and which is the backup.
The upload is written into the backup slot, so whichever slot holds 1.20.1 now is the rollback.
On 2026-09-10 that was `image2.bin`. The backup, `image1.bin`, held the factory `1.1.3`, which
the upload replaces; nothing is lost with it.

### 2. Upload into the backup image

Download the `.bin` from the artifact server to the machine running the browser. From the
builder, browse `https://10.20.99.10` directly — the builder is on the management segment with
the switch, so no tunnel is needed.

Under **SYSTEM → System Tools → Firmware Upgrade**, choose
`SG2218v1_en_1.20.24_[20260509-rel23533]_up.bin` and **leave "Reboot the switch using the
backup image after upgrading is completed" unchecked**. With it unchecked, the upload writes the
backup image and the switch keeps running 1.20.1. A failed write then costs nothing, and the
outage happens when you choose rather than as a side effect of the upload. The write takes
several minutes; leave the switch alone while it runs.

### 3. Boot from it

Under **SYSTEM → System Tools → Boot Config**, the image table should now show 1.20.24 in the
backup image. If it does not, stop here — nothing has changed yet. Otherwise set that image as
**Next Startup Image** and the current one as **Backup Image**, then **Apply**.

Then use **SYSTEM → System Tools → System Reboot**, with **Save the current configuration before
reboot** checked. Running and startup config should already match, because the playbook ends in
`write memory`, so the save should add nothing. It is TP-Link's instruction and does no harm.

Wait for it from the builder with `ping 10.20.99.10`.

### 4. Verify

Rerun the `show system-info` and `show image-info` commands from step 1. The version should
read `1.20.24 Build 20260509`, and the backup image should hold 1.20.1.

The most important check is that those commands run at all. Ansible reaches this switch over
SSH with legacy key exchange (see the options in
[post-migration](/docs/changes/2026/2026-03-21-flat-network-to-vlans/post-migration/)), and two years of builds —
including an OpenSSL update in 1.20.4 and an SSH stability fix in 1.20.19 — are where that
could change.

Then compare the running config with step 1's capture; expect only additions. Two builds in
between change defaults: spanning tree is on by default from 1.20.9, and LLDP from 1.20.4. A
setting that was never written to config, because it matched the old default, is the kind that
can come up under a new one. Check `show spanning-tree active` in particular. If STP is now on,
decide deliberately whether it stays, and declare that decision either way instead of
inheriting it.

Run the recovery [verification](#4-verify) pings, then the playbook once:

```bash
ansible-playbook playbooks/switch-vlans.yml
```

It applies nothing that is not already declared. It is also the only test that the role's
command grammar still parses on the new firmware, and that is better learned now than in the
middle of a recovery.

### Rollback

1.20.1 is still on flash, in the backup image. In **Boot Config**, set it as **Next Startup
Image**, **Apply**, and reboot. There is no re-flash and no download. The configuration is
kept, although anything configured through a feature newer than 1.20.1 will not apply.

---

## Related

- [Access switch platform](/docs/platforms/network/access-switch/) — what the device is and how it is wired
