---
title: "Decisions"
weight: 6
bookCollapseSection: true
---

# Architecture Decision Records

This section records **significant architectural decisions** — the design forks where more
than one option was viable, the reasoning that selected one, and the consequences accepted
in doing so. Each record is a durable answer to "why is it built this way, and what did we
turn down?"

Decision records are **point-in-time**. They capture what was decided and why *at the time
the decision was made*. When a later decision supersedes an earlier one, the earlier record
is marked `Superseded` and linked forward — records are never rewritten to hide the history.
The descriptive architecture, platform, and roadmap pages are kept current; the decision log
is kept honest.

---

## Format

Each record follows a lightweight ADR structure:

| Field | Purpose |
|-------|---------|
| **Status** | `Proposed`, `Accepted`, `Superseded`, or `Deprecated` |
| **Context** | The situation and the goals that forced a choice |
| **Options considered** | The viable alternatives, each with its trade-offs |
| **Decision** | What was chosen |
| **Consequences** | What the decision commits us to — good and bad |

Records are numbered in the order they are **opened** (`0001`, `0002`, …) and never renumbered.
A record may sit at `Proposed` for a while before it is accepted; the number is claimed when the
question is written down, not when it is answered.

---

## Records

- [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) — tenant networking is an
  overlay fabric owned by the tenant compute domain, self-contained per hypervisor, built as
  a single-member fabric that expands to a cluster without redefinition.
- [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/) — every tenant
  identifier (VNI, VRF, subnet) derives from a single tenant index, allocated inside the existing
  site `/16` rather than a second aggregate.
- [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/) —
  tenant egress needs transit forwarding and a default route inside each tenant VRF; Proxmox's own
  exit-node behaviour routes around the perimeter rather than through it.
