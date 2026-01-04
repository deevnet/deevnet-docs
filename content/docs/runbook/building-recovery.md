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

## Enable Bootstrap-Authoritative Mode

Before PXE booting substrate hosts, enable the bootstrap node as the DNS/DHCP authority for the network.

This makes the bootstrap node the gateway and DNS forwarder for 192.168.10.0/23, bypassing OPNsense during initial provisioning.

### Commands

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

This runs the `bootstrap-authoritative.yml` playbook which:

- Enables dnsmasq for DHCP (192.168.10.100-192.168.11.254) and DNS forwarding
- Configures IP forwarding and NAT on the WAN interface
- Makes the provisioner (192.168.10.95) the gateway for substrate hosts

### Verification

```bash
# Check dnsmasq is running
systemctl status dnsmasq

# Verify DHCP is listening
ss -ulnp | grep :67

# Test DNS forwarding
dig @192.168.10.95 google.com
```

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

1. Bootstrap node connects to substrate network
2. Start dnsmasq (DHCP/DNS/TFTP) and nginx (artifacts)
3. PXE boot target hosts
4. Hosts install from local artifacts (ISO/cdrom)
5. Post-install: Ansible configures services

---

## Air-Gap Status

| Component | Method | Status |
|-----------|--------|--------|
| Proxmox VM template | kickstart + cdrom | Ready |
| Proxmox VE bare metal | embedded answer file | Ready |
| Fedora packages (install) | local mirror/ISO | Ready |
| OPNsense | manual | Gap |

---

## Known Gaps

### OPNsense

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
