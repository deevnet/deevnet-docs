---
title: "Wireless AP"
weight: 4
---

# Wireless AP

Recovering `dv02wap001p01` when it stops answering at 10.20.99.9 or its SSIDs stop serving
the right VLANs — by factory reset, re-adoption, and reapplying its wireless configuration.

Losing the AP is the least disruptive failure in this section. Nothing wired depends on it,
so the site keeps running while you work.

## What you need

| | |
|---|---|
| **Access** | Physical, to press and hold the reset button. |
| **A laptop** | To reach the AP on its factory address. |
| **A patch cable** | Only if you cannot reach it over the wire once reset. |

| | |
|---|---|
| Device | `dv02wap001p01`, TP-Link EAP650-Outdoor |
| Managed address | 10.20.99.9, gateway 10.20.99.1 |
| Switch port | `gigabitEthernet 1/0/4` — trunk, native VLAN 99, allowed 10, 30, 31, 40, 99 |
| Controller | Omada, at `https://10.20.99.95:8043` on `dv00bld001p01` |
| Factory address | `192.168.0.254`, `admin`/`admin` — static, **not** DHCP |

---

## 1. Check the port before resetting the AP

The AP is on a trunk. If its native VLAN or allowed list has drifted, the AP will look dead
while being perfectly healthy — and resetting it will not help.

```
show interface switchport gigabitEthernet 1/0/4
```

Native VLAN 99 with 10, 30, 31, 40 and 99 allowed. If that is wrong, fix the switch — see
[access switch](/docs/runbook/console-recovery/access-switch/) — and stop here.

---

## 2. Reset

Press and hold the reset button until the AP restarts.

A factory-reset EAP does **not** take a DHCP lease. It comes up on a static
`192.168.0.254/24`, which is why a laptop or a temporary address on the builder is needed to
reach it:

```bash
sudo ip addr add 192.168.0.1/24 dev enp4s0
```

Then browse to `http://192.168.0.254` with `admin`/`admin`.

---

## 3. Re-adopt into Omada

Set the AP's **inform URL** to the controller so it can be discovered, then adopt it at
`https://10.20.99.95:8043`. The full sequence is in
[Omada device adoption](/docs/runbook/network-migration/port-migration/#step-12-omada-device-adoption).

Remove the temporary address from the builder once the AP is reachable on the management
segment:

```bash
sudo ip addr del 192.168.0.1/24 dev enp4s0
```

---

## 4. Reapply the SSIDs

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

## 5. Verify

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
