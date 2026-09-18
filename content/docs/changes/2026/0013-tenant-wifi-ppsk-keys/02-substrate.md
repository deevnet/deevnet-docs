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

## Record here when it runs

- [ ] Did the controller accept a PPSK profile with an **empty** key list, or did the play fall back
      to the seed-and-delete path? (The play says so in its output.) This answers the one question
      phase 1 could not.
- [ ] Did any client drop, and for how long?
