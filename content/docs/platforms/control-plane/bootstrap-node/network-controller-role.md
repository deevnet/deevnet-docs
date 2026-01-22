---
title: "Network Controller Role"
weight: 4
---

# Network Controller Role

## Purpose

The network controller role deploys **centralized management software** for switches and access points as Podman containers managed by systemd.

---

## Controllers

| Substrate | Controller | Managed Devices |
|-----------|------------|-----------------|
| **dvntm** | TP-Link Omada SDN | SG2218 switch, EAP650-Outdoor AP |
| **dvnt** | Ubiquiti UniFi Network | USW-24-G2, US-8 switches, UAP-AC-M APs |

Both controllers run on the bootstrap node because they must be available for initial network configuration before VLANs exist.

---

## Deployment

| Attribute | Omada (dvntm) | UniFi (dvnt) |
|-----------|---------------|--------------|
| **Container runtime** | Podman | Podman |
| **Web UI port** | 8043 (HTTPS) | 8443 (HTTPS) |
| **Discovery** | L2 discovery | L2 discovery |
| **systemd unit** | omada-controller.service | unifi-controller.service |

### Air-Gapped Installation

Container images are fetched as tarballs from the local artifacts server:

1. Artifacts role downloads image from upstream, saves as tarball
2. Controller role fetches tarball from `http://artifacts.<substrate>.deevnet.net/`
3. `podman load` imports the image
4. `podman create` sets up the container
5. systemd manages the lifecycle

---

## Relationship to Other Roles

| Role | Relationship |
|------|--------------|
| **artifacts** | Provides container image tarballs |
| **base** | System prerequisites |

---

## Details

For full configuration details, managed devices, and API automation, see [Network Controllers](/docs/platforms/network/network-controllers/).
