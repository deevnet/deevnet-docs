---
title: "Verify Site"
weight: 14
aliases:
  - /docs/runbook/building-recovery/build-verification/
---

# Verify Site

Validation after the site is built or rebuilt, once every component is up.

---

## Overview

Each build phase checks itself: the Ansible roles assert what they deployed, and each change record
carries its own verification. This page is the end-to-end pass: a short list of checks that, together,
say the site is up.

- **Run it from the Builder**, on the management segment, which reaches every zone. Tenant-facing
  segments are checked from a real client instead: see [From the client segments](#from-the-client-segments).
- **Use the site CA** for every TLS check. The control node's copy is
  `ansible-collection-deevnet.mgmt/.openbao/site-ca.pem`:

  ```bash
  CA=~/dvnt/ansible-collection-deevnet.mgmt/.openbao/site-ca.pem
  ```

- **Addresses** are from inventory. Names are in the `mobile.deevnet.net` zone and resolve through the
  core router, `10.20.99.1`.

*Rewritten 2026-09-26 from inventory and the change records, for the domain-VM layout of
[ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/). Expected results marked
"recorded" were measured in the change record named. The others are the service's standard health
endpoint and have not yet been run as part of this page.*

---

## Network

```bash
# Core router answers on management
ping -c 3 10.20.99.1

# DNS: the router answers for site names, and forwards tenant zones
dig +short @10.20.99.1 dv02hyp001p01.mobile.deevnet.net      # 10.20.99.21
dig +short @10.20.99.1 api.mobile.deevnet.net                # 10.20.25.20
dig +short @10.20.99.1 tdemo-1.tdemo.mobile.deevnet.net      # 10.20.129.10, if tdemo is applied
```

- **DHCP** is checked from a client: a lease in the right subnet is the first thing
  [Segment Check](/docs/runbook/substrate/network/segment-check/) tests.
- **Zone policy** is checked by the firewall role's own plan (no drift), and from clients by Segment
  Check. Pinging across segments from the Builder proves little, since management reaches every zone.

---

## Hypervisors

```bash
ping -c 3 dv02hyp001p01.mobile.deevnet.net    # management hypervisor, 10.20.99.21
ping -c 3 dv02hyp002p02.mobile.deevnet.net    # tenant hypervisor, 10.20.99.22

# Proxmox API answers
curl -k https://dv02hyp001p01.mobile.deevnet.net:8006/api2/json/version
curl -k https://dv02hyp002p02.mobile.deevnet.net:8006/api2/json/version

# SSH as the automation user
ssh a_autoprov@dv02hyp001p01.mobile.deevnet.net hostname
```

A `401` from `/api2/json/version` means the API is up and wants a token: that passes. A timeout
fails.

---

## Management-plane services

The domain VMs, and one check each.

| Service | Host | Check | Expected |
|---|---|---|---|
| Deevnet API | `dv02prv001v01`, 10.20.25.20 | `curl --cacert $CA https://api.mobile.deevnet.net:8080/readyz` | `200` (recorded: the `deevnet_api` role asserts it) |
| | | `curl --cacert $CA https://api.mobile.deevnet.net:8080/version` | the deployed tag |
| Terraform state store | `dv02prv001v01`, 10.20.25.20 | `curl -I http://tfstate.mobile.deevnet.net:9000/minio/health/live` | `200` |
| OpenBao | `dv02idn001v01`, 10.20.25.21 | `curl --cacert $CA https://dv02idn001v01.mobile.deevnet.net:8200/v1/sys/health` | `200`: initialized, unsealed, active |
| Tenant DNS (PowerDNS) | `dv02idn001v01`, 10.20.25.21 | `dig @10.20.25.21 tdemo.mobile.deevnet.net SOA` | an answer for each admitted tenant's zone |
| MQTT broker (VerneMQ) | `dv02msg001v01`, 10.20.35.20 | `openssl s_client -connect mqtt.mobile.deevnet.net:8883 -CAfile $CA </dev/null` | `Verify return code: 0` (recorded: [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/)) |
| Log store (vmauth) | `dv02obs001v01`, 10.20.25.22 | `curl --cacert $CA -o /dev/null -w '%{http_code}\n' https://dv02obs001v01.mobile.deevnet.net:8427/select/logsql/query` | `401`: vmauth is up and refuses a request with no token (recorded: [CHG-0018](/docs/changes/2026/0018-central-log-store/)) |
| Grafana | `dv02obs001v01`, 10.20.25.22 | `curl --cacert $CA https://dv02obs001v01.mobile.deevnet.net:3000/api/health` | `200`, `"database": "ok"` (recorded: the `grafana` role checks it, [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)) |
| Tenant downloads | `dv02obs001v01`, 10.20.25.22 | `curl --cacert $CA -I https://downloads.mobile.deevnet.net:8443/` | `200` |
| Omada controller | `dv02nms001v01`, 10.20.99.40 | `curl -k -I https://omada.mobile.deevnet.net:8043/` | an answer (the login page, or a redirect to it) |
| Artifact server | Builder, 10.20.99.95 | `curl -I http://artifacts.mobile.deevnet.net/fedora/43/mirror/` | `200` |

Then **reconcile one tenant**. It exercises every backend the API writes (DNS, state, broker
accounts, the log store, Grafana) in one call, and a failing backend is named in the response:

```bash
# OPERATOR_TOKEN is vault_deevnet_api_token, in the deevnet_api group vault
curl --cacert $CA -X POST -H "Authorization: Bearer $OPERATOR_TOKEN" \
  https://api.mobile.deevnet.net:8080/v1/tenants/tdemo/reconcile
```

The tenant ends `ready`, and every step succeeded. A `502` names the backend that is down
(recorded: [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/)).

---

## PXE infrastructure

Only while the Builder is serving PXE, in bootstrap mode
([Authority Transition](/docs/runbook/substrate/building-recovery/authority-transition/)). On the
Builder:

```bash
systemctl status tftp.socket
ls /srv/tftp/pxelinux.cfg/
```

---

## From the client segments

Run [Segment Check](/docs/runbook/substrate/network/segment-check/) from a laptop on each SSID. It
proves what the Builder can't: a lease in the right subnet, names answered by the segment's own
gateway, and that everything the zone policy denies is really dropped.

```bash
bash segment-check.sh DVNTM-TD     # tenant dev
bash segment-check.sh DVNTM-IOT    # IoT
```

Recorded results for comparison: `DVNTM-TD` 29/29 and `DVNTM-IOT` 15/15
([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/)).

---

## Automated verification

Not built. One playbook that runs the checks above and produces a single pass/fail report is on the
[Extended Management Plane](/docs/roadmap/infrastructure/mobile/management-plane/) roadmap, under
Build Verification.
