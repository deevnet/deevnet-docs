---
title: "Project Kits"
weight: 6
---

# Project Kits

A **project kit** is a microcontroller project that comes pre-wired and already running reference
firmware. You borrow one at a meetup, it joins **your** tenant, and you see it working in minutes
instead of an evening of wiring. Then you change it: the firmware is a starting point, not the
project.

The kits themselves, what's in them, how they're wired and their reference firmware, belong to
[CARPE](https://carpe-tech.org/): the kit list is on CARPE's
[Hands-On](https://carpe-tech.org/hands-on/) page, and wiring and firmware live in the
[carpe-tech](https://github.com/carpe-tech) GitHub organisation. This page is the Deevnet side: how
any kit is borrowed into your tenant and handed back.

{{< hint info >}}
Not this page: a **bank Pi** to develop on is the [Pi Lab](/docs/runbook/tenant/pi-lab/), and taking
your backend home on a Pi of your own is [Take it home on a Pi](/docs/runbook/tenant/take-it-home/).
A project kit is also not the *mobile kit* (the platform in the toolkit base) or `deevnet-kit` (the
take-home Pi's tooling).
{{< /hint >}}

---

## Borrowing a kit

A kit is an ordinary device in your tenant. Nothing about it is special to Deevnet, so it is
declared the way [Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/) and the
[walkthrough](/docs/runbook/tenant/walkthrough-mqtt-device/) describe:

1. **Your tenant's Wi-Fi key**: `deevnet_iot_wifi_key`, one per tenant and trust class
   ([Wi-Fi Keys](/docs/runbook/tenant/services/wifi-keys/)). If your own devices already use it, the
   kit uses the same one
2. **A device and a broker account** for the kit: `deevnet_iot_device` and
   `deevnet_iot_broker_account`, then `terraform apply`
3. **The credentials onto the kit**: the Wi-Fi key and the broker username and password, the way the
   kit's own instructions say

From then on the kit publishes under your tenant-relative topics, logs to `<tenant>/log/<device>`
([Logs](/docs/runbook/tenant/services/logs/)), and shows up in your
[dashboards](/docs/runbook/tenant/services/dashboards/). Nothing is hand-issued: the kit is in your
Terraform like everything else you own.

## Making it yours

The reference firmware shows the kit working. Reflash it with your own code and keep the same
account: the broker cares about the username and password, not which firmware sent them. If you
break it, the kit's reference firmware is in its repository to flash back.

## Handing it back

1. **Remove the kit** from your Terraform (its device and broker account) and `terraform apply`
2. **Power-cycle or wipe the kit.** Deleting an account blocks the *next* connection, not the one
   already open ([Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/#credentials))

A returned kit carries nothing of yours: its credentials no longer work, and the next borrower
declares it in their own tenant.

## Kits and the Pi bank

| | Bank Pi | Project kit |
|---|---|---|
| **Whose** | Deevnet's, carries the automation user | A device in your tenant |
| **What you get** | A Pi to develop on | A working project to change |
| **What you keep** | The SD card | Your firmware and your Terraform |

A kit's topics and account work against a [take-home Pi](/docs/runbook/tenant/take-it-home/) too,
so a project built on a borrowed kit goes home the same way as one built on your own devices.

## Not built yet {{< status-badge "planned" "Planned" >}}

- **Credentials without a reflash.** Getting your Wi-Fi key and account onto a kit that is already
  flashed, for example a provisioning mode or a config file, is up to each kit's firmware; there is
  no common way yet
- **A kit in one block.** A Terraform module that declares a kit's device, account and topics
  together
