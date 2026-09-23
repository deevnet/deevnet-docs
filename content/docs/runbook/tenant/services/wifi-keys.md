---
title: "Wi-Fi Keys"
weight: 3
---

# Wi-Fi Keys {{< status-badge "active" "Available" >}}

## What you get

A **Wi-Fi key of your own** on the site's IoT SSID. Devices that join with it land on the IoT
network (VLAN 30, `10.20.30.0/24` at the mobile site), where they can reach the MQTT broker and the
internet — and nothing else: not your workloads, not the management network, not other tenants'
services.

The SSID is shared; the **key** is yours. The access point uses per-key passphrases (PPSK), so your
key identifies your devices as yours, and revoking it disconnects only yours.

## Declare one

```hcl
resource "deevnet_iot_wifi_key" "devices" {
  tenant      = deevnet_tenant.this.name
  name        = "devices"
  trust_class = "iot"
}

output "device_wifi" {
  value     = { ssid = deevnet_iot_wifi_key.devices.ssid, psk = deevnet_iot_wifi_key.devices.psk }
  sensitive = true
}
```

```bash
terraform output -json device_wifi
```

**One key per tenant per trust class**, not per device: every device you flash uses the same key.
Read the SSID from the output rather than hardcoding `DVNTM-IOT` — the same trust class is
`DVNT-IOT` at the home site.

| Trust class | For | Available at mobile |
|---|---|---|
| `iot` | devices you build and flash yourself | yes |
| `iot_vendor` | commercial devices that phone home to a vendor cloud | not configured |

## Rotating it

```bash
terraform apply -replace=deevnet_iot_wifi_key.devices
```

issues a new key, and **every device holding the old one drops off** until it is reflashed. The
`psk` is only ever returned when the key is issued — your state is its only copy.

## What it does not do

- **It is not authorization.** Joining the network proves you have the key, nothing more; each
  service still wants its own credential (the broker wants a broker account)
  ([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/))
- **Your devices cannot reach your workloads directly.** Both talk to the broker
- **Known defect:** on a *freshly built* site whose key profile started empty, the first key issued
  does not authenticate. The mobile site is past this; it matters only after a site rebuild
