---
title: "Authority Transition"
weight: 2
---

# Authority Transition Runbook

Procedures for transitioning DNS/DHCP authority between the builder and production network infrastructure.

For the architectural model, see [Core Services Architecture](/docs/architecture/substrate/management-plane/core-services/).

---

## Overview

| Transition | From | To | When |
|------------|------|----|------|
| **Promote to production** | Builder-authoritative | Router-authoritative | After network infrastructure is configured and validated |
| **Revert to bootstrap** | Router-authoritative | Builder-authoritative | Before substrate rebuild or recovery |

---

## Promote to Production

Transfer DNS/DHCP authority from the builder to production network infrastructure.

### Prerequisites

- [ ] Production network infrastructure is online and reachable
- [ ] DNS records are configured in the production router
- [ ] DHCP scopes are configured in the production router
- [ ] All substrate hosts can reach the production gateway

### Steps

1. **Verify production DNS** — Confirm all `mgmt.deevnet.net` records resolve correctly from the production router
2. **Verify production DHCP** — Confirm static mappings and dynamic pools are configured
3. **Disable builder DNS/DHCP** — Stop dnsmasq (or equivalent) on the builder
4. **Reconfigure builder IP** — Move the builder from the gateway IP to its reserved IP
5. **Validate resolution** — From a substrate host, confirm DNS resolution via the production router
6. **Validate DHCP** — Confirm a test host receives the correct lease from the production router
7. **Record transition** — Log the transition with timestamp and operator

### Rollback

If validation fails at any step, re-enable the builder's DNS/DHCP services and restore its gateway IP.

---

## Revert to Bootstrap

Transfer DNS/DHCP authority from production network infrastructure back to the builder.

### Prerequisites

- [ ] Builder is online and connected to the management segment
- [ ] Builder's DNS/DHCP configuration is current (matches inventory)
- [ ] Artifacts are staged on the builder

### Steps

1. **Disable production DNS/DHCP** — Remove or disable DNS/DHCP services on the production router (if it is still operational)
2. **Reconfigure builder IP** — Move the builder to the gateway IP for the management segment
3. **Enable builder DNS/DHCP** — Start dnsmasq (or equivalent) on the builder
4. **Validate resolution** — From a substrate host, confirm DNS resolution via the builder
5. **Validate PXE** — Confirm a test host can PXE boot from the builder
6. **Record transition** — Log the transition with timestamp and operator

### Rollback

Re-enable production router DNS/DHCP and return the builder to its reserved IP.
