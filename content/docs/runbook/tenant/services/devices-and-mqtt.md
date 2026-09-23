---
title: "Devices & MQTT"
weight: 4
---

# Devices & MQTT {{< status-badge "active" "Available" >}}

## What you get

- A **device registry** — your own inventory of what you have flashed
- **MQTT accounts** on the platform broker, each confined to your own topic space

The broker is where devices and workloads meet. Neither connects to the other; both dial out to it.

| | |
|---|---|
| Broker | `mqtt.mobile.deevnet.net`, port **8883**, **TLS only** — nothing listens on 1883 |
| Certificate | issued by the site CA — trust `site-ca.pem` |
| Who can reach it | the IoT network (your devices) and tenant networks (your workloads) |
| Your topic space | everything under `<tenant>/` — and nothing else |

## Declare a device and its account

```hcl
resource "deevnet_iot_device" "pico" {
  tenant      = deevnet_tenant.this.name
  name        = "pico-1"
  trust_class = "iot"
  # mac = "28:cd:c1:..."      # optional; recorded, never used as authorization
}

resource "deevnet_iot_broker_account" "pico" {
  tenant = deevnet_tenant.this.name
  name   = "pico-1"
  device = deevnet_iot_device.pico.name

  # Relative to your tenant: the API adds the "<tenant>/" prefix itself.
  publish   = ["sensors/pico-1/telemetry", "log/pico-1"]
  subscribe = ["sensors/pico-1/command"]
}

output "pico_mqtt" {
  value = {
    username = deevnet_iot_broker_account.pico.username   # "<tenant>-pico-1"
    password = deevnet_iot_broker_account.pico.password
    publish  = deevnet_iot_broker_account.pico.granted_publish
  }
  sensitive = true
}
```

A **workload's** account is the same resource without `device`:

```hcl
resource "deevnet_iot_broker_account" "backend" {
  tenant    = deevnet_tenant.this.name
  name      = "backend"
  subscribe = ["sensors/+/telemetry", "log/#"]
  publish   = ["sensors/+/command"]
}
```

`granted_publish` and `granted_subscribe` show what the broker actually enforces, prefix included —
`bench1/sensors/pico-1/telemetry`, not `sensors/pico-1/telemetry`. **Devices publish to the full
topic.**

## Topic rules

- Patterns are relative to your tenant. A leading `/`, a `$` or `%`, or a `#` anywhere but the end
  is refused with a 400
- **`log/` is reserved for device logs** (see [Logs](/docs/runbook/tenant/services/logs/)):
  - a **device** account may publish only `log/<its own device name>`, and may not subscribe under
    `log/`
  - a **workload** account may not publish under `log/`, but may subscribe to your tenant's
  - wildcards that reach into `log/` from a device account (`#`, `+/pico-1`) are refused
- At least one of `publish` and `subscribe` is required

## Credentials

- The **username** is `<tenant>-<name>`. The **password** is returned once, when the account is
  created; the API keeps only a hash, so your state is the only copy
- `terraform apply -replace=deevnet_iot_broker_account.pico` issues a new password; the device needs
  reflashing
- Deleting an account blocks the **next** connection, not the one already open

## What it does not do

- **No broker address from the API.** The hostname is not an attribute yet; hardcode
  `mqtt.mobile.deevnet.net:8883`
- **Not bound to a client id.** Any client id works with your account. Choose a stable, unique one
  per device anyway — the broker drops an older connection that reuses a client id
- **Registering a device grants nothing.** The registry is identity only: no DHCP reservation, no DNS
  name, no access. The broker account is what grants access
