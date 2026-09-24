---
title: "Troubleshooting"
weight: 2
---

# Troubleshooting

## Is it the network?

If Terraform or an MQTT client times out, check the network before anything else. From your laptop
on `DVNTM-TD`:

```bash
curl -fsSLO https://raw.githubusercontent.com/deevnet/ansible-collection-deevnet.net/main/scripts/segment-check.sh
bash segment-check.sh DVNTM-TD
```

It checks your address and DNS, the provisioning API, the state store and the broker (each over the
site CA), the internet, and that the rest of the site is correctly out of reach. Turn off any VPN
or iCloud Private Relay first. **All passing** means the network is fine and the problem is on the
Terraform or client side (below). **Anything failing:** send the whole output to the operator; the
fix is on the substrate, not in your repo.

## Terraform side

| Symptom | What it means |
|---|---|
| `No API token` | `DEEVNET_API_TOKEN` is not exported in *this* shell |
| `Failed to query available provider packages` for `deevnet/deevnet` | the provider is not in your filesystem mirror, or not at a version your constraint allows. See [Before you start](/docs/runbook/tenant/getting-started/before-you-start/#getting-the-provider) |
| Connection timed out to `api.mobile.deevnet.net:8080` or `tfstate…:9000` | you are not on `DVNTM-TD` (or a trusted seat) — [where to sit](/docs/runbook/tenant/getting-started/before-you-start/#where-you-need-to-sit-on-the-network) |
| `api.mobile.deevnet.net` does not resolve on `DVNTM-TD` | a VPN, Private Relay or hard-coded DNS is bypassing the site's resolver `10.20.45.1` |
| `x509: certificate signed by unknown authority` | `DEEVNET_API_CACERT` does not point at `site-ca.pem` |
| `401` on the first apply | the enrollment token was for a different name, and is now spent. Ask for a new admission |
| `401` later | you are presenting the enrollment token (spent) instead of `terraform output -raw api_token` |
| `400` on a broker account | a topic pattern breaks the rules: a leading `/`, `$` or `%`, a `#` not at the end, or a device reaching into `log/` ([rules](/docs/runbook/tenant/services/devices-and-mqtt/#topic-rules)) |
| `400` on a DNS record | the address is outside your own subnet |
| `Saved plan is stale` | the state moved between `plan` and `apply`. Re-plan |
| `ssh_keys` apply fails on a workload | a known defect — [leave `ssh_keys` unset](/docs/runbook/tenant/services/network-and-workloads/#getting-onto-it) |

## Device side

In rough order of how often each is the cause:

| Symptom | Check |
|---|---|
| Never joins Wi-Fi | the PSK is the one from `terraform output`, not an older one; the SSID is the output's (`DVNTM-IOT` on the mobile kit); the board is 2.4 GHz-capable and in range |
| Joins, but the broker connection fails at TLS | the CA is `site-ca.pem` (DER for MicroPython); you connect by **name**, `mqtt.mobile.deevnet.net`, not by IP — the certificate is for the name; the ESP32 has a sane clock |
| TLS works, `CONNACK` refused (not authorised) | username is `<tenant>-<name>`; the password is from the *current* state — a `-replace` issued a new one |
| Connected, but publishes vanish | the topic must be the **granted** one, `<tenant>/…`, exactly. An unauthorised publish is dropped or disconnects the client — it is not an error you will see |
| Connected, subscribed, but nothing arrives | a refused subscription is also silent. Compare your topic with `granted_subscribe` |
| Keeps reconnecting | two devices with the same client id — the broker drops the older one each time |
| Log lines missing | the device publishes to `<tenant>/log/<its own device name>` and nothing else under `log/`; read partition `<index>-2`, not the default |
