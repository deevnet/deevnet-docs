---
title: "Move Your Tenant"
weight: 6
---

# Move Your Tenant

**With the backend up, your tenant moves onto it in the same order on every medium:** the broker
accounts, then the devices, then your app, then its dashboards, alert rules and buckets. Each step
keeps what your tenant had on Deevnet, its names, passwords, topics and data source UIDs, so
nothing your app or your devices do has to change.

## Recreate your broker accounts

**`deevnet-kit account` makes the accounts your `deevnet_iot_broker_account` resources made on
Deevnet, by the same rules.** Patterns are relative to your tenant, a device account may publish
only its own `log/<device>`, and a device account may not read the log space.

For each account in your Terraform, pass the same name, device and patterns, and keep its
password: put it on the first line of a file and pass `--password-file`, so it stays out of your
shell history. For devices the password is in `flash`; for your app it is `MQTT_PASSWORD` in your
Deevnet `kit.env`.

```bash
sudo deevnet-kit account add pico-1 --device pico-1 \
  --publish sensors/pico-1/telemetry --publish log/pico-1 \
  --subscribe sensors/pico-1/command \
  --password-file pico-1.pw

sudo deevnet-kit account add backend \
  --subscribe 'sensors/+/telemetry' --publish 'sensors/+/command' \
  --password-file backend.pw
```

Without a password a new one is generated and printed **once**. The username is
`<tenant>-<name>`, as on Deevnet. `deevnet-kit account list` and `deevnet-kit account rm NAME` do
the rest. Removing an account disconnects any client still using it.

## Repoint the devices

**Two lines change in the firmware from the
[walkthrough](/docs/runbook/tenant/walkthrough-mqtt-device/):**

- **The broker.** Use the backend's address. A Pico W cannot resolve `bench1.local`. Give the
  backend a DHCP reservation on your router so the address stays put.
- **The CA.** Replace `deevnet-root-ca.pem`/`.der` with the backend's
  (`~/deevnet-kit/deevnet-kit-ca.pem`;
  `openssl x509 -in deevnet-kit-ca.pem -outform der -out deevnet-kit-ca.der` for the Pico).

And the Wi-Fi: your network instead of `DVNTM-IOT`. The username, the password and every topic
stay the same.

## Run your app

**Your app runs on the backend as a container.** Build it on your computer for the backend's
architecture, and copy the image across over SSH; no registry is involved:

| Backend | Build with |
|---|---|
| A Raspberry Pi, or UTM on a Mac with Apple Silicon | `--platform linux/arm64` |
| Proxmox or KVM, VirtualBox, Hyper-V, or a computer of your own | `--platform linux/amd64` |

```bash
podman build --platform linux/arm64 -t my-app .
podman save my-app | ssh you@bench1.local sudo podman load
```

On the backend, export the app's settings **with its broker login**. `--app` checks the password
against the account you recreated before it writes anything, so `kit.env` can't carry one the
broker refuses. Then install the example unit, which runs `localhost/my-app:latest`:

```bash
sudo deevnet-kit export /opt/my-app --app backend --password-file backend.pw
shred -u backend.pw
sudo cp /opt/deevnet-kit/examples/my-app.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now my-app
sudo journalctl -u my-app -f
```

The unit uses host networking and points the app's broker, log store and Grafana at `localhost`,
because a container cannot resolve `.local` names. The certificate covers `localhost`. Podman on
Bookworm is 4.3, which has no quadlets, so it is a plain unit.

Or run the app on your computer with `~/deevnet-kit/kit.env`; the backend does not mind.

## Bring your dashboards

**Your dashboards on Deevnet are Terraform, and the same configuration applies to the backend**
([Dashboards](/docs/runbook/tenant/services/dashboards/#dashboards-as-code)). Run it with the
backend's `kit.env` in the environment:

```bash
set -a; . ~/deevnet-kit/kit.env; set +a
export GRAFANA_CA_CERT=~/deevnet-kit/deevnet-kit-ca.pem
terraform -chdir=dashboards init
terraform -chdir=dashboards apply
```

Use a **separate state** from your Deevnet one, as above (its own directory, or a workspace): the
backend is a different Grafana, and your Deevnet state would try to update objects that are not
there. The data source UIDs are the same, so every panel finds its data. A dashboard you built only
by clicking on Deevnet does not come along; export it into your repository first.

In a browser: `https://<hostname>.local:3000`, with the user and password from `GRAFANA_AUTH`.
Your organization opens with a **"Start here"** dashboard: a temperature graph from device log
lines, your device logs and your app logs. It is yours to change; the backend never overwrites it.
Your metrics are there too, through `deevnet-metrics-workloads`, as on Deevnet.

## Your alert rules

**Your rule groups come from your own Terraform, exported as JSON**
([Alerting](/docs/runbook/tenant/services/alerting/)). Add an output beside your
`deevnet_alert_rule_group` resources, naming each group:

```hcl
output "alert_rules" {
  value = {
    groups = [for g in [deevnet_alert_rule_group.backend, deevnet_alert_rule_group.devices] : {
      name      = g.name
      type      = g.type
      interval  = g.interval
      topic     = g.topic
      partition = g.partition
      rules = [for r in g.rule : {
        alert       = r.alert
        expr        = r.expr
        "for"       = r.for # quoted: bare, "for" starts a for expression
        labels      = r.labels
        annotations = r.annotations
      }]
    }]
  }
}
```

Then export them, copy the file to the backend, and load it:

```bash
terraform output -json alert_rules > rules.json
sudo deevnet-kit alerts import rules.json
sudo deevnet-kit alerts list
```

**The backend checks them as Deevnet does**, with the same code: a label that routes an alert
(`tenant`, `deevnet_topic`), or a rule vmalert won't load, is refused with the reason, and nothing
changes. Importing again replaces every group; `sudo deevnet-kit alerts clear` removes them. Each
group's alerts go to `<tenant>-<topic>`, as on Deevnet.

## Your phone

**The ntfy app reads your alerts from the backend, on the backend's network.**

```bash
sudo deevnet-kit notify
```

prints the server, the login and the topics. On the phone, install `deevnet-kit-ca.pem` as a CA
certificate (or `deevnet-root-ca.pem` on a Deevnet backend), then subscribe to each topic in the
ntfy app on that server, with that login, as on
[Deevnet](/docs/runbook/tenant/services/alerting/#your-phone). If the phone can't find
`<hostname>.local`, use the backend's address: its certificate names that too. The login reads only
your topics and publishes to none. Nothing is sent off the backend, so the phone hears it only on a
network that reaches the backend.

## Your buckets

**The backend runs the bucket store Deevnet runs, once you add a bucket**
([Object Storage](/docs/runbook/tenant/services/object-storage/)). Make each bucket your app uses,
with the same name and settings, and bring its key so the app's settings carry over:

```bash
terraform output -json files_bucket | jq .writer > writer.json   # on your computer
sudo deevnet-kit bucket add files --quota-gb 5 --versioning --key-file writer.json
sudo deevnet-kit bucket key add files reader --access read      # a new key, or --key-file
sudo deevnet-kit export ~/deevnet-kit --bucket files:default
```

The bucket is `<tenant>-files` at `https://<hostname>.local:9000`, path-style, and each key reaches
only its own bucket, as on Deevnet. The quotas must fit the backend's disk. **The objects don't
come with it:** copy them across while you can reach both, for example with `rclone sync` from
`s3.mobile.deevnet.net` to the backend.

## Check it

**Your app's broker login and your devices' log lines, read from your computer:**

```bash
set -a; . ~/deevnet-kit/kit.env; set +a
mosquitto_sub -h "$MQTT_HOST" -p 8883 --cafile ~/deevnet-kit/deevnet-kit-ca.pem \
  -u "$DEEVNET_TENANT-backend" -P '<backend password>' -t "$DEEVNET_TENANT/sensors/+/telemetry" -v

# Device log lines, as on Deevnet
curl -sS --cacert ~/deevnet-kit/deevnet-kit-ca.pem -H "Authorization: Bearer $LOG_READ_TOKEN" \
  -H "$LOG_SELECT_HEADER: $LOG_DEVICE_PARTITION" \
  "$LOG_ENDPOINT/select/logsql/query" --data-urlencode 'query=*'
```

Next, if you want more than the backend's own CA:
[Choose its certificates](/docs/runbook/tenant/take-it-home/certificates/).
