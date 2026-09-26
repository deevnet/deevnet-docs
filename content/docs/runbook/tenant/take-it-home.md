---
title: "Take It Home on a Pi"
weight: 7
---

# Take It Home on a Pi

The meetup ends and the mobile kit packs up. Your app and your devices worked against Deevnet, and
you want them to keep working at home. This page moves them onto a **Raspberry Pi of your own**,
flashed from the image factory's `pi-backend` image, and the card is yours when you leave.

**Bring your own SD card and laptop.** The card is flashed at the meetup and goes home in your Pi;
the laptop is where you prototyped, and where your Terraform state, `kit.env` and firmware live.
Nothing of yours stays on Deevnet's equipment.

```
 at the meetup                                  at home
 ─────────────                                  ───────
 devices ──TLS 8883──▶ mqtt.mobile.deevnet.net   devices ──TLS 8883──▶ your Pi (Mosquitto)
 app     ──TLS 8427──▶ Deevnet log store         app     ──TLS 8427──▶ your Pi (VictoriaLogs)
 you     ──TLS 3000──▶ Deevnet Grafana           you     ──TLS 3000──▶ your Pi (Grafana)
         <tenant>/…  <tenant>/log/<device>               <tenant>/…  <tenant>/log/<device>   ← unchanged
```

The Pi keeps the **app contract**: the same ports, the same topic prefix, the same reserved `log`
level, the same ingest and read tokens with the same partition header, and a Grafana organization
with the same three data source UIDs. What changes is the host
name, the CA and the secrets. **Nothing on the Pi belongs to Deevnet.** It has no Deevnet account,
key or route, and its CA and tokens are generated on the card the first time it boots.

---

## The one rule: configure from the environment

The move takes one file only if your app never hard-codes a Deevnet name. Read every endpoint from
the environment, under these names:

| Variable | On Deevnet | On your Pi |
|---|---|---|
| `DEEVNET_TENANT` | your tenant | the same |
| `MQTT_HOST` | `mqtt.mobile.deevnet.net` | `<hostname>.local` |
| `MQTT_PORT` | `8883` | `8883` |
| `MQTT_CA_FILE` | `site-ca.pem` (Deevnet's) | `site-ca.pem` (the card's) |
| `LOG_ENDPOINT` | `log_endpoint` | `https://<hostname>.local:8427` |
| `LOG_INGEST_TOKEN`, `LOG_READ_TOKEN` | `log_ingest_token`, `log_read_token` | the card's |
| `LOG_SELECT_HEADER` | `X-Deevnet-Partition` | the same |
| `LOG_DEVICE_PARTITION` | `<index>-2` | the same, if you keep the index |
| `GRAFANA_URL` | `dashboard_url` | `https://<hostname>.local:3000` |
| `GRAFANA_AUTH` | `dashboard_username:dashboard_password` | the card's |
| `GRAFANA_ORG_ID`, `TF_VAR_grafana_org_id` | `dashboard_org_id` | the card's |
| `GRAFANA_CA_CERT` | `site-ca.pem` (Deevnet's) | `site-ca.pem` (the card's) |

The `GRAFANA_*` names are the ones the Terraform `grafana` provider reads by itself, and
`TF_VAR_grafana_org_id` feeds the `org_id` every resource must carry
([Dashboards](/docs/runbook/tenant/services/dashboards/#dashboards-as-code)). The dashboards' data
sources have the same UIDs on both, so **the same dashboard code applies to both**.

While you are still on Deevnet, have Terraform write the file for you:

```hcl
output "kit_env" {
  sensitive = true
  value     = <<-EOT
    DEEVNET_TENANT=${deevnet_tenant.this.name}
    MQTT_HOST=mqtt.mobile.deevnet.net
    MQTT_PORT=8883
    MQTT_CA_FILE=site-ca.pem
    LOG_ENDPOINT=${deevnet_tenant.this.log_endpoint}
    LOG_INGEST_TOKEN=${deevnet_tenant.this.log_ingest_token}
    LOG_READ_TOKEN=${deevnet_tenant.this.log_read_token}
    LOG_SELECT_HEADER=${deevnet_tenant.this.log_select_header}
    LOG_DEVICE_PARTITION=${deevnet_tenant.this.index}-2
    GRAFANA_URL=${deevnet_tenant.this.dashboard_url}
    GRAFANA_AUTH=${deevnet_tenant.this.dashboard_username}:${deevnet_tenant.this.dashboard_password}
    GRAFANA_ORG_ID=${deevnet_tenant.this.dashboard_org_id}
    TF_VAR_grafana_org_id=${deevnet_tenant.this.dashboard_org_id}
    GRAFANA_CA_CERT=site-ca.pem
  EOT
}
```

```bash
terraform output -raw kit_env > kit.env
```

If the app runs with that file on Deevnet, the Pi's `kit.env` runs it at home.

**Before you leave**, save `terraform output -json flash`: it holds your devices' broker
passwords. Keep those passwords on the Pi and nothing needs reflashing but the host name and the CA.

---

## 1. Flash the card

You need a Raspberry Pi 3, 4, 5 or Zero 2 W (64-bit; a Pi 4 or 5 if you want dashboards), your
own card of 8 GB or more, and the take-home tools in
[Before You Start](/docs/runbook/tenant/getting-started/before-you-start/#tools). At the site, the
image and Pi Imager are in the
[tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#tenant-downloads) `pi/`
and `tools/`; check the image against its `.sha256` before flashing.

1. In **Raspberry Pi Imager** choose *Use custom* and pick `raspios-bookworm-mobile-pi-backend.img.xz`
   (from the tenant downloads' `pi/`). **Imager 2.x offers no OS customization for a custom image**,
   so skip it: the boot partition does the same job in step 3.
2. Write the card, and leave it in the reader. The boot partition (`bootfs`) opens on your laptop.
   **`README.txt`** there is this page's short version, and stays on the card.
3. **On the boot partition:**
   - **Name your tenant** in `deevnet-kit.txt`:

     ```
     tenant=bench1
     index=4
     ```

     Use your Deevnet tenant's name and index (`terraform output`, or `deevnet_tenant.this.index`).
     With the same index, `LOG_DEVICE_PARTITION` doesn't change either. Left empty, the tenant is
     `pi` with index 1.
   - **Create your login, and turn on SSH:**

     ```bash
     cd /Volumes/bootfs                      # macOS; on Linux, wherever bootfs mounted
     touch ssh                               # enables SSH on first boot
     echo "you:$(openssl passwd -6)" > userconf.txt    # asks for the password twice
     ```

     `userconf.txt` is one line, `username:password-hash`. Raspberry Pi OS creates that user on first
     boot and deletes the file. The username is yours to choose, and the image has no user of its
     own. **macOS's own `openssl` can't make that hash** (LibreSSL has no `-6`). Use Homebrew's
     (`brew install openssl`, then `$(brew --prefix openssl)/bin/openssl passwd -6`), or run the
     command on any Linux machine and paste the result.

### How you sign in: your choice

Every option works from the same `userconf.txt` user. Pick whichever you like:

| | Set up | Signing in |
|---|---|---|
| **Password only** | nothing more | `ssh you@<pi>`, then type the password |
| **A key you already have** | once, after first boot: `ssh-copy-id -i ~/.ssh/id_ed25519.pub you@<pi>` | no password |
| **A new key, just for this Pi** | `ssh-keygen -t ed25519 -f ~/.ssh/my-pi`, then `ssh-copy-id -i ~/.ssh/my-pi.pub you@<pi>` | `ssh -i ~/.ssh/my-pi you@<pi>` |

`ssh-copy-id` asks for the password once, and installs the **public** key for that user on the Pi.
The name at the end of a public key is only a label, so a key made as `alice` works for a Pi user
called `bench1`. Password sign-in stays on in every case. Turning it off
(`PasswordAuthentication no`) is your call once a key works.

If your version of Imager does offer OS customization for the image, you can use it instead of
`userconf.txt` and `ssh`. Both routes end the same way.

## 2. First boot

Boot the Pi at home, wired or on Wi-Fi you've set up. First boot creates your user, grows the
filesystem and reboots once. Then `deevnet-kit` runs **once**. It
generates the card's CA and certificate, the log tokens, the bridge's credentials and Grafana's
secrets, and starts the broker, the log store, the bridge and Grafana. Grafana's first start takes a
minute or two; then `deevnet-kit dashboards` creates your organization. Until it has, `kit.env`
carries no `GRAFANA_*` lines.

The hostname is `raspberrypi` unless you changed it. Find the Pi's address on your router's
client list, or use `raspberrypi.local` from a laptop on the same network.

```bash
ssh you@<pi>
sudo deevnet-kit status
sudo deevnet-kit selftest                 # the card, end to end: every check ok?
sudo deevnet-kit export ~/deevnet-kit     # kit.env + site-ca.pem, the Pi's side of the table above
```

**The self-test** runs by itself after every boot, and `status` shows the last result. It checks:
- every service;
- TLS on 8883, 8427 and 3000;
- a device log line sent over MQTT (through a throwaway account) and read back;
- an app log line sent and read back;
- your Grafana login, data sources and dashboard, including the device line read back through Grafana.

If a check fails, it names it. Each run leaves two log lines marked `deevnet-kit selftest`.

**If the Pi's address changes after first boot,** for example because your router later gives it a
different lease, the certificate no longer names the address your devices dial. `status` says so.
Run `sudo deevnet-kit regen-certs`. It reissues the certificate from the same card CA, so no device
needs a new CA. On a network where the Pi's MAC has a DHCP reservation, the first boot can still
land on a pool address if an older OS on the same Pi holds the reserved lease. It moves once that
lease expires.

Copy `~/deevnet-kit/` to your laptop. That is everything your app needs.

## 3. Recreate your broker accounts

On Deevnet your `deevnet_iot_broker_account` resources made the accounts. On the Pi,
`deevnet-kit account` does, and it applies the same rules: patterns are relative to your tenant,
a device account may publish only its own `log/<device>`, and a device account may not read the
log space.

For each account in your Terraform, pass the same name, device and patterns. Pass the password
from `flash` to keep it:

```bash
sudo deevnet-kit account add pico-1 --device pico-1 \
  --publish sensors/pico-1/telemetry --publish log/pico-1 \
  --subscribe sensors/pico-1/command \
  --password '<flash.mqtt.pico-1.pass>'

sudo deevnet-kit account add backend \
  --subscribe 'sensors/+/telemetry' --publish 'sensors/+/command'
```

Without `--password` a new one is generated and printed **once**. The username is
`<tenant>-<name>`, as on Deevnet. `deevnet-kit account list` and `deevnet-kit account rm NAME` do
the rest. Removing an account disconnects any client still using it.

## 4. Repoint the devices

Two lines change in the firmware from the [walkthrough](/docs/runbook/tenant/walkthrough-mqtt-device/):

- **The broker.** Use the Pi's address. A Pico W cannot resolve `bench1.local`. Give the Pi a DHCP
  reservation on your router so the address stays put.
- **The CA.** Replace `site-ca.pem`/`site-ca.der` with the card's (`~/deevnet-kit/site-ca.pem`;
  `openssl x509 -in site-ca.pem -outform der -out site-ca.der` for the Pico).

And the Wi-Fi: your home network instead of `DVNTM-IOT`. The username, the password and every topic
stay the same.

The certificate names the Pi's addresses at the time it was issued. If the address changes,
`deevnet-kit status` says so; run `sudo deevnet-kit regen-certs`. That reissues the server
certificate from the same CA, so no device needs a new CA.

## 5. Run your app on the Pi

Build your app as a container image (arm64) and run it with the example unit:

```bash
sudo deevnet-kit export /opt/my-app
sudo cp /opt/deevnet-kit/examples/my-app.service /etc/systemd/system/
sudoedit /etc/systemd/system/my-app.service        # set IMAGE=
sudo systemctl daemon-reload && sudo systemctl enable --now my-app
```

The unit uses host networking and points the app at `localhost`, because a container cannot
resolve `.local` names. The certificate covers `localhost`. Podman on Bookworm is 4.3, which has no
quadlets, so it is a plain unit.

Or run the app on your laptop with `~/deevnet-kit/kit.env`; the Pi does not mind.

## 6. Bring your dashboards

Your dashboards on Deevnet are Terraform (the
[Dashboards](/docs/runbook/tenant/services/dashboards/#dashboards-as-code) page). Apply the same
configuration against the Pi, with the Pi's `kit.env` in the environment:

```bash
set -a; . ~/deevnet-kit/kit.env; set +a
export GRAFANA_CA_CERT=~/deevnet-kit/site-ca.pem
terraform -chdir=dashboards init
terraform -chdir=dashboards apply
```

Use a **separate state** from your Deevnet one, as above (its own directory, or a workspace):
the Pi is a different Grafana, and your Deevnet state would try to update objects that are not
there. The data source UIDs are the same, so every panel finds its data. A dashboard you built only
by clicking on Deevnet does not come along; export it into your repository first.

In a browser: `https://<hostname>.local:3000`, with the user and password from `GRAFANA_AUTH`.
Your organization opens with a **"Start here"** dashboard: a temperature graph from device log
lines, your device logs and your app logs. It is yours to change; the card never overwrites it.

## 7. Check it

```bash
set -a; . ~/deevnet-kit/kit.env; set +a
mosquitto_sub -h "$MQTT_HOST" -p 8883 --cafile ~/deevnet-kit/site-ca.pem \
  -u "$DEEVNET_TENANT-backend" -P '<backend password>' -t "$DEEVNET_TENANT/sensors/+/telemetry" -v

# Device log lines, as on Deevnet
curl -sS --cacert ~/deevnet-kit/site-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  -H "$LOG_SELECT_HEADER: $LOG_DEVICE_PARTITION" \
  "$LOG_ENDPOINT/select/logsql/query" --data-urlencode 'query=*'
```

---

## What does not come along

| On Deevnet | At home |
|---|---|
| Workload VMs | Your app runs on the Pi or your laptop |
| `<tenant>.mobile.deevnet.net` DNS | `<hostname>.local`, and the Pi's address for devices |
| Wi-Fi keys on `DVNTM-IOT` | Your own Wi-Fi |
| The device registry | Device names are checked for shape only |
| Terraform state and the API token | Nothing to apply: `deevnet-kit` is the whole control plane. Only your dashboards are still Terraform, against the Pi's Grafana |

Your Deevnet tenant is untouched by any of this. Destroy it when you are done
([Day 2](/docs/runbook/tenant/operating/day-2/)), or keep prototyping there. The two do not share a secret.

## Where it differs, for the careful

- **The broker is Mosquitto**, not VerneMQ. The wire protocol, ports and topic rules are the same.
- **A subscription outside your grant** is refused in the SUBACK on Deevnet. On the Pi it is
  accepted and nothing is delivered. Either way no message crosses.
- **Revocation** is immediate on the Pi and takes effect on the next connect on Deevnet.
- **You are Grafana's admin on the Pi** (`grafana_admin_password` in `/etc/deevnet-kit/kit.json`).
  Your tenant login is still an Editor, so the same Terraform runs on both.
- **Memory.** Grafana wants about 512 MB. On a 512 MB Zero 2 W, turn it off:
  `sudo systemctl disable --now grafana deevnet-kit-dashboards`.

{{< hint warning >}}
**First real Pi, 2026-09-25.** A Pi 4 flashed with this image, set up with `userconf.txt` and
`ssh` as above, booted cleanly. The broker, log store and Grafana all came up on the card's own
certificate, and the self-test passed **14 of 15**. The failure is Grafana's "device log readable
through Grafana" check: on real hardware Grafana reports the VictoriaLogs plugin as **not
registered**, although it loads under emulation. The cause is being investigated; until it's
fixed, read device logs with the `curl` in step 7. Earlier, under emulation, every check on this
page passed.
{{< /hint >}}

The image is built by `make pi-backend` in `deevnet-image-factory` (`docs/pi-backend.md`), and
`deevnet-kit` lives in `deevnet-provisioning-api` beside the rules it applies.
