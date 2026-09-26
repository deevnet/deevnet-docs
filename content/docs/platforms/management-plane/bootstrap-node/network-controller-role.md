---
title: "Network Controller Role"
weight: 4
---

# Network Controller Role

## Purpose

The network controller role deploys **centralized management software** for switches and access points as Podman containers managed by systemd.

---

## Controllers

| Controller | Managed Devices |
|------------|-----------------|
| TP-Link Omada SDN | EAP650-Outdoor AP (adopted); the SG2218 switch is standalone until [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/) |

The controller must be available for initial network configuration, before VLANs exist, so the
bootstrap node can run it. Since [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) it runs
on `dv02nms001v01`, and the bootstrap node keeps a stopped cold spare for when that VM is down.

---

## Deployment

| Attribute | Omada |
|-----------|-------|
| **Container runtime** | Podman |
| **Web UI port** | 8043 (HTTPS) |
| **Discovery** | L2 discovery |
| **systemd unit** | omada-controller.service |

### Air-Gapped Installation

Container images are fetched as tarballs from the local artifacts server:

1. Artifacts role downloads image from upstream, saves as tarball
2. Controller role fetches tarball from `http://artifacts.<site>.deevnet.net/`
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
