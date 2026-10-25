---
title: "CHG-0057: Build the Home Site"
weight: -57
---

# CHG-0057: Build the Home Site

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/) and [CHG-0056](/docs/changes/2026/0056-kit-deevnet-or-own-pki/). One ceremony at the factory; the rest on a visit, from the Builder |
| **Site** | home |
| **Systems** | The home site's core router (OPNsense, Unbound), switch and access point; one tenant's Deevnet Pi; the Builder `dv00bld001p01`; the offline ceremony machine |
| **Automation** | `ansible-inventory-deevnet` `home/`; `deevnet.net` and `deevnet.builder` (`substrate_cert`); `deevnet.mgmt` `scripts/pki/` |
| **Risk** | Medium. Most likely to go wrong: the home network is the household's, and a misapplied firewall or DHCP change takes it down. Each step is applied and checked on its own, with the router's configuration exported first |
| **Related changes** | [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (the mobile site's PKI, the pattern here), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (the mobile site's zone policy) |
| **Related incidents** | None |
| **Related runbooks** | [Ceremony](/docs/runbook/root-of-trust/ceremony/), [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) |

---

## Summary

The Mobile Factory builds sites as well as tenants, and home (`home.deevnet.net`, site code `01`) is
the next. This change builds what a site needs to host tenants' Deevnet Pis: its own PKI, its
network from its inventory, and DNS and DHCP on its core router. The Builder comes home and applies
it with Ansible. Home runs no broker, registry or Deevnet API: a Pi is its devices' broker and
registry ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/)
§1, §8; [Home Site](/docs/roadmap/infrastructure/home-site/); review phase P8).

## Goal

- A Home Site CA, signed by the root, held offline; a Home Substrate CA, its key in home's vault,
  signed by the Home Site CA.
- The home inventory declares its hosts, VLANs, firewall policy and Wi-Fi, beside the mobile site's.
- The core router runs DNS (Unbound) and DHCP for `home.deevnet.net`, from the inventory, with a
  certificate from the Home Substrate CA.
- `mqtt.deevnet.net` is not answered at home: there is no site broker.
- A hosted Pi's site-less names and its home site name resolve at home.
- One tenant's Deevnet Pi served at home, its devices connecting to it.

## Scope

**In scope:** home's PKI, inventory, router, switch and access point, one Pi's DNS.
**Out of scope:** Kea, a hypervisor at home, and anything for tenants beyond a Pi's network and names
([Home Site](/docs/roadmap/infrastructure/home-site/), Later).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The household loses its network | home | Each step applied and checked alone; the router's configuration exported first; a change window agreed |
| The wrong inventory applied | the Builder | Every play run with `-i home/` named explicitly and `--limit` |
| A home key written only to a local file | control node | The lock-in rule: vault, encrypt, commit, push before the next step |

## Prerequisites

- [ ] The offline ceremony machine, with its bootloader reset
- [ ] The home inventory's hardware recorded (by model, never by serial)
- [ ] A Deevnet Pi provisioned at the factory for a tenant, its devices' registrations written

## Procedure

### Step 1: Home's PKI

A Home Site CA (ceremony path 2), then a Home Substrate CA: its key in home's vault, its request
signed by the Home Site CA (path 3).

**Verify:** both chain to the root; the Home Site CA carries the same name constraints as the mobile
Site CA.

### Step 2: The inventory

Hosts, VLANs, firewall policy and Wi-Fi in `home/`.

**Verify:** a syntax check and a check-mode run against home report the intended changes only.

### Step 3: The core router

DNS and DHCP from the inventory; its certificate from the Home Substrate CA.

**Verify:** a client on each VLAN gets an address and resolves `home.deevnet.net` names; the router's
UI verifies with the root alone.

### Step 4: The Pi

The Pi's VLAN, firewall and Wi-Fi from the inventory; its names in home's DNS.

**Verify:** a computer reaches the Pi by its site-less name and verifies it; its devices connect.

## Verification

A Deevnet Pi is served at home and its devices connect to it.

## Undo

Each step reverses on its own: the router's exported configuration restored, the inventory's change
reverted and applied. The CAs stay; they cost nothing unused.
