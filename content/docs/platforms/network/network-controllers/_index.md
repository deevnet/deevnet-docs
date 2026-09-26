---
title: "Network Controllers"
weight: 5
---

# Network Controllers

## Purpose

Network controllers provide **centralized management** for switches and access points. They enable VLAN configuration, firmware updates, and API-based automation across all managed network devices.

{{< mermaid >}}
graph LR
    A[Bootstrap Node<br>hosts controller] <--> B[Network Controller<br>Omada] <--> C[Switches & APs<br>managed devices]
{{< /mermaid >}}

Both controllers run on the **bootstrap node** as containerized services, providing management capability during initial network configuration.

---

## Software Platform

**Site**: mobile (mobile)

The Omada SDN Controller manages all TP-Link Omada devices in the mobile site, including the SG2218 switch and EAP650-Outdoor access point.

### Software

| Attribute | Value |
|-----------|-------|
| **Software** | Omada SDN Controller |
| **Deployment** | Podman container on bootstrap node |
| **Web UI** | Port 8043 (HTTPS) |
| **Discovery** | L2 discovery or manual adoption |

### Managed Devices

| Device | Type |
|--------|------|
| SG2218 | Access Switch |
| EAP650-Outdoor | Access Point |

### Capabilities

| Feature | Description |
|---------|-------------|
| **VLAN Management** | Create VLANs, assign ports, configure trunks |
| **SSID Configuration** | Create SSIDs, map to VLANs, set security |
| **Firmware Updates** | Centralized firmware management |
| **REST API** | Automation via `deevnet.net` Ansible collection |
| **Zero-touch Provisioning** | Devices auto-discover and adopt |

### Automation

The controller is driven through its **documented Open API** — the spec the running controller
serves at `/v3/api-docs` — and not through the undocumented internal API
([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/) §3). Inventory is
the only declaration of site structure; the controller applies it.

| What | How |
|---|---|
| LAN networks, PPSK profiles, SSIDs, the AP's name and address | `deevnet.net` `playbooks/omada-wireless.yml`, via `make wireless` |
| Tenant Wi-Fi keys inside a PPSK profile | the Deevnet API, per tenant ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3) |
| Switch ports and VLANs | not yet adopted — see [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/) |

`make wireless` plans without writing by default; `APPLY=1` writes and `ADOPT=1` also adopts a
pending AP.

#### Two Open API clients, on purpose

An Open API client needs a **global** role, so only the controller's Owner can create one — the
site-scoped automation account cannot. There are two, and they are not interchangeable:

| Client | Used by | Credential |
|---|---|---|
| Ansible's | `omada-wireless.yml` | `vault_omada_openapi_client_id` / `_secret` |
| The Deevnet API's | tenant Wi-Fi key issuance | `vault_omada_api_client_id` / `_secret` |

Both need the same permission — every PPSK write requires site-wide *Network Config Page Modify* —
so this is not about privilege. It is about blast radius, independent rotation, and being able to
tell the two apart in the controller's audit log: revoking the API's client must not stop
`make wireless` working, and revoking Ansible's must not stop tenants issuing keys.

The API reaches the controller over a single declared path, `platform -> management` on 8043 from the
provisioning VM only.

**The controller's event log records device events, not client associations.** It will tell you that
an AP connected or dropped; it will not tell you afterwards whether a client briefly lost its
association. If that matters for a change, watch a client directly while the change runs.

