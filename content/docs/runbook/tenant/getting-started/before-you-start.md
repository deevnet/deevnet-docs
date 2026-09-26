---
title: "Before You Start"
weight: 1
---

# Before You Start

## What to bring

**A Mac or a Linux laptop, and your own SD card** if you'll take your backend home. Everything
below can be installed before the meetup. At the meetup, the provider, Terraform, Pi Imager,
MicroPython and the take-home image come from the site's
[tenant downloads](#tenant-downloads) rather than the venue's internet.

From the operator, at [admission](/docs/runbook/tenant/getting-started/admission/):

| | |
|---|---|
| An enrollment token | one-time, bound to your tenant name, valid 72 hours |
| The API endpoint | `https://api.mobile.deevnet.net:8080` |
| The `DVNTM-TD` Wi-Fi key | the network you work from ([below](#where-you-need-to-sit-on-the-network)) |
| The site CA | `site-ca.pem`, the certificate authority for everything Deevnet serves over TLS. Check its SHA-256 fingerprint: `ED:ED:43:04:B8:40:8A:CE:14:FE:B8:AB:6C:B6:43:BC:A5:56:84:E8:26:A3:C2:75:CD:BD:EB:70:DF:E5:2D:5C` |

---

## Tools

**Required** to apply your Terraform:

| Tool | Why | macOS | Fedora | Debian / Ubuntu |
|---|---|---|---|---|
| `git` | your repository | `xcode-select --install` | `sudo dnf install git` | `sudo apt install git` |
| Terraform ≥ 1.5 | applies your tenant | `brew install hashicorp/tap/terraform` | from [tenant downloads](#tenant-downloads) `terraform/`, or HashiCorp's repo | the same |
| `deevnet/deevnet` provider **0.4.x** | the Deevnet resources | [install-provider.sh](#getting-the-provider) | the same | the same |
| `curl`, `openssl` | TLS checks, the CA | built in | `sudo dnf install curl openssl` | `sudo apt install curl openssl` |

**For devices:**

| Tool | Why | macOS | Fedora | Debian / Ubuntu |
|---|---|---|---|---|
| `mosquitto_pub`, `mosquitto_sub` | MQTT test clients | `brew install mosquitto` | `sudo dnf install mosquitto` | `sudo apt install mosquitto-clients` |
| `mpremote` | copies files to a Pico | `python3 -m pip install --user mpremote` | the same | the same |
| MicroPython ≥ 1.23 for the Pico W | the Pico's firmware | from [tenant downloads](#tenant-downloads) `tools/` | the same | the same |
| Thonny *or* the Arduino IDE with PubSubClient | editing firmware (Pico / ESP32) | thonny.org / arduino.cc | the same | the same |
| `dig`, `python3` | name checks, scripting | `brew install bind`; `python3` built in | `sudo dnf install bind-utils python3` | `sudo apt install dnsutils python3` |

Plus the board itself (a Pico W or an ESP32) and a USB **data** cable.

**To [take it home on a Pi](/docs/runbook/tenant/take-it-home/):**

| Tool | Why | macOS | Fedora | Debian / Ubuntu |
|---|---|---|---|---|
| Raspberry Pi Imager and an SD card reader | flashes your card | from [tenant downloads](#tenant-downloads) `tools/` (`.dmg`) | Imager from `tools/` (`.deb`) or Flathub | `.deb` from `tools/` |
| An SSH client | reaches the Pi | built in | built in | built in |
| `.local` names | `<hostname>.local` | built in | `sudo dnf install nss-mdns avahi` | `sudo apt install libnss-mdns avahi-daemon` |
| Podman or Docker with arm64 builds | builds your app for the Pi | `brew install podman` | `sudo dnf install podman qemu-user-static` | `sudo apt install podman qemu-user-static` |

### Check your laptop

`tenant-check.sh` checks all of the above. For each missing tool it prints the command that installs
it on your laptop. Run it at home with `--offline`; on `DVNTM-TD` it also checks every service you'll
use:

```bash
bash tenant-check.sh --offline      # at home: the tools only
bash tenant-check.sh                # on DVNTM-TD: tools and the site's services
```

It is in [tenant downloads](#tenant-downloads) `scripts/`, and attached to every
[provider release](https://github.com/deevnet/terraform-provider-deevnet/releases).

---

## Tenant downloads

**At the site**, on `DVNTM-TD`, everything above that isn't a package-manager install is served
at **`https://downloads.mobile.deevnet.net:8443/`**. It is read-only and verified with the site CA
([CHG-0025](/docs/changes/2026/0025-tenant-downloads/)):

| Path | What |
|---|---|
| `site-ca.pem` | the site CA. Check its fingerprint against the one above before trusting it |
| `scripts/` | `install-provider.sh`, `tenant-check.sh` |
| `provider/<version>/` | the deevnet provider for macOS and Linux, Intel and ARM, with `SHA256SUMS` |
| `providers/grafana/<version>/` | the Terraform `grafana` provider, for [dashboards](/docs/runbook/tenant/services/dashboards/) |
| `terraform/<version>/` | Terraform itself |
| `tools/` | Raspberry Pi Imager (macOS, Linux) and MicroPython for the Pico W |
| `pi/` | the [take-home](/docs/runbook/tenant/take-it-home/) Pi image and its sha256 |

---

## Getting the provider

The provider isn't on the public registry. It goes into Terraform's local mirror
(`~/.terraform.d/plugins/…`), where `terraform init` finds it. **At the site:**

```bash
curl -fsSLk -o site-ca.pem https://downloads.mobile.deevnet.net:8443/site-ca.pem
openssl x509 -in site-ca.pem -noout -fingerprint -sha256     # must match the fingerprint above
curl -fsSL --cacert site-ca.pem -O https://downloads.mobile.deevnet.net:8443/scripts/install-provider.sh
bash install-provider.sh
```

It installs `deevnet/deevnet` **and** the `grafana` provider, and checks every download against
its `SHA256SUMS`. **Off-site,** `bash install-provider.sh --github` fetches the same prebuilt
provider from the
[GitHub release](https://github.com/deevnet/terraform-provider-deevnet/releases). **From
source** (needs Go and make): clone the repository, check out the latest tag
(`git checkout "$(git describe --tags --abbrev=0)"`), then `make mirror`.

Pin it in your configuration:

```hcl
deevnet = {
  source  = "deevnet/deevnet"
  version = "~> 0.4"
}
```

---

## Where you need to sit on the network

Terraform talks to the Deevnet API. Which Wi-Fi your laptop is on decides whether it can:

| Your laptop is on | Reaches the API? | Use it for |
|---|---|---|
| **Guest** Wi-Fi | **No** — internet only | reading these docs |
| **IoT** Wi-Fi (`DVNTM-IOT`) | **No** — that is where your *devices* go, not your laptop | nothing |
| **Tenant dev** Wi-Fi (`DVNTM-TD`) | **Yes** — the tenant-facing services and the internet | `terraform plan` / `apply`, MQTT test clients |

**Apply from `DVNTM-TD`, on your own laptop.** Ask the operator for its key. It reaches the
services your Terraform, test clients and browser use (the API, the state store, the broker, the
log store, Grafana and the tenant downloads) and nothing else on the site.

`DVNTM-TD` uses the site's own DNS. If your laptop has a VPN, iCloud Private Relay or a hard-coded
DNS server, turn it off, or `api.mobile.deevnet.net` will not resolve.
