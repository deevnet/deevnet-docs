---
title: "Inventory Setup"
weight: 2
---

# Inventory Setup

Before any host can be PXE booted, its MAC address and host definition must be seeded into inventory.

---

## When This Is Required

- **Greenfield build** - All hosts are new
- **Hardware replacement** - New NIC = new MAC address
- **Capacity expansion** - Adding new hosts

---

## Information Needed

For each host:

| Field | Example | Notes |
|-------|---------|-------|
| Hostname | `pve01.dvntm.deevnet.net` | FQDN |
| MAC address | `aa:bb:cc:dd:ee:ff` | PXE boot interface |
| IP address | `192.168.10.101` | Static assignment |
| Role | `proxmox_hosts` | Inventory group |

---

## Procedure

1. **Collect MAC addresses** from hardware (BIOS/UEFI or label)

2. **Add to Ansible inventory** in the appropriate group:
   ```yaml
   proxmox_hosts:
     hosts:
       pve01.dvntm.deevnet.net:
         ansible_host: 192.168.10.101
         mac_address: "aa:bb:cc:dd:ee:ff"
   ```

3. **Add DHCP reservation** in Core Router (or bootstrap dnsmasq for greenfield):
   - Via Core Router UI/API, or
   - Via `deevnet.net` Ansible collection

4. **Apply bootstrap role** to generate PXE configs:
   ```bash
   cd ~/dvnt/ansible-collection-deevnet.builder
   make rebuild
   ansible-playbook playbooks/site.yml --limit bootstrap_nodes
   ```

---

## Verification

Confirm DHCP reservation exists and PXE config was generated:

```bash
# Check DHCP lease/reservation on Core Router
# Check TFTP directory for host-specific config
ls /srv/tftp/pxelinux.cfg/
```
