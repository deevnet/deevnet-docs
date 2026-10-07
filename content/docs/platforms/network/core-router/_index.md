---
title: "Core Router"
weight: 2
bookCollapseSection: true
---

# Core Router

Fills the **core router** role — segment routing, firewall, DNS, DHCP and NAT for every segment. See
[Substrate Networking → Core Router Role](/docs/architecture/substrate/networking/#core-router-role).

---

## Hardware

[ZimaBoard 832](/docs/platforms/hardware/network/zimaboard-832/): specs, cabling, power and console.

---

## Operating System

The core router runs OPNsense.

| Attribute | Value |
|-----------|-------|
| **OS** | OPNsense |
| **Version** | [Software Catalog](/docs/platforms/software-catalog/#core-router-opnsense-dv02cor002p01), with the bundled services in use |
| **Base** | FreeBSD |
| **Installation** | Manual, from USB. OPNsense has no network or unattended install; see [Build Network](/docs/runbook/substrate/building-recovery/build-network/) |

---

## Product features in use

Beyond the role itself:

| Feature | Use |
|---------|-----|
| **Wake-on-LAN** | The `os-wol` plugin wakes substrate hosts that are declared `wol: true` in inventory |

---

## Configuration Management

Configured via the `deevnet.net` Ansible collection:

| Component | Management |
|-----------|------------|
| DNS records | Pushed from inventory |
| DHCP static mappings | Substrate hosts: pushed from inventory. Tenants' devices: written by the Deevnet API |
| Firewall rules | Defined in playbooks |
| WoL targets | Defined in inventory |

### DNS: Unbound

Three distinct collections, reconciled from inventory by the `opnsense_dns` role:

| What | OPNsense feature | Used for |
|------|------------------|----------|
| Address records | Host override | `host.mobile.deevnet.net` → address |
| Aliases | Host alias | Service names pointing at a host — stored as CNAMEs |
| Zone forwards | Query Forwarding | Sending a tenant zone to the tenant authoritative service |

**The API shape for Query Forwarding is not where you would look for it, verified on 25.7.10.**
These rows are *not* part of `unbound/settings/get` — that payload's keys are `general`, `advanced`,
`acls`, `dnsbl`, `forwarding`, `dots`, `hosts`, `aliases`, and `forwarding` is the *use system
nameservers* toggle rather than a collection. Forward rows have their own endpoints and are wrapped
in a `dot` object that backs both DNS-over-TLS and plain rows:

```
POST /api/unbound/settings/searchForward
POST /api/unbound/settings/addForward
POST /api/unbound/settings/setForward/<uuid>
POST /api/unbound/settings/delForward/<uuid>

body: {"dot": {"enabled": "1", "type": "forward",
               "domain": "...", "server": "...", "description": "..."}}
```

`type` must be `forward`. The default would attempt DNS-over-TLS against an authoritative server on
port 53.

Changes land in the saved configuration only; the running resolver is not updated until
`POST /api/unbound/service/reconfigure`.

Because these are forwards rather than referrals, the resolver never consults the tenant zone's own
apex records — see
[Naming and Addressing](/docs/architecture/naming-and-addressing/) for what that changes.

### DHCP: Kea

Reservations are generated from inventory and keyed on each host's declared hardware address, which
makes the MAC load-bearing: a guest whose NIC does not carry its declared address does not match its
reservation and silently receives a pool address instead. On the management segment the pool begins
at `.200`, so that failure shows up as a host sitting somewhere in the `.200+` range with no name
pointing at it.

The platform segment has reservations only and no pool at all.

The IoT segment's reservations have two writers. Inventory's rows are described `Ansible managed -
<host>`; the [Deevnet API](/docs/platforms/deevnet-software/deevnet-api/) adds one for each fixed
address a tenant reserves for a device, described `Deevnet API - <tenant>/<device>`
([ADR-0035](/docs/architecture/decisions/edge-devices/0035-fixed-address-for-a-tenant-device/)). Each writer changes
only its own rows, and the DHCP role stops if an inventory host's MAC is already reserved under
another description.

---

## Authority Transition

The core router is the production DNS/DHCP authority. During a greenfield build or a full recovery, the Builder's dnsmasq holds authority instead, and the two are never authoritative at once. The model is in [Builder → Authority Transition](/docs/architecture/builder/#authority-transition). To move authority in either direction, see the [Authority Transition runbook](/docs/runbook/substrate/building-recovery/authority-transition/).
