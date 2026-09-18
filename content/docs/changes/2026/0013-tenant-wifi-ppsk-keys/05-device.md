---
title: "5. Device"
weight: 5
---

# Phase 5: A device joins

**Needs an operator at the site.** Everything before this is remote.

## Run

The firmware already expects this SSID — `CONFIG_LP_WIFI_SSID` in
`/srv/eds/firmware/lp-stand/main/Kconfig.projbuild` defaults to `DVNTM-IOT`. Nothing in the firmware
changes; only the two Kconfig values are set from phase 4's output.

```bash
cd /srv/eds/firmware/lp-stand
idf.py menuconfig     # LP jacket stand -> Network -> WiFi SSID / WiFi password
idf.py flash monitor
```

## Verify

**From the network:**

1. OPNsense's lease table shows the stand in `10.20.30.0/24`.
2. The controller's client list shows it associated to `DVNTM-IOT`, on VLAN 30.
3. The serial monitor shows it obtaining an address.

It will then fail to reach a broker, because there is no broker. That is expected and is not part of
this change.

## Undo

Reflash the previous configuration. Nothing depends on the stand.
