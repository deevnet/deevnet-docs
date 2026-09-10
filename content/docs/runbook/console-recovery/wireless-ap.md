---
title: "Wireless AP"
weight: 4
---

# Wireless AP

Recovering `dv02wap001p01` when it stops answering at 10.20.99.9 or its SSIDs stop serving
the right VLANs — by factory reset, re-adoption, and reapplying its wireless configuration.

Nothing wired depends on the AP, so the site keeps running while you work — but **you**
probably do. The AP supplies primary connectivity here, so the moment it stops serving, the
laptop you would recover it from is off the network too, and every address in this page
becomes unreachable. Getting a wired path onto the management segment is therefore step 1,
not a footnote.

## What you need

| | |
|---|---|
| **Access** | Physical, to press and hold the reset button. |
| **A laptop** | To reach the AP on its factory address. |
| **A patch cable** | Always — it is how you get on the network at all. See step 1. |
| **A wired port on the laptop** | Or a USB-Ethernet adapter. Keep one with the console kit. |

| | |
|---|---|
| Device | `dv02wap001p01`, TP-Link EAP650-Outdoor |
| Managed address | 10.20.99.9, gateway 10.20.99.1 |
| Switch port | `gigabitEthernet 1/0/4` — trunk, native VLAN 99, allowed 10, 30, 31, 40, 99 |
| Controller | Omada, at `https://10.20.99.95:8043` on `dv00bld001p01` |
| Factory address | `192.168.0.254`, `admin`/`admin` — static, **not** DHCP |

---

## 1. Get onto the management network by wire

The AP is the primary path to this site. With it down or mid-reset there is no wireless
management path, and the controller, the switch and the AP's own addresses are all on the far
side of it. Everything below assumes you have already done this.

Cable the laptop into the access switch `dv02acc001p01` on a port that is an **access port on
VLAN 99**. Which port that is matters — the switch does not put a spare port on the management
segment by default.

| Port | VLAN | Use |
|---|---|---|
| `gigabitEthernet 1/0/2` | 99 access | **Free — this is the one to use.** Reserved for exactly this. |
| `gigabitEthernet 1/0/16` | 99 access | `dv00bld001p01` — the builder, which runs the Omada controller |
| `gigabitEthernet 1/0/15` | trunk, native 99 | `dv02hyp001p01` — a trunk since the MQTT broker needed `iot_backend` (35). Not an access port. |

{{< hint warning >}}
**Use 1/0/2, and do not improvise.** `switch_vlans` configures only the ports declared in
`switch_ports` in `host_vars/dv02acc001p01.yml`, and leaves every other port at the switch
default — untagged VLAN 1, which is not in `deevnet_vlans` and is not routed. A laptop in any
other free port gets a link light and nothing else, which reads exactly like a dead switch.

`1/0/2` is declared and held empty for this, and it is the **only** spare untagged-99 port on
the switch. `1/0/15` stopped being an access port when the MQTT broker needed `iot_backend`,
which leaves `1/0/16` as the only other one — and that is the builder. Borrowing it would take
the Omada controller off the network at the moment you need it.
{{< /hint >}}

The port is declared in `host_vars/dv02acc001p01.yml`, first in the access list so that it is
configured before the run reaches `1/0/16` — the port the control node's own session runs over:

```yaml
    - interface: "gigabitEthernet 1/0/2"
      vlan_id: 99
      description: "operator laptop for console recovery"
```

If it ever needs reapplying, do it while the network is still healthy. The access-port commands
are additive — they add VLAN membership and never remove it — so reapplying does not disturb
the ports already in place:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/switch-vlans.yml --limit dv02acc001p01 --tags access
```

### Address the laptop

VLAN 99 is **static only** — there is no DHCP pool on the management segment, so a wired laptop
will not lease an address. Set one by hand from outside the reserved range:

```bash
sudo ip addr add 10.20.99.50/24 dev <iface>
sudo ip route add default via 10.20.99.1
```

Confirm the path before going further — if these fail, the fault is the switch or the router,
not the AP:

```bash
ping -c2 10.20.99.1          # core router
curl -k https://10.20.99.95:8043   # Omada controller on the builder
```

---

## 2. Check the port before resetting the AP

The AP is on a trunk. If its native VLAN or allowed list has drifted, the AP will look dead
while being perfectly healthy — and resetting it will not help.

```
show interface switchport gigabitEthernet 1/0/4
```

Native VLAN 99 with 10, 30, 31, 40 and 99 allowed. If that is wrong, fix the switch — see
[access switch](/docs/runbook/console-recovery/access-switch/) — and stop here.

---

## 3. Reset

Press and hold the reset button until the AP restarts.

A factory-reset EAP does **not** take a DHCP lease. It comes up on a static
`192.168.0.254/24`, which is why a laptop or a temporary address on the builder is needed to
reach it:

```bash
sudo ip addr add 192.168.0.1/24 dev enp4s0
```

Then browse to `http://192.168.0.254` with `admin`/`admin`.

---

## 4. Re-adopt into Omada

Set the AP's **inform URL** to the controller so it can be discovered, then adopt it at
`https://10.20.99.95:8043`. The full sequence is in
[Omada device adoption](/docs/runbook/network-migration/port-migration/#step-12-omada-device-adoption).

Remove the temporary address from the builder once the AP is reachable on the management
segment:

```bash
sudo ip addr del 192.168.0.1/24 dev enp4s0
```

---

## 5. Reapply the SSIDs

{{< hint warning >}}
**Omada cannot push VLAN-tagged SSIDs to this AP.** Omada 6.1 will not provision VLAN
configuration to EAP650-Outdoor firmware 1.0.4 (2023), so the SSIDs must be configured in the
**AP's own standalone web UI**, with their VLAN tags, after adoption. This is a firmware
limitation, not a misconfiguration.
{{< /hint >}}

SSIDs map to the VLANs the trunk allows — `DVNTM-IOT` onto VLAN 30 for custom-firmware
devices, and the trusted, vendor-IoT and guest SSIDs onto 10, 31 and 40. The authoritative
list is `deevnet_vlans` in inventory and
[Step 13](/docs/runbook/network-migration/port-migration/#step-13-ap-ssid-configuration).

Once the AP's firmware has been updated and Omada can provision it, this becomes:

```bash
make migration-omada-ssids
```

---

## 6. Verify

Per SSID, from a client:

- it associates
- it receives a lease from the **expected** subnet — that is the VLAN tag working, and the
  test that actually distinguishes a correct SSID from a plausible one
- it reaches its gateway, and the internet if that segment is allowed one

An IoT client on `DVNTM-IOT` should land in 10.20.30.0/24. A guest client should land in
10.20.40.0/24 and reach nothing but the internet.

{{< hint info >}}
**A client that associates but gets no lease is almost always the trunk**, not the SSID —
the VLAN is not allowed on `gigabitEthernet 1/0/4`, or DHCP is not serving that segment. See
[troubleshooting](/docs/runbook/network-migration/troubleshooting/#device-not-getting-dhcp-lease).
{{< /hint >}}

---

## Related

- [Access point platform](/docs/platforms/network/access-point/) — what the device is and what it serves
