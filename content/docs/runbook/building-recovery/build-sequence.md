---
title: "Configure PXE"
weight: 4
---

# Configure PXE

Configure PXE boot authority before provisioning hosts.

---

## Greenfield Build (No Core Router)

For initial substrate build or full recovery, the bootstrap node provides DNS/DHCP/TFTP.

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

This enables dnsmasq for DHCP/DNS/TFTP and configures the bootstrap node as the network gateway.

Proceed to [Build Network](../build-network/) to provision Core Router.

---

## Component Rebuild (Core Router Running)

If Core Router is already operational, no PXE reconfiguration is needed. The bootstrap node provides TFTP only; Core Router handles DHCP with PXE options.

Verify TFTP is running:

```bash
systemctl status tftp.socket
```

Proceed directly to:
- [Build Network](../build-network/) for Core Router rebuild
- [Build Management Plane](../build-management-plane/) for hypervisor rebuild
- [Build Tenants](../build-tenants/) for tenant rebuild

---

## Mode Comparison

| Aspect | Bootstrap-Authoritative | Core-Authoritative |
|--------|-------------------------|---------------------|
| DHCP | Bootstrap (dnsmasq) | Core Router (Kea) |
| DNS | Bootstrap (dnsmasq) | Core Router |
| TFTP | Bootstrap (dnsmasq) | Bootstrap (standalone) |
| Use case | Greenfield / full recovery | Normal operations |
