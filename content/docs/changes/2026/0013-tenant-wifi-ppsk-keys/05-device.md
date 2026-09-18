---
title: "5. A client joins"
weight: 5
---

# Phase 5: A client joins with a tenant's key

**Needs someone at the site with a wireless client.** Everything before this is remote.

What this phase proves is narrow and worth stating: **that a tenant's key authenticates, and that
the key decides the VLAN.** Any wireless client does that. It does not have to be the device the
tenant will eventually run.

## Run

Get the credential from the tenant, not from the controller:

```bash
cd /srv/eds/infra/deevnet-tenant-eds
terraform output -json device_wifi     # ssid, psk, vlan
```

Then join `DVNTM-IOT` with it, from a laptop, a phone, or the LP stand:

```bash
# the stand, when one is to hand
cd /srv/eds/firmware/lp-stand
idf.py menuconfig     # LP jacket stand -> Network -> WiFi SSID / WiFi password
idf.py flash monitor
```

The firmware needs no code change: `CONFIG_LP_WIFI_SSID` already defaults to `DVNTM-IOT`.

## Verify

**From the network:**

1. The client associates with the tenant's key — and **only** with it. `DVNTM-IOT` has no shared
   key, so a wrong password is a clean failure.
2. It takes a lease in **`10.20.30.0/24`**. That is the per-key VLAN binding working, and it is the
   whole point of the phase: nothing about the SSID says VLAN 30 for this client, the key does.
3. The controller's client list shows it on `DVNTM-IOT`.

## Undo

Disconnect, or reflash the previous configuration. Nothing depends on the client.

---

## What this phase does NOT prove, and one trap

**A device reaching a tenant's workload is not this test, and would pass for the wrong reason
today.** It is tempting to join `DVNTM-IOT` and then curl a tenant service — say
`services.eds.mobile.deevnet.net` on 10.20.130.10, which
[CHG-0012](/docs/changes/2026/0012-operator-access-to-tenants/) made reachable. That will work right
now, and it proves nothing good:

- It works because **[CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) has never run**, so
  the core router passes everything between zones. CHG-0012's declared rules let `management` and
  `trusted` use the tenant route — **not `iot`**. So the moment the zone policy is enforced, that
  same test fails, correctly.
- It is also not the intended path. Under
  [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) a device is
  *platform-attached*, not a member of its owner's fabric: it talks to the **broker** on IoT
  Backend, and the broker talks to the tenant's workloads. A device reaching a tenant VM directly
  crosses a boundary the model deliberately does not draw.

So if you run it, read the result as **a demonstration that the zone policy is still missing**,
which is CHG-0007's job, not as a Wi-Fi or tenant-isolation success. The Wi-Fi result is step 2
above: the lease in 10.20.30.0/24.

**The end-to-end vertical is blocked elsewhere.** A joined stand has nothing to talk to — VerneMQ on
`dv02msg001v01` is built and empty. Packaging the eds services and standing up the broker are their
own effort, not this change.