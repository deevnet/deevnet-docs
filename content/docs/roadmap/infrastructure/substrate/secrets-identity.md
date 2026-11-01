---
title: "Secrets and Identity"
weight: 7
milestones:
  - title: "Substrate secrets in Ansible Vault, guarded on every commit"
    status: done
    date: "2026-03-14"
  - title: "OpenBao deployed; the API reads its credentials from it (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "Builds take their secrets from OpenBao, none on disk (CHG-0026)"
    status: done
    date: "2026-09-25"
  - title: "OpenBao's keys from the vault, its access bound and audited (CHG-0036)"
    status: done
    date: "2026-10-25"
  - title: "Secrets: the Shamir seal and the rebuild drill"
    status: active
  - title: "Identity Management"
    status: planned
---

# Secrets and Identity

Where the site's secrets live and who may reach them: Ansible Vault, then OpenBao with its own keys
from the vault; and identity for the people and services that use them.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Extended Management Plane](/projects/management-plane/), its secrets and identity phases
