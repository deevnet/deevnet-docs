---
title: "Devices & MQTT"
weight: 4
---

# Devices & MQTT {{< status-badge "active" "Available" >}}

## What you get

- A **device registry** — your own inventory of what you have flashed
- A **fixed address** for a device that needs one, and a name for it in your zone
- **MQTT accounts** on the platform broker, each confined to your own topic space

The broker is where devices and workloads meet. Neither connects to the other; both dial out to it.

| | |
|---|---|
| Broker | `mqtt.mobile.deevnet.net`, port **8883**, **TLS only** — nothing listens on 1883 |
| Certificate | chains to the Deevnet Root CA — trust `deevnet-root-ca.pem` |
| Who can reach it | the IoT network (your devices) and tenant networks (your workloads) |
| Your topic space | everything under `<tenant>/` — and nothing else |

## Declare a device and its account

```hcl
resource "deevnet_iot_device" "pico" {
  tenant      = deevnet_tenant.this.name
  name        = "pico-1"
  trust_class = "iot"
  # mac = "28:cd:c1:..."      # optional; needed only for a fixed address, never authorization
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

## A fixed address

A device normally takes whatever address the IoT network's pool gives it. Reserve one when the device
has to be found at the same place every time: it serves a page, or you connect to it.

```hcl
resource "deevnet_iot_device" "pico" {
  tenant      = deevnet_tenant.this.name
  name        = "pico-1"
  trust_class = "iot"
  mac         = "28:cd:c1:00:00:01"   # the board's Wi-Fi MAC; the address is reserved for it
}

resource "deevnet_iot_address" "pico" {
  tenant = deevnet_tenant.this.name
  device = deevnet_iot_device.pico.name
}

output "pico_address" {
  value = {
    address = deevnet_iot_address.pico.address   # e.g. 10.20.30.25
    fqdn    = deevnet_iot_address.pico.fqdn      # pico-1.<tenant>.mobile.deevnet.net
  }
}
```

- **The platform picks the address**, the lowest free one between `10.20.30.25` and `10.20.30.200`.
  Your Terraform state remembers it, so it stays the same. Set `address` yourself to ask for a
  particular one; the apply fails if it is taken
- **The device's name is published for you**: `<device>.<tenant>.mobile.deevnet.net`. Add more names
  for the same address with [`deevnet_dns_record`](/docs/runbook/tenant/services/dns/)
- **The device picks it up over DHCP**, at its next join or lease renewal. Nothing changes in its
  firmware
- **Replaced the board?** Change `mac`. The new board gets the same address
- **You can hold up to 16.** The range is shared by every tenant
- **A MAC that already has an address on the network is refused**, and so is an address that is
  taken. The error does not say who holds it
- **It changes nothing about what can reach the device.** The address is reachable from the
  operator's networks; your workloads still meet your devices at the broker

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
- **Registering a device grants nothing.** The registry is identity only: no address, no DNS name, no
  access. The broker account is what grants access, and [a fixed address](#a-fixed-address) is asked
  for separately
- **No reverse name for a device's address.** The reverse zone of the IoT network is the platform's
