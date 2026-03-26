---
title: "Configure PXE"
weight: 4
---

# Configure PXE

Configure PXE boot authority before provisioning hosts.

---

## Greenfield Build (No Core Router)

For initial site build or full recovery, the bootstrap node provides DNS/DHCP/TFTP for the management subnet.

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

This:
- Discovers the WAN interface from inventory (`bootstrap_wan_interface_key`)
- Enables IP forwarding and masquerading on the WAN interface
- Activates dnsmasq for DHCP/DNS/TFTP on the downstream (management) interface
- Populates DNS host records and DHCP static reservations from inventory
- Swaps the management interface IP from the reserved address to the gateway address

The IP swap is the last step — it drops the SSH connection. All configuration completes first while connectivity is stable. Reconnect at the gateway IP to verify.

The WAN interface, DHCP range, gateway IP, and DNS domain are all inventory-driven — no code changes are needed when switching between sites.

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
