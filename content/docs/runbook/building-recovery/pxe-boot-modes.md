---
title: "PXE Boot Modes"
weight: 2
---

# PXE Boot Modes

PXE provisioning operates in two modes depending on whether Core Router is available.

**Most operations use Core Router-Authoritative mode.**

---

## Core Router-Authoritative (Normal)

When Core Router is running (standard operation):

1. Core Router Kea provides DHCP with PXE options:
   - `next-server`: 192.168.10.95 (bootstrap node)
   - `boot-file-name`: grubx64.efi
2. Bootstrap node provides TFTP only (no dnsmasq needed)
3. Host PXE boots, gets DHCP from Core Router, TFTP from bootstrap

### Adding a New PXE Host

```bash
# 1. Add DHCP reservation in Core Router (via UI or API)
# 2. Add MAC config to inventory
# 3. Apply bootstrap role
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit bootstrap_nodes
```

See [PXE Boot Infrastructure](/docs/platforms/bootstrap-node/pxe-boot-infrastructure/) for technical details.

---

## Bootstrap-Authoritative (Greenfield Only)

Only for initial substrate buildout when Core Router doesn't exist yet.

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

This enables dnsmasq for DHCP/DNS/TFTP on the bootstrap node.

### Transition Back to Normal Mode

After Core Router is provisioned:

1. Configure Core Router Kea with DHCP reservations and PXE options
2. Transition bootstrap node to TFTP-only mode:

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make core-auth
```

This disables dnsmasq and masquerading, keeping only standalone TFTP.

---

## Mode Comparison

| Aspect | Core Router-Authoritative | Bootstrap-Authoritative |
|--------|---------------------------|-------------------------|
| DHCP | Core Router (Kea) | Bootstrap (dnsmasq) |
| DNS | Core Router | Bootstrap (dnsmasq) |
| TFTP | Bootstrap | Bootstrap (dnsmasq) |
| Use case | Normal operations | Greenfield/full recovery |
