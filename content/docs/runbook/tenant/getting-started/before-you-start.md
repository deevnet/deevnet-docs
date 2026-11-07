---
title: "Before You Start"
weight: 1
---

# Before You Start

Three things come before your first apply: a development environment with the tools installed, the
few things the operator gives you at [admission](/docs/runbook/tenant/getting-started/admission/),
and a Wi-Fi connection to the tenant development network.

## Your development environment

- **A computer running macOS, Linux or Windows 10 or 11, with Wi-Fi.** Tenants reach Deevnet over
  Wi-Fi only (see [Connecting](#connecting-wi-fi-only)). Windows works two ways, natively in
  PowerShell or under WSL2 ([Working from Windows](#working-from-windows)).
- **For devices:** the board itself (a Pico W or an ESP32) and a USB **data** cable.
- **To move your tenant onto a Pi of your own:** a Raspberry Pi, a microSD card of 8 GB or more, and
  a card reader.

Everything under [Tools](#tools) can be installed before you reach the site. The provider,
Terraform, Pi Imager, MicroPython and the Pi image are also served on the site's own
[tenant downloads](#tenant-downloads), so they don't depend on the internet connection there.

---

## Tools

**Required** to apply your Terraform:

| Tool | Why | macOS | Fedora | Debian / Ubuntu | Windows |
|---|---|---|---|---|---|
| `git` | your repository | `xcode-select --install` | `sudo dnf install git` | `sudo apt install git` | `winget install Git.Git` |
| Terraform ≥ 1.5 | applies your tenant | `brew install hashicorp/tap/terraform` | from [tenant downloads](#tenant-downloads) `terraform/`, or HashiCorp's repo | the same | `winget install Hashicorp.Terraform`, or from `terraform/` |
| `deevnet/deevnet` provider **0.9.x** | the Deevnet resources | [install-provider.sh](#getting-the-provider) | the same | the same | [install-provider.ps1](#getting-the-provider) |
| `curl`, `openssl` | TLS checks, the CA | built in | `sudo dnf install curl openssl` | `sudo apt install curl openssl` | `curl.exe` built in; no `openssl` needed |

**For devices:**

| Tool | Why | macOS | Fedora | Debian / Ubuntu | Windows |
|---|---|---|---|---|---|
| `mosquitto_pub`, `mosquitto_sub` | MQTT test clients | `brew install mosquitto` | `sudo dnf install mosquitto` | `sudo apt install mosquitto-clients` | `winget install EclipseFoundation.Mosquitto`, then add `C:\Program Files\mosquitto` to `PATH` |
| `mpremote` | copies files to a Pico | `python3 -m pip install --user mpremote` | the same | the same | `python -m pip install --user mpremote` |
| MicroPython ≥ 1.23 for the Pico W | the Pico's firmware | from [tenant downloads](#tenant-downloads) `tools/` | the same | the same | the same |
| Thonny *or* the Arduino IDE with PubSubClient | editing firmware (Pico / ESP32) | thonny.org / arduino.cc | the same | the same | the same |
| `dig`, `python3` | name checks, scripting | `brew install bind`; `python3` built in | `sudo dnf install bind-utils python3` | `sudo apt install dnsutils python3` | `Resolve-DnsName` built in; `winget install Python.Python.3.12` |

**To [convert your tenant to a Pi image](/docs/runbook/tenant/tenant-to-pi-image/):**

| Tool | Why | macOS | Fedora | Debian / Ubuntu | Windows |
|---|---|---|---|---|---|
| Raspberry Pi Imager and an SD card reader | flashes your card | from [tenant downloads](#tenant-downloads) `tools/` (`.dmg`) | Imager from `tools/` (`.deb`) or Flathub | `.deb` from `tools/` | `.exe` from `tools/` |
| An SSH client | reaches the Pi | built in | built in | built in | built in (OpenSSH) |
| `.local` names | `<hostname>.local` | built in | `sudo dnf install nss-mdns avahi` | `sudo apt install libnss-mdns avahi-daemon` | built in |
| Podman or Docker with arm64 builds | builds your app for the Pi | `brew install podman` | `sudo dnf install podman qemu-user-static` | `sudo apt install podman qemu-user-static` | `winget install RedHat.Podman`, then `podman machine init` |

### Check your development environment

`tenant-check.sh` checks all of the above. For each missing tool it prints the command that installs
it on your computer. Run it anywhere with `--offline`; on `DVNTM-TD` it also checks every service
you'll use:

```bash
bash tenant-check.sh --offline      # anywhere: the tools only
bash tenant-check.sh                # on DVNTM-TD: tools and the site's services
```

On Windows, `tenant-check.ps1` does the same and prints `winget` lines. Under WSL2, run
`tenant-check.sh`, which also checks WSL's networking:

```powershell
powershell -ExecutionPolicy Bypass -File tenant-check.ps1 -Offline
powershell -ExecutionPolicy Bypass -File tenant-check.ps1
```

Both are in [tenant downloads](#tenant-downloads) `scripts/`, and attached to every
[provider release](https://github.com/deevnet/terraform-provider-deevnet/releases).

---

## What the operator gives you

At [admission](/docs/runbook/tenant/getting-started/admission/):

| | |
|---|---|
| An enrollment token | one-time, bound to your tenant name, valid 72 hours |
| The API endpoint | `https://api.mobile.deevnet.net` |
| The `DVNTM-TD` Wi-Fi key | the network you work from ([below](#connecting-wi-fi-only)) |
| The Deevnet Root CA | the certificate authority everything this site serves over TLS chains to: one for every Deevnet site, the same for every tenant (`O=Deevnet, OU=Deevnet PKI, CN=Deevnet Root CA`). You download it, and keep it, as **`deevnet-root-ca.pem`**. Your tools and apps name it through a variable (`DEEVNET_API_CACERT`, `MQTT_CA_FILE`, `GRAFANA_CA_CERT`), so on a [take-home Pi](/docs/runbook/tenant/tenant-to-pi-image/) the same variables name the Pi's own CA instead. Check its SHA-256 fingerprint: `F6:8A:BD:B3:1E:A5:6D:0A:88:1F:31:28:56:8A:4C:14:B0:3A:3F:5C:3F:38:CC:F1:7C:C4:F0:09:8B:EB:94:52` |

---

## Connecting: Wi-Fi only

**Deevnet's tenant networks are Wi-Fi only.** There are no wired ports for tenants, on the switch or
anywhere else: your computer joins over Wi-Fi, and so do your devices. Terraform talks to the
Deevnet API, and which Wi-Fi your computer is on decides whether it can:

| Your computer is on | Reaches the API? | Use it for |
|---|---|---|
| **Guest** Wi-Fi | **No** — internet only | reading these docs |
| **IoT** Wi-Fi (`DVNTM-IOT`) | **No** — that is where your *devices* go, not your computer | nothing |
| **Tenant dev** Wi-Fi (`DVNTM-TD`) | **Yes** — the tenant-facing services and the internet | `terraform plan` / `apply`, MQTT test clients, SSH to your workloads |

**Work from `DVNTM-TD`.** Its key comes from the operator. It reaches the services your Terraform,
test clients and browser use (the API, the state store, the broker, the log store, Grafana and the
tenant downloads), SSH to tenant workloads, and nothing else on the site.

`DVNTM-TD` uses the site's own DNS. If your computer has a VPN, iCloud Private Relay or a hard-coded
DNS server, turn it off, or `api.mobile.deevnet.net` will not resolve. Under WSL2, the same goes
for WSL's own DNS ([below](#wsl2)).

**If your laptop is also on ethernet** (or a second Wi-Fi network), the mobile subnet
(`10.20.0.0/16`) may route out the wrong interface. Add a static route so mobile traffic goes
through `DVNTM-TD`'s gateway (requires admin / elevated prompt):

```
# Windows
route add 10.20.0.0 mask 255.255.0.0 <DVNTM-TD gateway, e.g. 10.20.45.1>

# macOS / Linux
sudo ip route add 10.20.0.0/16 via <DVNTM-TD gateway>
```

The route lasts until the next reboot. If downloads or the API time out and you are on
`DVNTM-TD`, this is the most likely cause.

---

## Tenant downloads

**At the site**, on `DVNTM-TD`, everything above that isn't a package-manager install is served
at **`https://downloads.mobile.deevnet.net/`**. It is read-only and verified with the Deevnet Root CA
([CHG-0025](/docs/changes/2026/0025-tenant-downloads/)):

| Path | What |
|---|---|
| `deevnet-root-ca.pem` | the Deevnet Root CA. Check its fingerprint against the one above before trusting it |
| `scripts/` | `install-provider.sh`, `tenant-check.sh`, and for Windows `install-provider.ps1`, `tenant-check.ps1` |
| `provider/<version>/` | the deevnet provider for macOS, Linux and Windows, Intel and ARM, with `SHA256SUMS` |
| `providers/grafana/<version>/` | the Terraform `grafana` provider, for [dashboards](/docs/runbook/tenant/services/dashboards/) |
| `terraform/<version>/` | Terraform itself |
| `tools/` | Raspberry Pi Imager (macOS, Linux, Windows) and MicroPython for the Pico W |
| `pi/` | the [tenant Pi](/docs/runbook/tenant/tenant-to-pi-image/) image and its sha256 |

---

## Getting the provider

The provider isn't on the public registry. It goes into Terraform's local mirror
(`~/.terraform.d/plugins/…`), where `terraform init` finds it. **At the site:**

```bash
curl -fsSLk -O https://downloads.mobile.deevnet.net/deevnet-root-ca.pem
openssl x509 -in deevnet-root-ca.pem -noout -fingerprint -sha256     # must match the fingerprint above
curl -fsSL --cacert deevnet-root-ca.pem -O https://downloads.mobile.deevnet.net/scripts/install-provider.sh
bash install-provider.sh
```

On Windows, in PowerShell:

```powershell
curl.exe -fsSLk -O https://downloads.mobile.deevnet.net/deevnet-root-ca.pem
$c = [Security.Cryptography.X509Certificates.X509Certificate2]::new("$PWD\deevnet-root-ca.pem");
[BitConverter]::ToString(
  [Security.Cryptography.SHA256]::Create().ComputeHash($c.RawData)
)   # must match the fingerprint above, with - in place of :
curl.exe -fsSL --ssl-revoke-best-effort --cacert deevnet-root-ca.pem -O https://downloads.mobile.deevnet.net/scripts/install-provider.ps1
powershell -ExecutionPolicy Bypass -File install-provider.ps1
```

Either script installs `deevnet/deevnet` **and** the `grafana` provider, and checks every download
against its `SHA256SUMS`. On Windows the mirror is `%APPDATA%\terraform.d\plugins\…`. **Off-site,** `bash install-provider.sh --github` (on Windows, `install-provider.ps1 -GitHub`) fetches the same prebuilt
provider from the
[GitHub release](https://github.com/deevnet/terraform-provider-deevnet/releases). **From
source** (needs Go and make): clone the repository, check out the latest tag
(`git checkout "$(git describe --tags --abbrev=0)"`), then `make mirror`. The provider's own
[Install](https://deevnet.github.io/terraform-provider-deevnet/docs/guides/install/) guide has all three routes.

Pin it in your configuration:

```hcl
deevnet = {
  source  = "deevnet/deevnet"
  version = "~> 0.5"
}
```

---

## Working from Windows

**Pick one route and stay on it.** Each has its own provider install, its own Terraform and its
own copy of your repository. Both reach the site the same way, over the laptop's Wi-Fi.

| | Native, in PowerShell | WSL2 |
|---|---|---|
| Install and check | `install-provider.ps1`, `tenant-check.ps1` | `install-provider.sh`, `tenant-check.sh`, as on Linux |
| Your tenant repository | `.\tenant.ps1 <target>`: the Makefile's targets, without make | `make <target>` |
| The token | `$env:DEEVNET_API_TOKEN = terraform output -raw api_token` | `export DEEVNET_API_TOKEN=$(terraform output -raw api_token)` |
| Devices over USB | as on macOS: Thonny, the Arduino IDE, `mpremote` | needs `usbipd-win` to hand the board to WSL |
| Building for a Pi, deploying an app | Podman Desktop, `scp` | as on Linux |

### Native, in PowerShell

- Write **`curl.exe`**, not `curl`: in Windows PowerShell 5.1, `curl` is another command.
- If PowerShell refuses to run a script, run it as
  `powershell -ExecutionPolicy Bypass -File <script>.ps1`. That changes nothing for other scripts.
- **`>` writes UTF-16 in Windows PowerShell 5.1**, which an env file reader cannot use. Let `cmd`
  redirect byte for byte: `cmd /c "terraform output -raw kit_env > kit.env"`.
- **Don't pipe an image between commands** (`podman save … | ssh …`). Windows PowerShell 5.1
  re-encodes the bytes. Save to a file and copy it: `podman save -o app.tar my-app`, then `scp`.

### WSL2

Put this in `%UserProfile%\.wslconfig`, then run `wsl --shutdown` once:

```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
```

**Both lines are required.** Mirrored mode gives WSL the laptop's own address on `DVNTM-TD`;
`dnsTunneling` forwards the site's DNS into WSL. Without `dnsTunneling`, names like
`api.mobile.deevnet.net` will not resolve inside WSL even though Windows resolves them. The default
NAT mode (neither line) puts WSL behind a network Windows makes up, and nothing on the site works.

- **Install `unzip` and `curl`** if your WSL distribution is fresh:
  `sudo apt install -y unzip curl` (Ubuntu/Debian). Both are needed to download and extract
  Terraform from the tenant downloads.
- **Clone inside WSL** (`~/…`), not under `/mnt/c`: a Windows checkout rewrites line endings and
  loses file modes, and the tenant Makefile and scripts then fail.
- **Boards over USB:** install `usbipd-win` in Windows (`winget install usbipd`), then
  `usbipd bind` and `usbipd attach --wsl` for the board. Flashing from Windows itself, with Thonny or
  the Arduino IDE, avoids this.
- Raspberry Pi Imager runs in Windows, not WSL.
