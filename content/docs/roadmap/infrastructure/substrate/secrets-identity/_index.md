---
title: "Secrets and Identity"
bookCollapseSection: true
weight: 7
value: [secure-by-default]
milestones:
  - title: "The site's infrastructure secrets in Ansible Vault, guarded on every commit"
    status: done
    date: "2026-03-14"
  - title: "OpenBao secrets manager deployed; the Deevnet API reads its credentials from it (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "Builds take their secrets from OpenBao, none on disk (CHG-0026)"
    value: [secure-by-default, one-operator]
    status: done
    date: "2026-09-25"
  - title: "OpenBao's keys made outside it and loaded from the site's vault on every build, its access restricted and audited (CHG-0036)"
    value: [secure-by-default, rebuild-from-code]
    status: done
    date: "2026-10-25"
  - title: "OpenBao moved to a split-key (Shamir) seal, and its rebuild drilled"
    value: [secure-by-default, rebuild-from-code]
    status: active
  - title: "Single sign-on and role-based access for infrastructure services"
    status: planned
---

# Secrets and Identity

Where the site's secrets live and who may reach them: Ansible Vault, then OpenBao with its own keys
from the vault; and identity for the people and services that use them.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Secrets and Identity](/docs/roadmap/infrastructure/substrate/secrets-identity/plan/)
