---
title: "Wireless AP"
weight: 4
aliases:
  - /docs/runbook/recovery/console-recovery/wireless-ap/
  - /docs/runbook/console-recovery/wireless-ap/
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
| **The firmware chain** | Already mirrored — `http://artifacts.mobile.deevnet.net/firmware/eap650-outdoor/`. See step 4. |

| | |
|---|---|
| Device | `dv02wap001p01`, TP-Link EAP650-Outdoor |
| Managed address | 10.20.99.9, gateway 10.20.99.1 |
| Switch port | `gigabitEthernet 1/0/4` — trunk, native VLAN 99, allowed 10, 30, 31, 40, 99 |
| Controller | Omada, at `https://10.20.99.40:8043` on `dv02nms001v01` |
| Factory / reset address | `10.20.99.9` via DHCP reservation — see below; `192.168.0.254` only as fallback |

{{< hint info >}}
**A reset AP comes back on `10.20.99.9`, because it does DHCP.** A factory-default
EAP650-Outdoor requests DHCP first and only falls back to a static `192.168.0.254` if nothing
answers. OPNsense reserves `40:ED:00:6F:F9:D4 → 10.20.99.9`, so once the reset AP finishes
booting and brings up its DHCP client, Kea hands it that reserved address — its normal managed
address, reached directly, no re-addressing needed. *(Confirmed on the CHG-0005 reset,
2026-09-15: the AP came up `firstLogin: true` on `10.20.99.9` with an active Kea lease.)*

Two wrinkles to expect during the reset:
- **Mid-boot it may briefly sit on `192.168.0.254`** (serving only a `boot` splash page) before
  its DHCP client is up. That is transient; wait for it to finish and it moves to `10.20.99.9`.
- **A factory-default AP serves HTTP, not HTTPS**, until first login is completed; after first
  login it is back on HTTPS.

Only if DHCP does not answer will it stay on `192.168.0.254`, which the management segment does
not route — then give the builder a temporary `192.168.0.1/24` on `enp4s0` to reach it.
{{< /hint >}}

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
| `gigabitEthernet 1/0/16` | 99 access | `dv00bld001p01` — the builder, which runs Ansible and the artifact server |
| `gigabitEthernet 1/0/15` | trunk, native 99 | `dv02hyp001p01` — a trunk since the MQTT broker needed `iot_backend` (35). Not an access port. |

{{< hint warning >}}
**Use 1/0/2, and do not improvise.** `switch_vlans` configures only the ports declared in
`switch_ports` in `host_vars/dv02acc001p01.yml`, and leaves every other port at the switch
default — untagged VLAN 1, which is not in `deevnet_vlans` and is not routed. A laptop in any
other free port gets a link light and nothing else, which reads exactly like a dead switch.

`1/0/2` is declared and held empty for this, and it is the **only** spare untagged-99 port on
the switch. `1/0/15` stopped being an access port when the MQTT broker needed `iot_backend`,
which leaves `1/0/16` as the only other one — and that is the builder. Borrowing it would take
Ansible and the artifact server off the network at the moment you need them.
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

OPNsense runs Kea DHCP on VLAN 99. Inventory declares a pool of `10.20.99.200–230` on it
(`group_vars/all/vlans.yml`, marked temporary), and the `opnsense_dhcp` role creates the subnet
from that. Infrastructure on the segment gets static addresses or reservations. A wired laptop
should therefore get a lease. If it doesn't, set an address by hand from outside the pool and the
reserved addresses:

```bash
sudo ip addr add 10.20.99.50/24 dev <iface>
sudo ip route add default via 10.20.99.1
```

Confirm the path before going further — if these fail, the fault is the switch or the router,
not the AP:

```bash
ping -c2 10.20.99.1          # core router
curl -k https://10.20.99.40:8043/api/info   # Omada controller on dv02nms001v01
```

---

## 2. Check the port before resetting the AP

The AP is on a trunk. If its native VLAN or allowed list has drifted, the AP will look dead
while being perfectly healthy — and resetting it will not help.

```
show interface switchport gigabitEthernet 1/0/4
```

Native VLAN 99 with 10, 30, 31, 40 and 99 allowed. If that is wrong, fix the switch — see
[access switch](/docs/runbook/substrate/recovery/console-recovery/access-switch/) — and stop here.

---

## 3. Reset

Press and hold the reset button until the AP restarts.

Confirm the reset took, then find the AP. The reset wipes the managed address, so it briefly
drops off `10.20.99.9`, then **comes back on `10.20.99.9` via its DHCP reservation** once it has
finished booting. Watch for it to drop and return:

```bash
# during the reset 10.20.99.9 goes dark for ~1 min, then returns as a DHCP lease
ping -c2 10.20.99.9
```

If it does not come back on `10.20.99.9` (no DHCP answer), it is on the static fallback
`192.168.0.254`, which the management segment does not route — give the builder a temporary
address in that subnet, on the same broadcast domain (untagged VLAN 99):

```bash
sudo ip addr add 192.168.0.1/24 dev enp4s0      # remove it once the AP is adopted
```

A factory-default AP serves **HTTP** and forces a first-login account. Log in with
`admin`/`admin`, set the admin account, and **record it in the vault as
`vault_wap_standalone_user` / `vault_wap_standalone_password`** in
`group_vars/network_controllers/vault.yml` — adoption asks for it.

---

## 4. Upgrade the firmware before adopting

Do this while the AP is still standalone. Adoption replaces its configuration with the
controller's, and a controller several years newer than the AP's firmware is the combination
that mis-provisions VLAN-tagged SSIDs — the problem [step 6](#6-reapply-the-ssids) exists to
work around. Arriving at adoption on current firmware is what removes it.

Outside a recovery, `dv02wap001p01`'s upgrade is planned as phase 2 of [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/): the
same chain, applied in place without a reset, ahead of adopting the AP.

{{< hint danger >}}
**This is a chain, not a step, and one hop is irreversible.** Every build since 1.2.x declares
a minimum prior version, so an AP on the 2023 firmware cannot jump to current:

| Target | Requires first | |
|---|---|---|
| `1.2.5 Build 20250321` | — | |
| `1.3.3 Build 20251111` | 1.2.0 | **irreversible** — TP-Link state a downgrade needs their support |
| `1.3.11 Build 20260703` | 1.3.1 | |

Each hop reboots the AP. Wireless is already down from the reset in step 3 and stays down
until step 6 — do not start this without being on the cable from
[step 1](#1-get-onto-the-management-network-by-wire).
{{< /hint >}}

The files are mirrored on the artifact server, so no hop depends on TP-Link being reachable
(`artifacts_to_fetch` in `group_vars/artifact_servers.yml` pins each one's sha256):

```
http://artifacts.mobile.deevnet.net/firmware/eap650-outdoor/
```

Take the `.bin`, not the `.zip` — the AP's web UI wants the payload, and the extracted
`EAP650-Outdoorv1_<ver>_[<build>]_up_signed.bin` files are served alongside the archives. The
`v1` in the name is the hardware match for EAP650-Outdoor(US) v1.0; TP-Link's own page notes
`Vx.0 = Vx.6/Vx.8`, so a file labeled V1.6 is correct for this unit.

### Reaching the AP to upload

The builder can see the AP on either address and is itself the artifact server, so forward both
through it in one go rather than re-addressing the machine running the browser:

```bash
# AP on its DHCP reservation (the normal case):
ssh -L 8443:10.20.99.9:443 -L 8080:10.20.99.95:80 cdeever@10.20.99.95
# AP on the static fallback (needs the builder's 192.168.0.1/24 from step 3):
ssh -L 8443:192.168.0.254:443 -L 8080:10.20.99.95:80 cdeever@10.20.99.95
```

Forward `:80` rather than `:443` for a freshly reset AP that has not completed first login.

Then browse `https://localhost:8443` and upload under **System → Firmware Update**, taking the
files from `http://localhost:8080/firmware/eap650-outdoor/`. Download each `.bin` to the machine
running the browser first; the AP has no route to the artifact server, so the upload comes off
the browser's own disk.

### Between each hop

The AP reboots and returns to whichever address it was on. Confirm the version actually moved before
starting the next one — a failed flash that silently keeps the old image turns the next hop
into a rejected upload rather than a bricked AP, but only if you notice:

**Status → Device Information → Firmware Version**

Expected sequence: `1.0.4` → `1.2.5` → `1.3.3` → `1.3.11`.

---

## 5. Re-adopt into Omada

The AP and the controller both sit on VLAN 99, so Omada's L2 discovery normally finds it with
no inform URL set. If it does not appear, set the AP's **inform URL** to `https://10.20.99.40`
— **not** the builder, whose controller is a deliberately stopped cold spare. Then adopt it at
`https://10.20.99.40:8043`. The full sequence is in
[Omada device adoption](/docs/changes/2026/0001-flat-network-to-vlans/port-migration/#step-12-omada-device-adoption).

Remove the temporary address from the builder once the AP is reachable on the management
segment:

```bash
sudo ip addr del 192.168.0.1/24 dev enp4s0
```

---

## 6. Reapply the SSIDs

The controller provisions all four SSIDs. Since
[CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) the AP runs firmware the controller can configure
([current version](/docs/platforms/software-catalog/#switching-wireless-and-edge)) and is adopted, so nothing here is configured in the AP's standalone UI — that route was only ever a
workaround for firmware 1.0.4, which Omada would not push VLAN configuration to.

From `ansible-collection-deevnet.net`, with the inventory vault decrypted:

```bash
make wireless                    # plan; read the report first
make wireless APPLY=1 ADOPT=1    # adopt a pending AP, then apply
make wireless APPLY=1            # once adopted: SSIDs, profiles, networks
```

SSIDs map to the VLANs the trunk allows — `DVNTM` onto 10, `DVNTM-IOT` onto 30, `DVNTM-IOTV` onto 31
and `DVNTM-GUEST` onto 40. The authoritative list is `deevnet_vlans` in inventory; the security model
for each is on the
[access point](/docs/platforms/network/access-point/) page.

{{< hint info >}}
**Recovery does not re-issue tenant keys.** `DVNTM-IOT` is a PPSK SSID, and the per-tenant keys live
in its PPSK profile on the controller — not on the AP. Rebuilding or re-adopting the AP does not
touch them, so no device needs reflashing.

If the **profile itself** is lost, the SSID comes back empty and each tenant runs one
`terraform apply`, which restores **the same key it already holds** — the tenant's state is the
authoritative copy ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §5). Still no
device visit. Do not hand-create keys in the controller UI to "fix" this: the API owns them, and a
hand-made key is one nothing will ever clean up.
{{< /hint >}}

---

## 7. Verify

Per SSID, from a client:

- it associates
- it receives a lease from the **expected** subnet — that is the VLAN tag working, and the
  test that actually distinguishes a correct SSID from a plausible one
- it reaches its gateway, and the internet if that segment is allowed one

A guest client should land in 10.20.40.0/24 and reach nothing but the internet.

**`DVNTM-IOT` needs a tenant's key to test**, since it has no shared one: take `ssid` and `psk` from
a tenant's `device_wifi` output. A client joining with it should land in 10.20.30.0/24 — and landing
there is the per-key VLAN binding working, which is the thing worth checking. Confirm the SSID
broadcasts and that its PPSK profile is bound to it; the keys inside the profile are the API's and
are not part of this check.

{{< hint info >}}
**A client that associates but gets no lease is almost always the trunk**, not the SSID —
the VLAN is not allowed on `gigabitEthernet 1/0/4`, or DHCP is not serving that segment. See
[troubleshooting](/docs/changes/2026/0001-flat-network-to-vlans/troubleshooting/#device-not-getting-dhcp-lease).
{{< /hint >}}

---

## Related

- [Access point platform](/docs/platforms/network/access-point/) — what the device is and what it serves
