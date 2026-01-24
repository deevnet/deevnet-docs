---
title: "Verify Substrate"
weight: 13
---

# Verify Substrate

Validation after substrate build is complete.

---

## Overview

Each build phase includes automated verification via Ansible. This page covers final validation once all components are operational.

---

## Network Verification

```bash
# Core Router reachable
ping gateway.dvntm.deevnet.net

# DNS resolution working
dig +short hv01.dvntm.deevnet.net
dig +short @192.168.10.1 hv01.dvntm.deevnet.net

# DHCP serving leases
# (check Core Router UI or API)

# VLAN connectivity
# (ping across segments as appropriate)
```

---

## Management Plane Verification

```bash
# Hypervisors reachable
ping hv01.dvntm.deevnet.net
ping hv02.dvntm.deevnet.net

# Proxmox API accessible
curl -k https://hv01.dvntm.deevnet.net:8006/api2/json/version

# SSH access working
ssh hv01.dvntm.deevnet.net hostname
```

---

## PXE Infrastructure Verification

```bash
# TFTP service running
systemctl status tftp.socket

# PXE configs present
ls /srv/tftp/pxelinux.cfg/

# Artifact server accessible
curl -I http://artifacts.dvntm.deevnet.net/fedora/43/mirror/
```

---

## Automated Verification

*TBD - Ansible playbook for full substrate health check*
