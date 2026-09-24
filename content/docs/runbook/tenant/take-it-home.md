---
title: "Take It Home on a Pi"
weight: 6
---

# Take It Home on a Pi

The meetup ends and the mobile kit packs up. Your app and your devices worked against Deevnet, and
you want them to keep working at home. This page moves them onto a **Raspberry Pi of your own**,
flashed from the image factory's `pi-backend` image, and the card is yours when you leave.

```
 at the meetup                                  at home
 ─────────────                                  ───────
 devices ──TLS 8883──▶ mqtt.mobile.deevnet.net   devices ──TLS 8883──▶ your Pi (Mosquitto)
 app     ──TLS 8427──▶ Deevnet log store         app     ──TLS 8427──▶ your Pi (VictoriaLogs)
         <tenant>/…  <tenant>/log/<device>               <tenant>/…  <tenant>/log/<device>   ← unchanged
```

The Pi keeps the **app contract**: the same ports, the same topic prefix, the same reserved `log`
level, the same ingest and read tokens with the same partition header. What changes is the host
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

You need a Raspberry Pi 3, 4, 5 or Zero 2 W (64-bit) and a card of 8 GB or more.

1. In **Raspberry Pi Imager** choose *Use custom* and pick `raspios-bookworm-mobile-pi-backend.img.xz`
   (the operator has it at the meetup).
2. In **OS customisation** set a hostname (say `bench1`), your own user and password, your home
   Wi-Fi, and enable SSH. The image has no user of its own.
3. Write the card. Before you eject it, open the boot partition from your laptop and edit
   **`deevnet-kit.txt`**:

   ```
   tenant=bench1
   index=4
   ```

   Use your Deevnet tenant's name and index (`terraform output`, or `deevnet_tenant.this.index`).
   With the same index, `LOG_DEVICE_PARTITION` does not change either. Left empty, the tenant is
   `pi` with index 1.

## 2. First boot

Boot the Pi at home. Imager's first boot runs and reboots; then `deevnet-kit` runs **once**. It
generates the card's CA and certificate, the log tokens and the bridge's credentials, and starts
the broker, the log store and the bridge.

```bash
ssh you@bench1.local
sudo deevnet-kit status
sudo deevnet-kit export ~/deevnet-kit     # kit.env + site-ca.pem, the Pi's side of the table above
```

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

## 6. Check it

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
| Terraform state and the API token | Nothing to apply: `deevnet-kit` is the whole control plane |

Your Deevnet tenant is untouched by any of this. Destroy it when you are done
([Day 2](/docs/runbook/tenant/operating/day-2/)), or keep prototyping there. The two do not share a secret.

## Where it differs, for the careful

- **The broker is Mosquitto**, not VerneMQ. The wire protocol, ports and topic rules are the same.
- **A subscription outside your grant** is refused in the SUBACK on Deevnet. On the Pi it is
  accepted and nothing is delivered. Either way no message crosses.
- **Revocation** is immediate on the Pi and takes effect on the next connect on Deevnet.

{{< hint warning >}}
**Proven under emulation, not yet on a Pi.** The image was built with `make pi-backend` and
booted under emulation. First boot ran. All four services came up. Every check on this page
passed against the booted card: accounts, a refused device grant, telemetry reaching the
backend, device logs arriving in `4-2`, a forged device's line never arriving, and the file
permissions. A real Pi on real Wi-Fi, with Imager's customisation, has not been run. If a
step fails there, tell the operator so this page can say "tested".
{{< /hint >}}

The image is built by `make pi-backend` in `deevnet-image-factory` (`docs/pi-backend.md`), and
`deevnet-kit` lives in `deevnet-provisioning-api` beside the rules it applies.
