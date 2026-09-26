---
title: "Discovery"
weight: 2
---

# Discovery {{< status-badge "planned" "Planned" >}}

Stage 4 of [Lifecycle Management](/docs/policies/lifecycle-management/): knowing what is actually
running, and learning what upstream has released for it. Discovery doesn't change anything. What it
finds starts another stage: a patch, a certification, an upgrade or a retirement.

---

## Validate what is running

The [Software Catalog](/docs/platforms/software-catalog/) is the system of record for versions, but
most of what it holds is **declared**: inventory pins, role defaults, lockfiles. A pin is intent. It
says what the automation deploys, not what is running after a manual upgrade, a failed play or a host
rebuilt by hand. Some entries were never written down at all.

**What must be true:**
- Every catalog entry can be checked against the running system, by a read-only scan.
- A mismatch between the catalog, the pin and what is running is a finding. It is resolved by
  correcting the catalog, or by a change that brings the system back to its pin.
- The scan runs after any change that upgrades something, and as part of site verification.

**Today:** versions are gathered by hand from inventory, roles and change records. The scan is the
[Software Discovery](/docs/roadmap/infrastructure/software-discovery/) roadmap project.

---

## Learn about releases and advisories

Every item in the catalog has an upstream that ships new versions and, sometimes, security fixes.
Deevnet has to hear about both from the place that publishes them, not by chance.

**What must be true:**
- **Each catalog item names its sources:** where its releases are announced, and where its security
  advisories are published. Often these are two different places.
- **Each source is watched**, at a cadence that fits it.
- **Each new release is triaged** into one of these:

| Finding | Goes to |
|---|---|
| A patch within a certified line | [Patch](/docs/policies/lifecycle-management/): read its notes, and re-check a criterion if they touch one |
| A new line | [Certification](/docs/policies/lifecycle-management/certification/), then an upgrade change |
| End of life announced for a line in use | Plan the upgrade or the retirement, with a date |
| Upstream archived or abandoned | A risk entry, and a replacement decision (as [ADR-0026](/docs/architecture/decisions/0026-object-storage/) did for MinIO) |
| A security advisory | [Vulnerability Management](/docs/policies/risk-management/vulnerability-management/), which assesses and records it |
| Nothing relevant | Noted as seen, so it isn't triaged twice |

**Kinds of source**, for when an item's sources are recorded:

| Kind | Examples |
|---|---|
| Project release feed | GitHub or GitLab releases, a project's release notes page or RSS |
| Vendor firmware page | TP-Link's download pages for the SG2218 and EAP650-Outdoor |
| Distribution channel | Fedora updates and errata, OPNsense's firmware updates, Proxmox's repositories |
| Security advisories | Project security pages, GitHub security advisories, distribution errata |
| Registry tags | Container image tags, the Terraform Registry, Ansible Galaxy |

**Today:** release notes are read when an upgrade is planned, and a few upstreams are followed by
habit. Nothing is watched systematically. The sources and the watching are on the
[Software Discovery](/docs/roadmap/infrastructure/software-discovery/) roadmap.
