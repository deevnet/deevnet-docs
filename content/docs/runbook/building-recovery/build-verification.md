---
title: "Verify Site"
weight: 14
---

# Verify Site

Validation after site build is complete.

---

## Overview

Each build phase includes automated verification via Ansible. This page covers final validation once all components are operational.

---

## Network Verification

```bash
# Core Router reachable
ping gateway.mobile.deevnet.net

# DNS resolution working
dig +short hv01.mobile.deevnet.net
dig +short @192.168.10.1 hv01.mobile.deevnet.net

# DHCP serving leases
# (check Core Router UI or API)

# VLAN connectivity
# (ping across segments as appropriate)
```

---

## Management Plane Verification

```bash
# Hypervisors reachable
ping hv01.mobile.deevnet.net
ping hv02.mobile.deevnet.net

# Proxmox API accessible
curl -k https://hv01.mobile.deevnet.net:8006/api2/json/version

# SSH access working
ssh hv01.mobile.deevnet.net hostname
```

---

## PXE Infrastructure Verification

```bash
# TFTP service running
systemctl status tftp.socket

# PXE configs present
ls /srv/tftp/pxelinux.cfg/

# Artifact server accessible
curl -I http://artifacts.mobile.deevnet.net/fedora/43/mirror/
```

---

## Automated Verification

*TBD - Ansible playbook for full substrate health check*
