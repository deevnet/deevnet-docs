---
title: "CHG-0054: Tenant Names Without a Site"
weight: -54
---

# CHG-0054: Tenant Names Without a Site

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | **In progress.** API v0.15.0 deployed on `dv02prv001v01` and provider v0.8.0 released, 2026-10-25. Steps 2 and 3 dropped. The first certificate was issued with the new names on 2026-10-29 (EdS CHG-0042): V2 and V10 in part, see Outcome |
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
name. This change builds the names,
the reserved labels that keep tenants and sites apart, and issuance under the new rule
([review](/docs/architecture/reviews/2026-10-tenant-pki/), phases P3 and P4).

**The rule after this change:** a tenant certificate's CN and first SAN are the site-less name, and
its site names follow; a tenant cannot take a reserved label.

## Goal

- ~~Each tenant's `<tenant>.deevnet.net` zone, served by tenant DNS and forwarded by the site's
  resolver, answering with this site's deployment.~~ Dropped: site-less names resolve only at
  production sites, and the Mobile Factory is not one (ADR-0040 §1, 2026-10-26).
- The API refuses reserved tenant labels: `home`, `mobile`, `mgmt`, `dvnt`, `dvntm`, `device`, every
  global alias, and `mqtt`. A service label may not be `device`.
- The signing role enforces the same list, so OpenBao refuses a reserved name even if the API asked.
- The API builds each certificate's names from a label and the tenant's sites: the site-less name as
  CN and first SAN, then a site name for each site in the tenant's record.
- A tenant's record lists the sites it runs on and is headed for; the provider sets them.
- ~~`mqtt.deevnet.net` answers with this site's broker, and the broker's certificate, from the Mobile
  Substrate CA, carries it as a SAN.~~ Dropped: there is no bus name; a device dials its own
  tenant's broker (ADR-0040 §5, 2026-10-26).

## Scope

**In scope:** zones, the resolver's forward, the reserved list in the API and the signing role,
issuance, the tenants' site list.
**Out of scope:** reissuing existing tenants (CHG-0055); device certificates and their site-less URI
(CHG-0034); other sites' DNS (CHG-0057).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A tenant takes a site's or an alias's label | the API, the signing role | The list in both; V4 and V10 try each reserved label |
| A new zone shadows a substrate name | tenant DNS, the resolver | Only `<tenant>.deevnet.net` for admitted tenants is forwarded; `mobile.deevnet.net` and the aliases are unchanged |
| Site-named certificates stop working | tenants | Nothing is revoked; they run to expiry and CHG-0055 replaces them |

## Prerequisites

- [x] CHG-0036 complete (the Tenant Service CA re-keyed, under its new name): 2026-10-25
- [ ] The current API, provider and broker certificate noted for the undo

## Procedure

### Step 1: Reserved labels

The API's name check refuses the list; the signing role is given a guard that refuses it.

**Verify:** V4's API half: each reserved label is refused as a tenant name.

### Step 2: The zones and the resolver

**Dropped (2026-10-26).** Site-less names resolve only at production sites
([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) §1). The
Mobile Factory serves a tenant's site zone alone, and a production site answers the site-less names
for what it hosts, as the home network's DNS does for eds's home Pi (EdS CHG-0042).

### Step 3: The bus name

**Dropped (2026-10-26).** Every device belongs to a tenant (ADR-0032) and dials its tenant's broker,
so no site answers `mqtt.deevnet.net` and no broker certificate carries it (ADR-0040 §5).

### Step 4: Issuance

The API and provider release: names built from a label and the tenant's sites, site-less first.

**Verify:** V2 and V10 pass.

## Verification

V2, V4 and V10 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass.

## Undo

The previous API and provider; the zones and forwards removed. Site names were never touched, so
nothing that used them breaks.

## Outcome

Built in [deevnet-provisioning-api#37](https://github.com/deevnet/deevnet-provisioning-api/pull/37)
and released as **v0.15.0**; `sites` on `deevnet_certificate` in
[terraform-provider-deevnet#24](https://github.com/deevnet/terraform-provider-deevnet/pull/24),
released as **v0.8.0**; the signing role and `DEEVNET_CERTIFICATE_SITES` in
[deevnet.mgmt #96](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/96), the sites
(`mobile`, `home`) in [inventory #90](https://github.com/deevnet/ansible-inventory-deevnet/pull/90),
and the version in [deevnet.mgmt #97](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/97).
Deployed 2026-10-25 with `openbao.yml`, then `site.yml --tags deevnet-api --limit deevnet_api`.

| Step | Result |
|---|---|
| 1 | The API refuses the reserved tenant names and the `device` label (unit tests). The signing role: see the departures |
| 2 | Dropped |
| 3 | Dropped |
| 4 | On `dv02prv001v01`, 2026-10-26: `/version` is v0.15.0 (commit `ffaa1e8`), `/readyz` `ok` for the database and OpenBao. The signing role read back with the widened domain after `openbao.yml`. No certificate has yet been issued with the new names, so V2 and V10 wait on the first: eds's home Pi (EdS CHG-0042) |
| 4 | **The first, 2026-10-29** (EdS [CHG-0042](https://cdeever.github.io/eds/docs/changes/2026/0042-the-home-pi-becomes-a-deevnet-pi/)): `deevnet_certificate.backend` for eds, with provider v0.8.0, `name` `mqtt`, `names` `logs`, `grafana`, `console`, `sites` `home` and `mobile`, for a Deevnet Pi's request. Serial `55:c1:0d:cb:…:9d:0a`, valid to 2027-10-28. It named all twelve: each label site-less, then at `eds.home` and `eds.mobile`, CN `mqtt.eds.deevnet.net`, issued by the Tenant Service CA and chaining to the Deevnet Root through the Mobile Site CA |
| V2 | **In part.** Go: `deevnet-kit cert install` verified it for every kit name, and every EdS service on the Pi then dialed `mqtt.eds.deevnet.net`. OpenSSL: `openssl verify -purpose sslserver` against the Root. A browser: the owner's, on a Mac that trusts the Root, opened `console.eds.deevnet.net` and used its controls; `console.eds.home.deevnet.net` answered over TLS to curl. An ESP32: three (a beacon, a cover screen, a light stand) connected to `mqtt.eds.deevnet.net` with only the Root, no firmware change. **Not tried:** a name outside `deevnet.net` failing |
| V10 | **In part.** A browser opened `console.eds.deevnet.net`. **Not tried:** `console.eds.mobile.deevnet.net` with this certificate (at the factory that name is the workload's console, with its own), and none of the refusals: tenant B asking for an `eds` name, a wildcard, a site broker's name, a `device` label |

### Departures from the plan

- **The signing role was widened, not given a guard.** It allows `*.*.deevnet.net`; the API's
  reserved list is what keeps tenant names from site names. The owner accepted that the role alone
  no longer tells the two apart. A role per tenant is a follow-up.
- **A certificate's sites come from the request**, `sites` on `deevnet_certificate`, among the
  site's `DEEVNET_CERTIFICATE_SITES`, not from a site list on the tenant's record (ADR-0040 §3).
- **Step 2 was dropped** by ADR-0040's production-only rule, after the release.
- **Step 3 was dropped**: the bus name is withdrawn (ADR-0040 §5). `mqtt` stays a reserved tenant
  name, since a tenant named so would own a site broker's name.

## Follow-ups

- [ ] A signing role per tenant, so OpenBao refuses a reserved name even if the API asked.

## To discover

- How the signing role enforces the reserved list: a role per tenant written at creation, or a
  constraint OpenBao's roles can express (ADR-0040's open question).
