---
title: "CHG-0054: Tenant Names Without a Site"
weight: -54
---

# CHG-0054: Tenant Names Without a Site

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (the re-keyed Tenant Service CA); one API release, one provider release, Ansible runs for DNS, the resolver, OpenBao and the broker |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02idn001v01` (tenant DNS, OpenBao), the core router (Unbound), `dv02msg001v01` (the broker); the provider |
| **Automation** | `deevnet-provisioning-api`, `terraform-provider-deevnet`; `deevnet.mgmt` `site.yml --tags tenant-dns,openbao,deevnet-api,vernemq`; `deevnet.net` for the resolver |
| **Risk** | Medium. Most likely to go wrong: a tenant label that collides with a site or an alias gets through the signing role, and a tenant certificate answers for a substrate name |
| **Related changes** | [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) (built issuance under site names), [CHG-0055](/docs/changes/2026/0055-reissue-tenants-site-less/) (reissues the tenants after this) |
| **Related incidents** | None |
| **Related runbooks** | [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

A tenant service is named under its site today, `console.eds.mobile.deevnet.net`.
[ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) names it
`console.eds.deevnet.net` for its whole life, with each site it runs on or is headed for as an extra
name, and devices dial one bus name, `mqtt.deevnet.net`, at every site. This change builds the names,
the reserved labels that keep tenants and sites apart, and issuance under the new rule
([review](/docs/architecture/reviews/2026-10-tenant-pki/), phases P3 and P4).

**The rule after this change:** a tenant certificate's CN and first SAN are the site-less name, and
its site names follow; a tenant cannot take a reserved label.

## Goal

- Each tenant's `<tenant>.deevnet.net` zone, served by tenant DNS and forwarded by the site's
  resolver, answering with this site's deployment.
- The API refuses reserved tenant labels: `home`, `mobile`, `mgmt`, `dvnt`, `dvntm`, `device`, every
  global alias, and the bus name. A service label may not be `device`.
- The signing role enforces the same list, so OpenBao refuses a reserved name even if the API asked.
- The API builds each certificate's names from a label and the tenant's sites: the site-less name as
  CN and first SAN, then a site name for each site in the tenant's record.
- A tenant's record lists the sites it runs on and is headed for; the provider sets them.
- `mqtt.deevnet.net` answers with this site's broker, and the broker's certificate, from the Mobile
  Substrate CA, carries it as a SAN.

## Scope

**In scope:** zones, the resolver's forward, the reserved list in the API and the signing role,
issuance, the tenants' site list, the bus name.
**Out of scope:** reissuing existing tenants (CHG-0055); device certificates and their site-less URI
(CHG-0034); other sites' DNS (CHG-0057).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A tenant takes a site's or an alias's label | the API, the signing role | The list in both; V4 and V10 try each reserved label |
| A new zone shadows a substrate name | tenant DNS, the resolver | Only `<tenant>.deevnet.net` for admitted tenants is forwarded; `mobile.deevnet.net` and the aliases are unchanged |
| A broker certificate change drops devices | the broker | The bus name is added beside the existing names; nothing is removed |
| Site-named certificates stop working | tenants | Nothing is revoked; they run to expiry and CHG-0055 replaces them |

## Prerequisites

- [ ] CHG-0036 complete (the Tenant Service CA re-keyed, under its new name)
- [ ] The current API, provider and broker certificate noted for the undo

## Procedure

### Step 1: Reserved labels

The API's name check refuses the list; the signing role is given a guard that refuses it.

**Verify:** V4's API half: each reserved label is refused as a tenant name.

### Step 2: The zones and the resolver

Tenant DNS serves `<tenant>.deevnet.net` for each admitted tenant; the resolver forwards each.

**Verify:** `console.eds.deevnet.net` resolves on the site to eds's console.

### Step 3: The bus name

`mqtt.deevnet.net` in the site's DNS; the broker's certificate reissued with it as a SAN.

**Verify:** a client dialing `mqtt.deevnet.net` verifies the broker with the root alone.

### Step 4: Issuance

The API and provider release: names built from a label and the tenant's sites, site-less first.

**Verify:** V2 and V10 pass.

## Verification

V2, V4 and V10 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass.

## Undo

The previous API and provider; the zones and forwards removed. Site names were never touched, so
nothing that used them breaks.

## To discover

- How the signing role enforces the reserved list: a role per tenant written at creation, or a
  constraint OpenBao's roles can express (ADR-0040's open question).
