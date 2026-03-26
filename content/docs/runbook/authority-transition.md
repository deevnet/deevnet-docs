---
title: "Authority Transition"
weight: 2
---

# Authority Transition Runbook

Procedures for transitioning DNS/DHCP authority between the builder and production network infrastructure.

For the architectural model, see [Core Services Architecture](/docs/architecture/substrate/management-plane/core-services/).

{{< hint info >}}
**Build context:** During a greenfield build, these transitions happen as part of the [Building Infrastructure](/docs/runbook/building-recovery/) sequence — [Configure PXE](/docs/runbook/building-recovery/build-sequence/) enters bootstrap-authoritative mode, and [Build Network](/docs/runbook/building-recovery/build-network/) transitions to core-authoritative mode. This page is the standalone reference for both directions.
{{< /hint >}}

---

## Overview

| Transition | From | To | When |
|------------|------|----|------|
| **Promote to production** | Builder-authoritative | Router-authoritative | After network infrastructure is configured and validated |
| **Revert to bootstrap** | Router-authoritative | Builder-authoritative | Before substrate rebuild or recovery |

Both transitions are automated via playbooks in `deevnet.builder` and `deevnet.net`. The IP swap is the final step in each playbook and drops the SSH connection — reconnect at the new IP to verify.

All site-specific values (IPs, domains, interfaces) come from inventory. No code changes are needed when switching between sites.

---

## Promote to Production

Transfer DNS/DHCP authority from the builder to production network infrastructure.

### Prerequisites

- [ ] Production network infrastructure (OPNsense) is online and reachable
- [ ] DNS records are configured on the router (`deevnet.net` dns.yml)
- [ ] DHCP scopes and reservations are configured on the router (`deevnet.net` dhcp.yml)
- [ ] All substrate hosts can reach the production gateway

### Steps

1. **Transition builder to TFTP-only mode:**
   ```bash
   cd ~/dvnt/ansible-collection-deevnet.builder
   make core-auth
   ```
   This disables dnsmasq, stops masquerading, installs standalone TFTP, and swaps the builder's IP from the gateway address to its reserved address. The SSH connection will drop.

2. **Verify from the builder** (reconnect at reserved IP):
   ```bash
   # dnsmasq should be stopped
   systemctl status dnsmasq

   # TFTP should be running
   systemctl status tftp.socket

   # DNS should resolve via the core router
   dig artifacts.dvntm.deevnet.net
   ```

3. **Verify transition log:**
   ```bash
   cat /var/log/authority-transitions.log
   ```

### Rollback

If validation fails, re-enable bootstrap-authoritative mode:
```bash
make bootstrap-auth
```

---

## Revert to Bootstrap

Transfer DNS/DHCP authority from production network infrastructure back to the builder.

### Prerequisites

- [ ] Builder is online and connected to the management segment
- [ ] Builder's inventory is current (host MACs, IPs match reality)
- [ ] Artifacts are staged on the builder

### Steps

1. **Disable OPNsense DNS/DHCP** (if the router is still operational):
   ```bash
   cd ~/dvnt/ansible-collection-deevnet.net
   ansible-playbook playbooks/disable-opnsense-services.yml --ask-vault-pass
   ```
   If the router is down or unreachable, skip this step.

2. **Enable bootstrap-authoritative mode on the builder:**
   ```bash
   cd ~/dvnt/ansible-collection-deevnet.builder
   make bootstrap-auth
   ```
   This enables dnsmasq with DNS host records and DHCP reservations from inventory, configures masquerading on the WAN interface, and swaps the builder's IP from the reserved address to the gateway address. The SSH connection will drop.

3. **Verify from the builder** (reconnect at gateway IP):
   ```bash
   # dnsmasq should be running
   systemctl status dnsmasq

   # DNS should resolve via the builder
   dig artifacts.dvntm.deevnet.net @localhost

   # TFTP should be available
   systemctl status dnsmasq   # dnsmasq provides TFTP in this mode
   ```

4. **Verify transition log:**
   ```bash
   cat /var/log/authority-transitions.log
   ```

### Rollback

Re-enable OPNsense services and return the builder to production mode:
```bash
cd ~/dvnt/ansible-collection-deevnet.net
ansible-playbook playbooks/enable-opnsense-services.yml --ask-vault-pass

cd ~/dvnt/ansible-collection-deevnet.builder
make core-auth
```

---

## Mode Comparison

| Aspect | Bootstrap-Authoritative | Core-Authoritative |
|--------|-------------------------|---------------------|
| DHCP | Builder (dnsmasq) | Core Router (Kea) |
| DNS | Builder (dnsmasq) | Core Router (Unbound) |
| TFTP | Builder (dnsmasq) | Builder (standalone tftpd) |
| Builder IP | Gateway address (.1) | Reserved address (.95) |
| Default gateway | Builder | Core Router |
| Masquerading | Enabled (WAN interface) | Disabled |
| Use case | Greenfield / full recovery | Normal operations |

---

## Transition Log

Both playbooks append to `/var/log/authority-transitions.log` with timestamp, direction, and operator. Example:

```
2026-03-26T14:30:00+00:00 PROMOTE bootstrap-authoritative by cdeever on provisioner-ph01
2026-03-26T15:45:00+00:00 REVERT core-authoritative by cdeever on provisioner-ph01
```
