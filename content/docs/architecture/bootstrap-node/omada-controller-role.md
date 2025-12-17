---
title: "Omada Controller Role"
weight: 3
---

# Omada Controller Role

## Purpose

The `omada_controller` role deploys the **TP-Link Omada Software Controller** as a Podman container managed by systemd. This controller manages TP-Link network devices (switches, access points).

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Omada Controller              │
│         (Podman container)              │
├─────────────────────────────────────────┤
│  systemd unit: omada-controller.service │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐  ┌─────────────────┐
│  Omada Switch   │  │  Omada AP       │
│  (24-port)      │  │  (wireless)     │
└─────────────────┘  └─────────────────┘
```

---

## Container Configuration

| Setting | Value |
|---------|-------|
| **Image** | `docker.io/mbentley/omada-controller:5.12` |
| **Container name** | `omada-controller` |
| **Data root** | `/opt/omada-controller/` |

### Persistent Volumes

| Host Path | Container Path |
|-----------|----------------|
| `/opt/omada-controller/data` | `/opt/tplink/EAPController/data` |
| `/opt/omada-controller/work` | `/opt/tplink/EAPController/work` |
| `/opt/omada-controller/logs` | `/opt/tplink/EAPController/logs` |

---

## Network Ports

### Management Portal

| Port | Protocol | Purpose |
|------|----------|---------|
| 8088 | TCP | HTTP management |
| 8043 | TCP | HTTPS management |
| 8843 | TCP | Portal HTTPS redirector |

### Device Discovery & Adoption

| Port | Protocol | Purpose |
|------|----------|---------|
| 29810 | UDP | Controller discovery (v1) |
| 29811-29813 | TCP | Manager connection (v1) |
| 29814 | UDP | Controller discovery (v2) |
| 27001 | UDP | Device discovery |
| 27002 | TCP | Device adoption |

---

## Deployment Model

### Air-Gapped Installation

The container image is fetched as a tarball from the local artifacts server:

1. Artifacts role downloads image from upstream, saves as tarball
2. Omada role fetches tarball from `http://artifacts.<substrate>.deevnet.net/`
3. `podman load` imports the image
4. `podman create` sets up the container
5. systemd manages the lifecycle

### Systemd Integration

```
/etc/systemd/system/omada-controller.service
```

- Enabled by default
- Starts on boot
- Restart policy for reliability

---

## Firewall Configuration

The role configures firewalld to allow:

**TCP:** 8088, 8043, 8843, 29811, 29812, 29813, 27002

**UDP:** 29810, 29814, 27001

---

## Managed Devices

In the dvntm substrate:

| Device | Type |
|--------|------|
| 24-port Omada switch | Network switching |
| TP-Link wireless AP | WiFi access |

---

## Relationship to Other Roles

| Role | Relationship |
|------|--------------|
| **artifacts** | Provides container image tarball |
| **base** | System prerequisites |
