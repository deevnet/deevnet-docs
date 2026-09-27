---
title: "Network Controllers"
weight: 5
---

# Network Controllers

Fills the **network management** domain of the management plane — see
[Management Plane → Network management](/docs/architecture/substrate/management-plane/#network-management).

The controller runs in the network management domain VM, `dv02nms001v01`. The Builder keeps a
stopped copy with its data as a cold fallback for when the management hypervisor is down.

---

## Software Platform

**Site**: mobile (mobile)

The Omada SDN Controller manages all TP-Link Omada devices in the mobile site, including the SG2218 switch and EAP650-Outdoor access point.

### Software

| Attribute | Value |
|-----------|-------|
| **Software** | Omada SDN Controller |
| **Deployment** | Podman container on `dv02nms001v01`, `deevnet.mgmt` role `omada_controller` |
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
| **Open API** | Automation via the `deevnet.net` Ansible collection, and tenant Wi-Fi keys via the Deevnet API |
| **Zero-touch Provisioning** | Devices auto-discover and adopt |

### Automation

The controller is driven through its **documented Open API** — the spec the running controller
serves at `/v3/api-docs` — and not through the undocumented internal API
([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/) §3). Inventory is
the only declaration of site structure; the controller applies it.

| What | How |
|---|---|
| LAN networks, PPSK profiles, SSIDs, the AP's name and address | `deevnet.net` `omada-wireless.yml` ([how to run it](/docs/runbook/substrate/building-recovery/build-network/#wireless)) |
| Tenant Wi-Fi keys inside a PPSK profile | the Deevnet API, per tenant ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3) |
| Switch ports and VLANs | not yet adopted — see [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/) |

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
the wireless playbook working, and revoking Ansible's must not stop tenants issuing keys.

The API reaches the controller over a single declared path, `platform -> management` on 8043 from the
provisioning VM only.
