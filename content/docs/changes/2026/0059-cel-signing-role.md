---
title: "CHG-0059: The Secret Store Refuses Reserved Names"
weight: -59
---

# CHG-0059: The Secret Store Refuses Reserved Names

| | |
|---|---|
| **Date** | 2026-11-07 |
| **Change type** | Configuration · Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. One API release, then Ansible runs for OpenBao and the API, in that order |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao: the Tenant Service CA's mount and the API's policy), `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet-provisioning-api` (v0.17.0); `deevnet.mgmt` `site.yml --tags openbao`, then `--tags deevnet-api`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. Most likely to go wrong: the CEL program refuses a name the API rightly asks for, and tenants can't get or renew a certificate until the API is switched back. Rarer and worse: the program signs something the classic role would have refused, because a CEL role sets every field of the certificate itself |
| **Related changes** | [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/) (site-less names, and the widened role this narrows), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) (the Tenant Service CA's issuance) |
| **Related incidents** | None |
| **Related runbooks** | [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

The Tenant Service CA signs through one OpenBao role, and since [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/)
that role takes any name two labels below `deevnet.net`. A tenant's `console.eds.deevnet.net` and a
site's `grafana.mobile.deevnet.net` look the same to it. Only the Deevnet API's reserved labels
([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) §4) keep
a tenant off a site's names, so a fault in the API could have the CA sign a substrate name.

This change answers ADR-0040's open question with a **CEL role**. OpenBao 2.6.2's PKI engine signs
through a CEL program in place of a list of permissions. Ansible writes the program, and the API may
only sign through it. It refuses:

- a name not of the form `<service>.<tenant>.[<site>.]deevnet.net`, with the site one of the
  certificate sites (`mobile`, `home`)
- a tenant label on the reserved list
- a certificate that names two tenants
- `device` as a service label
- a name given twice
- a key that is not RSA or ECDSA

**The rejected alternative, a role per tenant:** the inventory records no tenants
([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)), so the API
would have to write each tenant's role, and its policy would have to let it write roles. A faulty
API could then write a wide one, which is the abuse ADR-0040 names. Neither design ties a
certificate to the tenant that asked for it: the API is OpenBao's only caller, and that check stays
the API's.

## Goal

The secret store itself refuses a tenant certificate for a reserved label or a site's names, and the
Deevnet API can sign through nothing else.

## Procedure

**The program was tested on a throwaway OpenBao 2.6.2 on the Builder before it went near the
site**, in dev mode with a test CA. It signed EC and RSA requests at both sites. It refused every
case in the list above, plus a wildcard, a bare tenant zone, a device name, an unknown site,
another root, uppercase and a trailing dot. A CSR's own names, and an `ip_sans` or `ttl` in the
request, did not reach the certificate.

| Step | What | Check |
|---|---|---|
| 1 | Release API v0.17.0: `OPENBAO_TENANT_SERVICE_CEL=true` signs through `cel/sign/<role>`. `make stage` | Tagged; the image is under the Builder's artifact root |
| 2 | `site.yml --tags openbao`: the CEL role `tenant-service` on `pki-tenant-service`, read back whole; the API's policy grants `sign` and `cel/sign` | The role reads back as written. With the Ansible token, `cel/sign` refuses a reserved label, two tenants, a substrate name and a site's name |
| 3 | `deevnet_api_version: v0.17.0` and `deevnet_api_tenant_service_cel: true`; `site.yml --tags deevnet-api` | A probe certificate for `mabell` issues through the CEL role and is deleted; the V10 probes from CHG-0054 are still refused |
| 4 | `openbao_tenant_service_api_sign_paths: [cel/sign]`; delete the classic role; `site.yml --tags openbao` | The API's policy holds only `cel/sign`; `pki-tenant-service/roles/tenant-service` is gone |

**Rollback, through step 3:** set `deevnet_api_tenant_service_cel: false` and rerun
`--tags deevnet-api`. The API signs through the classic role again, which the policy still grants.
After step 4, rerun the old commit of the collection with `--tags openbao` first.

## Outcome

*To be written.*

**One thing the CEL role does not do that the classic role does:** it can't see the issuer, so it
doesn't stop a leaf at the CA's own expiry. A leaf lasts a year, and the Tenant Service CA runs to
October 2031. This matters only after October 2030, long after the CA should have been renewed.

## Follow-ups

- The reserved list now has two copies: the API's (`internal/tenant/site.go`) and the openbao role's
  (`openbao_tenant_reserved_labels`). A label added to one is added to the other.
