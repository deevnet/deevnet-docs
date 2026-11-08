---
title: "Tenant PKI: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/tenant-pki/
  - /projects/tenant-pki/
weight: 12
tasks_completed: 13
tasks_in_progress: 0
tasks_planned: 4
---

# Tenant PKI: Project Plan

What a tenant does with Deevnet's certificates: service certificates under site-less names, a
Deevnet Pi that holds them, and devices with certificates of their own. The CAs themselves are
[TLS Cert Automation](/docs/roadmap/infrastructure/substrate/tls-cert-automation/).

**Roadmap item:** [Tenant PKI](/docs/roadmap/infrastructure/tenant-services/tenant-pki/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The PKI review ([2026-10](/docs/architecture/reviews/2026-10-tenant-pki/)) decided the tenant side;
this tracks building it.

**In Scope**
- Site-less names and their certificates, and reissuing the tenants under them
- The Deevnet Pi: `deevnet-kit`'s request and install, `pki init`, the image tenants download
- Device certificates and the broker's checks

**Out of Scope**
- The root, site and substrate CAs, and OpenBao's seal

---

## Site-less names ✅

- ✅ Reserved labels in the API, and `sites` on a certificate, API v0.15.0 and provider v0.8.0 (CHG-0054)
- ✅ The first certificate under the new names, for eds's home Pi, 2026-10-29 (CHG-0054)
- ✅ OpenBao itself refuses a reserved name, through one CEL role rather than a role per tenant, 2026-11-07 (CHG-0059; ADR-0040's open question)
- ✅ Reissue `eds`'s certificate under its site-less name, 2026-11-01 (CHG-0055). `tdemo`, `mabell` and
  `cdeever` hold no tenant service certificate; each names its sites when it is next worked on

---

## The Deevnet Pi ✅

- ✅ `deevnet-kit cert request` and `cert install`, first used on eds's home Pi (CHG-0056)
- ✅ The image tenants download carries the kit with them: v0.16.0's, served since 2026-11-07 (CHG-0056 step 3)
- ✅ `cert install` reruns the dashboards step ([#41](https://github.com/deevnet/deevnet-provisioning-api/issues/41)). Released in v0.16.0 ([#45](https://github.com/deevnet/deevnet-provisioning-api/pull/45)); in the tenant downloads' image since 2026-11-07
- ✅ No address warning on a Deevnet Pi ([#42](https://github.com/deevnet/deevnet-provisioning-api/issues/42)). Released in v0.16.0; in the tenant downloads' image since 2026-11-07
- ✅ A renewal that installs, for the same key ([#43](https://github.com/deevnet/deevnet-provisioning-api/issues/43)). Released in v0.16.0; in the tenant downloads' image since 2026-11-07
- ✅ Ceremony tools that take an owner's names and issue a leaf: `deevnet-pki-owner.sh`, 2026-11-08 (CHG-0056 step 1)
- ✅ `pki init` and the starter kit: leaving Deevnet with a PKI of one's own, a Deevnet Pi keeping its tenant's names, verified on a Pi of the Pi lab with an ESP32 (V7, V8, V11), 2026-11-08 (ADR-0041, CHG-0056 step 2)
- ✅ The image tenants download carries `pki`: `deevnet-kit` v0.18.0, in the tenant downloads since 2026-11-08 (CHG-0056 step 3)
- ✅ Grafana and first boot's certificates wait for the clock: a card starts at its image's build time and waits for NTP, in the tenant downloads' image since 2026-11-08 (CHG-0056 follow-up)

---

## Device certificates ⏳

- ⏳ The API signs a device's request and records its key fingerprint (CHG-0034)
- ⏳ A device certificate in the provider (CHG-0034)
- ⏳ The broker requires a client certificate, with its three checks: chain, registration, fingerprint (CHG-0034, ADR-0039 §5)
- ⏳ One real device on its certificate (CHG-0034)
