---
title: "deevnet-kit"
weight: 5
---

# deevnet-kit

The Deevnet API's stand-in on a Raspberry Pi. On the take-home Pi backend image it does, for one
tenant and on the Pi itself, what the API does for a tenant on the site: broker accounts, log users,
the card's own CA and certificates, and a Grafana organization. It is built from the API's own
packages, so the same rules apply in both places.

| | |
|---|---|
| **Source** | `deevnet-provisioning-api`, `cmd/deevnet-kit`; it shares the API's tag |
| **Built by** | `make build-pi` and `make stage-pi` in the API repository (linux/arm64), baked into the image by `make pi-backend` in `deevnet-image-factory` |
| **Runs as** | A CLI and three systemd units on the Pi: first boot, dashboards, and a self-test on every boot |
| **Commands** | `init`, `status`, `env`, `export`, `account add\|list\|rm`, `regen-certs`, `render`, `dashboards`, `selftest` |
| **State** | `/etc/deevnet-kit/` (the tenant and its tokens, accounts, TLS, Grafana settings); input from `/boot/firmware/deevnet-kit.txt` |

It is not part of the deployed API. How a tenant uses the image is
[Tenant to Pi Image](/docs/runbook/tenant/tenant-to-pi-image/).
