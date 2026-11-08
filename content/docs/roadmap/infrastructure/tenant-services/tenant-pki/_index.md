---
title: "Tenant PKI"
bookCollapseSection: true
weight: 4
value: [works-anywhere]
waypoints:
  - title: "Tenants' own services on Deevnet certificates (CHG-0047)"
    value: [secure-by-default]
    status: done
    date: "2026-10-11"
  - title: "Tenant names not tied to a site, issued by the Deevnet API and Terraform provider (CHG-0054)"
    status: done
    date: "2026-10-25"
  - title: "The EdS tenant's certificates reissued under a name not tied to a site (CHG-0055)"
    status: done
    date: "2026-11-01"
  - title: "The secret store itself refuses tenant certificates for a site's or the platform's own names (CHG-0059)"
    value: [secure-by-default]
    status: done
    date: "2026-11-07"
  - title: "The Raspberry Pi image tenants take home kept current with its setup tool, deevnet-kit (CHG-0049–0051)"
    status: done
    date: "2026-10-18"
  - title: "The first take-home Pi installed with Deevnet certificates, using a name not tied to a site (CHG-0056)"
    value: [works-anywhere, secure-by-default]
    status: done
    date: "2026-10-29"
  - title: "The take-home Pi image in the tenant downloads, using Deevnet certificates by default or a starter kit for an owner's own"
    status: done
    date: "2026-11-08"
  - title: "IoT devices issued their own certificates through the Deevnet API"
    value: [secure-by-default]
    status: planned
---

# Tenant PKI

What a tenant does with Deevnet's certificates: service certificates under site-less names, a
Deevnet Pi that holds them, and devices with certificates of their own. The CAs themselves are
[TLS Cert Automation](/docs/roadmap/infrastructure/substrate/tls-cert-automation/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Tenant PKI](/docs/roadmap/infrastructure/tenant-services/tenant-pki/plan/)
