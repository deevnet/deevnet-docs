---
title: "Network Controllers"
weight: 5
---

# Network Controllers

## Purpose

Network controllers provide **centralized management** for switches and access points. They enable VLAN configuration, firmware updates, and API-based automation across all managed network devices.

{{< mermaid >}}
graph LR
    A[Bootstrap Node<br>hosts controller] <--> B[Network Controller<br>Omada/UniFi] <--> C[Switches & APs<br>managed devices]
{{< /mermaid >}}

Both controllers run on the **bootstrap node** as containerized services, providing management capability during initial network configuration.

---

## TP-Link Omada SDN Controller

**Substrate**: dvntm (mobile)

The Omada SDN Controller manages all TP-Link Omada devices in the mobile substrate, including the SG2218 switch and EAP650-Outdoor access point.

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

The Omada controller provides a REST API used by the `deevnet.net` Ansible collection:

| Component | Module/Role |
|-----------|-------------|
| Switch ports | `omada_switch_port` |
| VLANs | `omada_vlan` |
| SSIDs | `omada_ssid` |

---

## Ubiquiti UniFi Network Application

**Substrate**: dvnt (home)

The UniFi Network Application manages all Ubiquiti UniFi devices in the home substrate, including the USW-24-G2 and US-8 switches, and both UAP-AC-M access points.

### Software

| Attribute | Value |
|-----------|-------|
| **Software** | UniFi Network Application |
| **Deployment** | Podman container on bootstrap node |
| **Web UI** | Port 8443 (HTTPS) |
| **Discovery** | L2 discovery or manual adoption |

### Managed Devices

| Device | Type | Quantity |
|--------|------|----------|
| USW-24-G2 | Access Switch (primary) | 1 |
| US-8 | Access Switch (secondary) | 1 |
| UAP-AC-M | Access Point | 2 |

### Capabilities

| Feature | Description |
|---------|-------------|
| **VLAN Management** | Create networks, assign port profiles |
| **SSID Configuration** | Create WLANs, map to networks, set security |
| **Firmware Updates** | Centralized firmware management |
| **REST API** | Automation via UniFi API |
| **Zero-touch Provisioning** | Devices auto-discover and adopt |

### Automation

The UniFi controller provides a REST API. Automation is currently manual but planned:

| Component | Status |
|-----------|--------|
| Switch ports | Manual (API available) |
| VLANs/Networks | Manual (API available) |
| WLANs | Manual (API available) |

---

## Controller Comparison

| Feature | Omada SDN (dvntm) | UniFi Network (dvnt) |
|---------|-------------------|----------------------|
| **Managed switches** | SG2218 | USW-24-G2, US-8 |
| **Managed APs** | EAP650-Outdoor | UAP-AC-M (x2) |
| **Web UI port** | 8043 | 8443 |
| **API** | REST | REST |
| **Ansible support** | `deevnet.net` collection | Planned |
| **Container runtime** | Podman | Podman |
