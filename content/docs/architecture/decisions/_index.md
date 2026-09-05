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

Not every follow-on decision is a reversal. A record is often found to be **correct but
incomplete** — it settled the question it asked and left an adjacent one unanswered, usually
because building the thing is what exposed the gap. That case gets its own record, which
**extends** the earlier one: the earlier record keeps its `Accepted` status, because nothing
it decided has stopped being true, and gains a forward link. Superseding it instead would
retire a sound decision and force a near-duplicate rewrite, and appending the new reasoning
into the old record would date-stamp a decision to a day it was not made.

The test is whether the earlier record is still safe to act on. If yes, extend it. If acting
on it would now be a mistake, supersede it.

---

## Format

Each record follows a lightweight ADR structure:

| Field | Purpose |
|-------|---------|
| **Status** | `Proposed`, `Accepted`, `Superseded`, or `Deprecated` |
| **Extends** / **Extended by** | Set when one record answers a question another left open, without invalidating it. Both records stay `Accepted`. |
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
- [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/) —
  each tenant publishes into its own zone, delegated from the substrate zone and served by a
  substrate-run PowerDNS, written by the tenant over RFC 2136 with a TSIG key scoped to that zone.
- [ADR-0005: Tenant Zone Apex Ownership](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/) —
  a delegated zone's SOA and apex NS are substrate-owned and set at onboarding; extends ADR-0004,
  and records that this particular boundary is a convention rather than a server-enforced control.
- [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/) —
  each tenant lives in its own repository, consuming the tenant module by tag and a fabric
  attachment the substrate issues at onboarding; extends ADR-0004's onboarding-versus-recurring
  line into where the code itself lives.
- [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/) —
  the substrate offers an S3-compatible state store that tenants may use or decline; locking and
  per-tenant isolation are server-enforced, and the opt-out is what makes the dependency acceptable.
- [ADR-0008: Host Naming and Site Codes](/docs/architecture/decisions/0008-host-naming-site-codes/) —
  A fixed-width site code in every hostname, so the short name is unambiguous wherever
  it appears rather than only inside the inventory that loaded it; site zones renamed to say what
  the site is, and code `00` for the builder appliance that belongs to no site.
