---
title: "Important URLs"
weight: 1
---

# Important URLs

Every management interface and service endpoint on the mobile site, by DNS name and by IP.

- **Names** are in the `mobile.deevnet.net` zone and resolve through the core router,
  `10.20.99.1`.
- **Use the IP** when DNS is the thing that is broken, or when you are not using the site's
  resolver.
- **Where to reach them from:** the management segment (VLAN 99) — the builder, or a laptop on
  the operator port `gi1/0/2`, which gets an address from `10.20.99.200–230`.

**Checked 2026-09-11 from the builder:** every URL below answered, by name and by IP, except
where the Notes say otherwise.

---

## Network

| Service | By name | By IP | Notes |
|---|---|---|---|
| **OPNsense** (core router) | `https://dv02cor002p01.mobile.deevnet.net` | `https://10.20.99.1` | Also `dns.`, `dhcp.`, `gateway.`. Automation uses an API key (`vault_opnsense_api_key`); no web UI login is kept in the vault. |
| **Omada controller** | `https://dv00bld001p01.mobile.deevnet.net:8043/independent/index.html#login` | `https://10.20.99.95:8043/independent/index.html#login` | 6.3 moved the login from `/login`. The Owner login is `vault_omada_owner_*`; automation uses `vault_omada_admin_*`. |
| Omada API docs | `https://dv00bld001p01.mobile.deevnet.net:8043/swagger-ui/index.html` | `https://10.20.99.95:8043/swagger-ui/index.html` | The spec the running controller publishes: `/v3/api-docs/00%20All` ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/)) |
| **Access switch** | `https://dv02acc001p01.mobile.deevnet.net` | `https://10.20.99.10` | Login `vault_switch_*`. A factory-reset switch is at `192.168.0.1` if nothing hands it an address. |
| **Wireless AP** | `https://dv02wap001p01.mobile.deevnet.net` | `https://10.20.99.9` | Standalone web UI while not adopted. A factory-reset AP is at `192.168.0.254`. |
| Travel router | `http://dv02edg001p01.mobile.deevnet.net` | `http://192.168.8.1` | The WAN side, not on a site VLAN |

## Compute

| Service | By name | By IP | Notes |
|---|---|---|---|
| **Proxmox — management hypervisor** | `https://dv02hyp001p01.mobile.deevnet.net:8006` | `https://10.20.99.21:8006` | Also `pve.`. Automation uses an API token (`vault_proxmox_token_*`). |
| **Proxmox — tenant hypervisor** | `https://dv02hyp002p02.mobile.deevnet.net:8006` | `https://10.20.99.22:8006` | Also `pve2.` |

## Management-plane services

| Service | By name | By IP | Notes |
|---|---|---|---|
| **Artifact server** | `http://artifacts.mobile.deevnet.net` | `http://10.20.99.95` | On the builder; also `pxe.`. Firmware is under `/firmware/`, container images under `/container-images/`. |
| **Terraform state (MinIO)**: S3 API | `http://tfstate.mobile.deevnet.net:9000` | `http://10.20.99.31:9000` | On `dv02tst001v01`. Root login `vault_minio_root_*`. |
| Terraform state (MinIO): console | `http://tfstate.mobile.deevnet.net:9001` | `http://10.20.99.31:9001` | |
| **Tenant DNS (PowerDNS)** | `tdns.mobile.deevnet.net` port 53 | `10.20.99.30` port 53 | DNS only; no HTTP API is enabled. Tenants write over RFC 2136 ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)). |
| **MQTT broker** | *not in DNS* | `mqtt://10.20.35.20:1883` (TLS on `8883`) | On `dv02mqt001v01`, IoT Backend. **2026-09-11:** inventory declares `dv02mqt001v01` and `mqtt.`, but neither resolves, and 1883 did not answer from the builder. Users are in `vault_mqtt_users`. |

## Hosts without a web UI

Reach these by SSH as `a_autoprov`.

| Host | By name | By IP | What it is |
|---|---|---|---|
| Builder (roaming) | `dv00bld001p01.mobile.deevnet.net` | `10.20.99.95` | Control node: Ansible, the Omada controller, the artifact server |
| Provisioner VMs | `dv02bld001v01…`, `dv02bld002v01…` | `10.20.99.97`, `10.20.99.96` | Management-plane build VMs |
| SDR Pi | `dv02rpi001p01.mobile.deevnet.net` (also `sdr.`) | `10.20.30.11` | IoT; no HTTP answered on 2026-09-11 |
| Bell gateway | `dv02bgw001e01.mobile.deevnet.net` (also `mabell.`, `bellgw.`) | `10.20.30.50` | IoT (ESP32); no HTTP answered on 2026-09-11 |

## Documentation and code

| What | URL |
|---|---|
| This documentation | `https://deevnet.github.io/deevnet-docs/` |
| Repositories | `https://github.com/deevnet` |
| Omada controller downloads and release notes | `https://support.omadanetworks.com/us/product/omada-software-controller/?resourceType=download` |
| SG2218 (hardware 1.20) firmware | `https://support.omadanetworks.com/us/product/sg2218/v1.20/?resourceType=download` |

---

VLANs, subnets and DHCP ranges are in [Network Reference](network-reference/). Names come from
inventory (`env.interfaces.*.dns` in `host_vars`), and the `dns` role publishes them. If a
declared name does not resolve, check whether the `dns` role has run since the host was added.
