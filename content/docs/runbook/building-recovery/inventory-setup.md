---
title: "Inventory Setup"
weight: 2
---

# Inventory Setup

Before any host can be PXE booted, its definition must exist in the Ansible inventory. MAC addresses, IP assignments, DNS records, and DHCP reservations are all driven from host_vars.

**Repository:** `ansible-inventory-deevnet`

---

## When This Is Required

| Scenario | Action |
|----------|--------|
| Capacity expansion | Add host to `hosts.yml`, create new `host_vars/<hostname>.yml` |
| Hardware replacement | Update MAC address in existing `host_vars/<hostname>.yml` |
| Greenfield build | All hosts need both steps |

---

## Inventory Structure

```
ansible-inventory-deevnet/
└── dvntm/
    ├── hosts.yml           # Main inventory (hosts and group memberships)
    ├── group_vars/         # Variables by group
    └── host_vars/          # Per-host variables (MAC, IP, DNS, DHCP)
        ├── hv01.yml
        ├── hv02.yml
        └── ...
```

---

## Adding a New Host (Expansion)

### 1. Add to hosts.yml

Add the hostname to appropriate groups:

```yaml
hypervisors:
  hosts:
    hv01: {}
    hv02: {}
    hv03: {}    # new host
```

### 2. Create host_vars file

Create `host_vars/<hostname>.yml` with infrastructure and environment data:

```yaml
infrastructure:
  form: hv
  interfaces:
    eth0:
      mac: "aa:bb:cc:dd:ee:ff"

env:
  interfaces:
    eth0:
      ip: 192.168.10.23
      purpose: mgmt
      segment: management
      dns:
        host_a_record: true
        dhcp_reservation: true
        cnames:
          - pve3
```

### 3. Apply configuration

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit bootstrap_nodes
```

This generates PXE configs and pushes DNS/DHCP to Core Router.

---

## Updating for Hardware Replacement

When replacing hardware (new NIC = new MAC address), update the existing host_vars file:

```yaml
infrastructure:
  interfaces:
    eth0:
      mac: "new:ma:ca:dd:re:ss"   # updated MAC
```

Then apply configuration as above.

---

## Host Variables Reference

| Path | Purpose |
|------|---------|
| `infrastructure.form` | Device type (hv, rt, sw, ap, etc.) |
| `infrastructure.interfaces.<iface>.mac` | MAC address |
| `env.interfaces.<iface>.ip` | IP address (or `dhcp`) |
| `env.interfaces.<iface>.segment` | Network segment name |
| `env.interfaces.<iface>.dns.host_a_record` | Create DNS A record |
| `env.interfaces.<iface>.dns.dhcp_reservation` | Create DHCP reservation |
| `env.interfaces.<iface>.dns.cnames` | List of CNAME aliases |

