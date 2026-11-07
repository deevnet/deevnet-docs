---
title: "CHG-0055: Existing Tenants Reissued Under Site-Less Names"
weight: -55
---

# CHG-0055: Existing Tenants Reissued Under Site-Less Names

| | |
|---|---|
| **Date** | 2026-11-01 |
| **Change type** | Configuration · Migration |
| **Classification** | Routine |
| **Status** | Complete |
| **Window** | Unscheduled. After [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/); one work session, each tenant's apply |
| **Site** | mobile |
| **Systems** | Tenant `eds`: its DNS, its certificate, its workload's proxy |
| **Automation** | Each tenant's Terraform, from its own repository |
| **Risk** | Low. Most likely to go wrong: a tenant's code still dials a site name that a new certificate no longer carries. The site name stays as a SAN, so nothing that works today stops |
| **Related changes** | [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |
| **Related incidents** | None |
| **Related runbooks** | [Deploy Your App](/docs/runbook/tenant/deploy-your-app/) |

---

## Summary

CHG-0054 makes the API issue site-less names. The four tenants on the site were admitted before it:
their records list no sites, and the one tenant service certificate issued so far, `eds`'s console,
is under its site name and the old Tenant Service CA. This change has `eds` set its sites and ask
for its certificate again, so it serves `console.eds.deevnet.net` with its site name
beside it ([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P5).

## Goal

- `eds` names its sites on its certificate (`sites`, CHG-0054).
- Its site names resolve on the Mobile Factory, and its site-less names only where it runs
  in production (ADR-0040 §1).
- `eds`'s console holds a certificate from the re-keyed Tenant Service CA, its CN the site-less name,
  its site name as a SAN, and serves both.
- CHG-0047's probe certificates from the old CA are left to expire.

## Scope

**In scope:** `eds`'s record, certificate and DNS.
**Out of scope:** `tdemo`, `mabell` and `cdeever`, which hold no tenant service certificate: each
names its sites when it is next worked on. Devices (CHG-0034); moving any tenant to another site.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A tenant service dialed by its site name fails | tenants | The site name is a SAN on the new certificate |
| A tenant's apply needs secrets it no longer holds | tenants | Each tenant's state checked before its apply; nothing here re-mints a secret |

## Prerequisites

- [ ] CHG-0054 complete
- [ ] OpenBao open for a work session
- [ ] Each tenant's repository at its current tag, with the provider release from CHG-0054

## Procedure

### Step 1: The tenant

Update the provider, set each certificate's `sites`, apply.

**Verify:** a browser opens `console.eds.mobile.deevnet.net` with a certificate chained to the root
that also names `console.eds.deevnet.net`.

## Verification

`eds`'s site names resolve on the Mobile Factory, and its tenant service certificate is from the
re-keyed Tenant Service CA under its site-less name.

## Undo

The old site-named certificates stay valid until they expire. A tenant's previous apply restores its
previous certificate.

## Outcome

| Tenant | Result |
|---|---|
| `eds` | **2026-11-01** (EdS [CHG-0047](https://cdeever.github.io/eds/docs/changes/2026/0047-the-tenant-switches-spotify-and-names-its-console-without-a-site/)). Provider v0.8.0; `deevnet_certificate.console` given `sites = ["mobile"]`, updated in place for the same key. Serial `24:d7:34:39:…:36:1b`, valid to 2027-11-01, for `console.eds.deevnet.net` and `console.eds.mobile.deevnet.net`, deployed to the workload. Served from `10.20.130.10`, it verified to the Root for both names under OpenSSL 4.0.3, Go 1.27.2 and curl; `console.eds.deevnet.net` was reached with `--resolve`, since the factory does not resolve site-less names (ADR-0040 §1) |
| `tdemo`, `mabell`, `cdeever` | Out of scope since 2026-11-07: each names its sites when it is next worked on |
