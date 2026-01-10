---
title: "Building & Recovery"
weight: 1
---

# Building & Recovery

## Overview

Deevnet uses a two-phase model for substrate provisioning:

1. **Online Preparation** - Builder with internet stages all artifacts
2. **Offline Recovery** - Bootstrap rebuilds substrate without internet

---

## Phase 1: Online Preparation

The builder node (with internet access) stages artifacts to the artifact server.

### What Gets Staged

| Artifact | Source | Role/Task |
|----------|--------|-----------|
| Fedora install tree | rsync from Fedora mirrors | `artifacts` role |
| Fedora Server ISO | download.fedoraproject.org | `artifacts` role |
| Proxmox VE ISO | enterprise.proxmox.com | `artifacts` role |
| SSH public keys | Generated locally | `artifacts` role |
| Container images | docker.io, etc. | `artifacts` role |

### Commands

```bash
# From builder node with internet
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit artifact_servers
```

### Verification

After staging, verify artifacts are accessible:

```bash
curl -I http://artifacts.dvntm.deevnet.net/fedora/43/mirror/
curl -I http://artifacts.dvntm.deevnet.net/isos/proxmox/proxmox-ve_8.4-1.iso
```

---

## PXE Boot Modes

PXE provisioning operates in two modes. **Most operations use Core Router-Authoritative mode.**

### Core Router-Authoritative (Normal)

When Core Router is running (standard operation):

1. Core Router Kea provides DHCP with PXE options:
   - `next-server`: 192.168.10.95 (bootstrap node)
   - `boot-file-name`: grubx64.efi
2. Bootstrap node provides TFTP only (no dnsmasq needed)
3. Host PXE boots, gets DHCP from Core Router, TFTP from bootstrap

**To add a new PXE host:**

```bash
# 1. Add DHCP reservation in Core Router (via UI or API)
# 2. Add MAC config to inventory
# 3. Apply bootstrap role
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit bootstrap_nodes
```

See [PXE Boot Infrastructure](/docs/platforms/bootstrap-node/pxe-boot-infrastructure/) for details.

### Bootstrap-Authoritative (Greenfield Only)

Only for initial substrate buildout when Core Router doesn't exist yet:

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

This enables dnsmasq for DHCP/DNS/TFTP. After Core Router is provisioned, transition to Core Router-Authoritative mode and disable dnsmasq.

---

## Phase 2: Offline Recovery

With artifacts staged, the bootstrap node can rebuild the substrate without internet.

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

### Recovery Sequence

**If Core Router is running** (normal recovery):
1. Verify Core Router Kea has correct DHCP reservations with PXE options
2. Verify bootstrap node TFTP is running (`systemctl status tftp.socket`)
3. PXE boot target hosts
4. Hosts install from local artifacts (artifact server)
5. Post-install: Ansible configures services

**If Core Router is down** (full substrate recovery):
1. Bootstrap node connects to substrate network
2. Enable bootstrap-authoritative mode (`make bootstrap-auth`)
3. Start dnsmasq (DHCP/DNS/TFTP) and nginx (artifacts)
4. PXE boot target hosts including Core Router
5. Transition to Core Router-authoritative mode
6. Post-install: Ansible configures services

---

## Air-Gap Status

| Component | Method | Status |
|-----------|--------|--------|
| Proxmox VM template | kickstart + cdrom | Ready |
| Proxmox VE bare metal | embedded answer file | Ready |
| Fedora packages (install) | local mirror/ISO | Ready |
| Core Router | manual | Gap |

---

## Known Gaps

### Core Router

No automated install/recovery exists. Current workaround:

1. Manual reinstall from USB
2. Restore configuration via `deevnet.net` collection API calls

Future options under evaluation:
- USB installer with embedded config.xml
- Alternative firewall solution (whitebox)

### Post-Install Updates

See [Patching](../patching/) for day 2 update considerations.

---

## Set Up VLANs

*TBD - Configure VLAN tagging on switch and Proxmox bridges.*

---

## Rebuild Core Router

*TBD - Reinstall and configure firewall/router.*

---

## Rebuild Proxmox Hypervisor

*TBD - PXE boot and install Proxmox VE from local artifacts.*

---

## Configure Wireless AP

*TBD - Set up SSIDs, guest networks, and VLAN assignments on Omada AP.*

---

## Rebuild Application Tenants

*TBD - Provision tenant VMs and restore application workloads.*
