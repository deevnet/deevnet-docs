---
title: "Build Sequence"
weight: 4
---

# Build Sequence

With artifacts pre-staged and inventory seeded, the bootstrap node can build the substrate without internet access.

---

## Build Order

When building the full substrate, follow this order:

1. **Network** - Core Router, VLANs, wireless (see [Build Network](../build-network/))
2. **Management Plane** - Proxmox hypervisors (see [Build Management Plane](../build-management-plane/))
3. **Application Tenants** - Workloads (see [Build Tenants](../build-tenants/))

---

## Normal Build (Core Router Running)

Use this when Core Router is already operational.

1. Verify Core Router Kea has correct DHCP reservations with PXE options
2. Verify bootstrap node TFTP is running:
   ```bash
   systemctl status tftp.socket
   ```
3. PXE boot target hosts
4. Hosts install from local artifacts (artifact server)
5. Post-install: Run Ansible to configure services

---

## Greenfield Build (No Core Router)

Use this for initial infrastructure build or full recovery.

1. Bootstrap node connects to substrate network
2. Enable bootstrap-authoritative mode:
   ```bash
   make bootstrap-auth
   ```
3. Start dnsmasq (DHCP/DNS/TFTP) and nginx (artifacts)
4. Build Core Router first (manual USB install)
5. Configure Core Router and transition to normal mode
6. PXE boot remaining hosts
7. Post-install: Run Ansible to configure services

---

## Install Methods by Component

### Proxmox VM Templates (Fedora)

PXE boot triggers kickstart which uses `cdrom` source (no network packages):

- Packages installed from ISO
- SSH key fetched from artifact server (internal network)
- No external internet required

**Key file:** `deevnet-image-factory/packer/proxmox/fedora-base-image/http/kickstart.cfg`

### Proxmox VE Bare Metal

Boot customized ISO with embedded answer file:

- All credentials baked into answer file at ISO build time
- SSH keys embedded, no fetch required
- No external internet required during install

**Key files:**
- `deevnet-image-factory/packer/proxmox/pve-iso/answer-zfs.toml.template`
- `deevnet-image-factory/packer/proxmox/pve-iso/answer-ext4.toml.template`
