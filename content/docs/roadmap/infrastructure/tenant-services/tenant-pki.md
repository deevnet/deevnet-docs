---
title: "Tenant PKI"
weight: 4
milestones:
  - title: "Tenants' own services on Deevnet certificates (CHG-0047)"
    status: done
    date: "2026-10-11"
  - title: "Tenant names not tied to a site, issued by the Deevnet API and Terraform provider (CHG-0054)"
    status: done
    date: "2026-10-25"
  - title: "The EdS tenant's certificates reissued under a name not tied to a site (CHG-0055)"
    status: done
    date: "2026-11-01"
  - title: "The other tenants (tdemo, mabell and cdeever) moved to names not tied to a site"
    status: active
  - title: "The Raspberry Pi image tenants take home kept current with its setup tool, deevnet-kit (CHG-0049–0051)"
    status: done
    date: "2026-10-18"
  - title: "The first take-home Pi installed with Deevnet certificates, using a name not tied to a site (CHG-0056)"
    status: done
    date: "2026-10-29"
  - title: "The take-home Pi image in the tenant downloads, using Deevnet certificates by default or a starter kit for an owner's own"
    status: active
  - title: "IoT devices issued their own certificates through the Deevnet API"
    status: planned
---

# Tenant PKI

What a tenant does with Deevnet's certificates: service certificates under site-less names, a
Deevnet Pi that holds them, and devices with certificates of their own. The CAs themselves are
[TLS Cert Automation](/docs/roadmap/infrastructure/substrate/tls-cert-automation/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Tenant PKI](/projects/tenant-pki/)
