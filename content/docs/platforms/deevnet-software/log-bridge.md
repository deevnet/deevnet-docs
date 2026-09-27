---
title: "Log Bridge"
weight: 3
---

# Log Bridge

Carries device log lines from the MQTT broker into each tenant's device-log partition, `(index, 2)`,
in the tenant log store ([ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/) §4,
[CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/)). A device publishes; it never talks to the log
store.

| | |
|---|---|
| **Repository** | `deevnet-log-bridge`, Go ([version](/docs/platforms/software-catalog/#deevnets-own-software)) |
| **Runs on** | `dv02msg001v01`, beside the broker, as the `deevnet-log-bridge` container; `deevnet.mgmt` role `log_bridge`. Also on the Pi backend image |
| **Reads** | MQTT `+/log/#` (`<tenant>/log/<device>`), QoS 1, persistent session, as the subscribe-only account `substrate-log-bridge` |
| **Writes** | vmauth on the log store, with the tenant named in `X-Deevnet-Tenant`, under one store token |
| **Health** | `/healthz` on `127.0.0.1:9099` |

It keeps no state. Its queue holds 10,000 lines and drops the oldest when full, logging the loss.
Failed batches are retried with backoff; batches the store refuses are not. It is in no device's
path: if it stops, devices keep publishing, and their lines queue in its persistent broker session
up to the broker's limits.
