---
title: "CHG-0055: Existing Tenants Reissued Under Site-Less Names"
weight: -55
---

# CHG-0055: Existing Tenants Reissued Under Site-Less Names

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration · Migration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/); one work session, each tenant's apply |
| **Site** | mobile |
| **Systems** | Tenants `eds`, `tdemo`, `mabell` and `cdeever`: their DNS, their certificates, their workloads' proxies |
| **Automation** | Each tenant's Terraform, from its own repository |
| **Risk** | Low. Most likely to go wrong: a tenant's code still dials a site name that a new certificate no longer carries. The site name stays as a SAN, so nothing that works today stops |
| **Related changes** | [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |
| **Related incidents** | None |
| **Related runbooks** | [Deploy Your App](/docs/runbook/tenant/deploy-your-app/) |

---

## Summary

CHG-0054 makes the API issue site-less names. The four tenants on the site were admitted before it:
their records list no sites, and the one tenant service certificate issued so far, `eds`'s console,
is under its site name and the old Tenant Service CA. This change sets each tenant's sites and has
`eds` ask for its certificate again, so it serves `console.eds.deevnet.net` with its site name
beside it ([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P5).

## Goal

- `eds`, `tdemo`, `mabell` and `cdeever` each list their sites in their records.
- Each tenant's site-less names resolve on the site.
- `eds`'s console holds a certificate from the re-keyed Tenant Service CA, its CN the site-less name,
  its site name as a SAN, and serves both.
- CHG-0047's probe certificates from the old CA are left to expire.

## Scope

**In scope:** the four tenants' records, certificates and DNS.
**Out of scope:** devices (CHG-0034); moving any tenant to another site.

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

### Step 1: Each tenant in turn

Update the provider, set the tenant's sites, apply.

**Verify:** a browser opens `console.eds.deevnet.net` and `console.eds.mobile.deevnet.net` with one
certificate, chained to the root; each other tenant's site-less names resolve.

## Verification

Every tenant's site-less names resolve, and every tenant service certificate is from the re-keyed
Tenant Service CA under its site-less name.

## Undo

The old site-named certificates stay valid until they expire. A tenant's previous apply restores its
previous certificate.
