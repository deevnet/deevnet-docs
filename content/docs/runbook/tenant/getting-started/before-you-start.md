---
title: "Before You Start"
weight: 1
---

# Before You Start

## What to bring

| | |
|---|---|
| A laptop | with `git` and **Terraform 1.5 or later** |
| The provider | `deevnet/deevnet` **0.3.x**. It is not on the public registry — see below |
| A repository | somewhere to keep your Terraform. An empty directory is enough to start |
| For devices | a Pico W or ESP32, a USB cable, and Thonny or the Arduino IDE |

From the operator, at [admission](/docs/runbook/tenant/getting-started/admission/):

| | |
|---|---|
| An enrollment token | one-time, bound to your tenant name, valid 72 hours |
| The API endpoint | `https://api.mobile.deevnet.net:8080` |
| The site CA | `site-ca.pem` — the certificate authority for everything Deevnet serves over TLS |

---

## Getting the provider

The provider is built from
[`terraform-provider-deevnet`](https://github.com/deevnet/terraform-provider-deevnet) and installed
into Terraform's **filesystem mirror**, where `terraform init` finds it without a registry:

```bash
git clone https://github.com/deevnet/terraform-provider-deevnet
cd terraform-provider-deevnet
git checkout v0.3.0
make mirror      # installs into ~/.terraform.d/plugins/registry.terraform.io/deevnet/deevnet/0.3.0/<os_arch>/
```

`make mirror` needs Go, and refuses a dirty or untagged tree. On the Builder the mirror is already
populated by the workstation role.

{{< hint info >}}
**Coming soon:** downloading a prebuilt provider from the site's artifact server, so a visitor
needs neither Go nor GitHub on the day.
{{< /hint >}}

---

## Where you need to sit on the network

Terraform talks to the Deevnet API. Which Wi-Fi your laptop is on decides whether it can:

| Your laptop is on | Reaches the API? | Use it for |
|---|---|---|
| **Guest** Wi-Fi | **No** — internet only | reading these docs |
| **IoT** Wi-Fi (`DVNTM-IOT`) | **No** — that is where your *devices* go, not your laptop | nothing |
| **Tenant dev** Wi-Fi (`DVNTM-TD`) | **Yes** — the API, the state store and the broker, and the internet | `terraform plan` / `apply`, MQTT test clients |

**Apply from `DVNTM-TD`, on your own laptop.** Ask the operator for its key. It reaches the three
services your Terraform and test clients use and nothing else on the site, so there is nothing
else to ask for.

`DVNTM-TD` uses the site's own DNS. If your laptop has a VPN, iCloud Private Relay or a hard-coded
DNS server, turn it off, or `api.mobile.deevnet.net` will not resolve.
