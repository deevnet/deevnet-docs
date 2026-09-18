---
title: "2. Substrate"
weight: 2
---

# Phase 2: Create the profile and the SSID

**Needs a maintenance window.** This is the only phase that touches a live radio.

Merged: `ansible-collection-deevnet.net` #26, `ansible-inventory-deevnet` #41.

## What changed in inventory

```yaml
  iot:
    # ...
    wifi_ssid: "DVNTM-IOT"
    wifi_security: ppsk
    wifi_ppsk_profile: "DVNTM-IOT"
```

and `deevnet_wifi_psk.iot` was **deleted**. A segment that says nothing about `wifi_security` keeps
a shared key, so the other three wireless segments needed no edit at all — which is what keeps this
change away from `DVNTM`.

## Run

```bash
cd ansible-inventory-deevnet && make unvault
cd ../ansible-collection-deevnet.net
make wireless                 # plan; read the report before going further
make wireless APPLY=1
cd ../ansible-inventory-deevnet && make vault
```

The plan must propose exactly: network VLAN 30, PPSK profile `DVNTM-IOT`, SSID `DVNTM-IOT`. If it
proposes anything else, stop.

## Verify

**From the network, not from Ansible:**

1. Scan on a phone or laptop: **four** SSIDs are broadcast.
2. **On a client already associated to `DVNTM`**, confirm it kept its association and its address.
   Checking the controller is not enough — the risk here is a radio reconfiguration, which the
   controller will happily report as fine.
3. In the controller UI, `DVNTM-IOT` is `security: 4` and bound to the `DVNTM-IOT` profile, and the
   profile holds **no keys**.
4. `make wireless` again reports nothing to create.

## Undo

```
Controller UI → delete the SSID DVNTM-IOT, then the PPSK profile DVNTM-IOT.
git revert the inventory commit (restoring deevnet_wifi_psk.iot), then make vault.
```

Nothing depends on either object until phase 3. The VLAN 30 network object may be left: it is
harmless and the other segments have one.

## Outcome — ran 2026-09-18

**Done, and verified on the controller rather than from Ansible.**

```
PLAY RECAP  dv02nms001v01 : ok=30  changed=0  unreachable=0  failed=0  skipped=8
```

| Object | State after |
|---|---|
| SSID `DVNTM-IOT` | VLAN 30, `security: 4` (PPSK without RADIUS) |
| PPSK profile `DVNTM-IOT` | exists, `type: 0`, bound to that SSID, **0 keys** |
| `DVNTM` | VLAN 10, security 3 — untouched |
| `DVNTM-IOTV` | VLAN 31, security 3 — untouched |
| `DVNTM-GUEST` | VLAN 40, security 3 — untouched |
| AP `dv02wap001p01` | connected |

A second `make wireless` reports `networks_to_create: []`, `ppsk_profiles_to_create: []`,
`ssids_to_create: []` and no drift — so the run is idempotent and the new `security` comparison does
not false-positive on the three shared-key SSIDs.

**The question phase 1 could not answer: this controller ACCEPTS a PPSK profile with an empty key
list.** `POST .../ppsk-profile` with `{"profileName": "DVNTM-IOT", "ppsk": []}` returned
`errorCode 0`, and the seed-and-delete fallback was skipped. The fallback stays in the play — it is
one controller's behaviour, not a documented guarantee, and the schema is silent — but it has never
had to run here.

Both Open API clients were confirmed working beforehand, read-only: Ansible's and the API's own,
each `expiresIn: 7200`. That 2-hour TTL is why the API's token cache matters and why its 10-minute
fallback never fires at this site.

**Did anything drop off `DVNTM`? Unknown, with no sign of trouble.** Worth writing down honestly
rather than recording it as clean.

- The operator was connected independently of the AP for the window, by design, so had no client on
  it to watch. An SSH session surviving would not have settled it either: TCP rides out several
  seconds of radio outage.
- The controller's event log holds **three events in seven days, all `[Device] ap … was
  connected`**, and **none during the apply**. So the AP itself never disconnected from the
  controller — it did not reboot or re-provision at the device level.
- But there are **no `[Client]`-module events at all** in that log, so client association is not
  being recorded at this level. Its silence during the window says nothing about a client blip.

So: positive evidence the AP stayed up, no evidence of a client drop, and no proof there wasn't one.
**If this matters for a future SSID creation, watch a client directly** — the controller log will
not tell you afterwards.

`getEventLogsForSite` is the endpoint, and it needs `filters.timeStart` and `filters.timeEnd` as
epoch milliseconds; both are required.
