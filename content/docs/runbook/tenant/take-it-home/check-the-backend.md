---
title: "Check the Backend"
weight: 5
---

# Check the Backend

**On every medium, `tenant2backend` runs once at first boot and makes the backend yours.** It
generates the backend's CA and its certificate (naming its host name and address), the log tokens,
the bridge's credentials and Grafana's secrets, and starts the broker, the log store, the bridge and
Grafana. Grafana's first start takes a minute or two; then `tenant2backend dashboards` creates your
organization. Until it has, `kit.env` carries no `GRAFANA_*` lines.

## Sign in and check it

```bash
ssh you@<hostname>.local
sudo tenant2backend status
sudo tenant2backend selftest                 # the backend, end to end: every check ok?
sudo tenant2backend export ~/backend     # kit.env + backend-ca.pem, the backend's side of the table
```

Copy `~/backend/` to your computer. That is everything your app needs: the backend's column of
[the table](/docs/runbook/tenant/take-it-home/prepare/#the-one-rule-configure-from-the-environment).

## The self-test

**The self-test runs by itself after every boot, and `status` shows the last result.** It checks:
- every service;
- TLS on 8883, 8427, 3000 and 443, and on 9000 once you have a bucket;
- a device log line sent over MQTT (through a throwaway account) and read back;
- an app log line sent and read back;
- a metric pushed with the ingest token and read back, and another tenant's partition refused;
- your Grafana login, data sources and dashboard, including the device line read back through Grafana;
- alerting: Alertmanager's configuration loaded, every rule group evaluating, and the phone's login
  reading its own topics and publishing to none.

If a check fails, it names it. Each run leaves two log lines marked `tenant2backend selftest`.

## If its address changes

**The certificate names the backend's address at the time it was issued.** If your router later
gives the backend a different address, the certificate no longer names the one your devices dial,
and `status` says so. Run `sudo tenant2backend regen-certs`: it reissues the certificate from the same
CA, so no device needs a new CA. A DHCP reservation on your router keeps the address put. On a
[Deevnet backend](/docs/runbook/tenant/take-it-home/certificates/#take-a-certificate-from-deevnet),
`regen-certs` refuses: its certificate names no address, and is renewed from Deevnet.

Next: [Move your tenant](/docs/runbook/tenant/take-it-home/move-your-tenant/).
