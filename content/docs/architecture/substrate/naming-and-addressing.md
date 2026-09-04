---
title: "Naming and Addressing"
weight: 4
---

# Naming and Addressing

How a thing on this estate gets an address, and how it gets a name.

Both answers are deliberately boring for the substrate and deliberately different for tenants. This
page explains the chain, where authority changes hands, and what each half is allowed to write.

---

## The substrate chain

Nothing on the substrate picks its own address, and nothing invents its own name. A single declared
identity produces both:

{{< mermaid >}}
graph LR
    ID["Declared identity<br/>(inventory)"] --> MAC["Hardware address"]
    MAC --> RES["Address reservation"]
    RES --> IP["Address"]
    IP --> REC["Name record"]
    REC --> NAME["service.site.deevnet.net"]
{{< /mermaid >}}

Every link is derived, not chosen:

| Link | Where it comes from |
|------|---------------------|
| Identity → hardware address | Assigned from the estate's own address namespace, derived from the host's allocated identifier. Addresses on hardware we did not create are recorded as found, never rewritten. |
| Hardware address → address | A reservation on the address service, generated from inventory |
| Address → name | A record on the resolver, generated from the same inventory entry |

The consequence is that **a host's address is a fact about its declaration, not about the order it
booted in**. Rebuild it, and it comes back on the same address with the same name, because nothing
along that chain was decided at runtime.

### Reservations, not static configuration

Substrate hosts are addressed by **reservation**: they ask for an address, and the address service
always gives them the same one because it recognises their hardware address. They are not configured
with an address locally.

This looks like a detour — why not just configure the address on the host? — but it puts the
addressing plan in one place that can be reviewed, and it means a host with a fresh operating system
and no configuration at all still arrives at the right address. The declaration is authoritative;
the host is disposable.

It also means the **hardware address is load-bearing**. A host whose hardware address does not match
its declaration does not get its reserved address. It gets whatever the dynamic pool hands out,
which is a working address that no name points at — a failure that looks like success until
something tries to reach the host by name.

### Segments differ

Not every segment is reservation-only. Segments carrying transient devices have dynamic pools;
management and platform segments do not, because everything on them is declared. Where a pool and
reservations coexist on one segment, the pool is positioned above the reserved range so the two
cannot collide.

---

## Tenants address themselves

Tenant workloads do **not** use the substrate's address service, and the reason is structural
rather than preferential: a tenant's network is an overlay owned by the tenant compute domain
([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)), and that overlay has no
leasing service of its own.

So a tenant workload is given its address **at creation time**, from the tenant's own code, derived
from the tenant's index ([ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/)).
There is no reservation because there is nothing to reserve against.

| | Substrate host | Tenant workload |
|---|---|---|
| **Address decided by** | Reservation, from declared identity | The tenant's own code, at creation |
| **Address service involved** | Yes | No |
| **Survives a rebuild because** | The reservation is derived from inventory | The address is derived from the tenant index |

Both are deterministic. They arrive there by different routes because they live on different
networks with different capabilities, and pretending otherwise would mean adding a leasing service
to the overlay purely for symmetry.

---

## Two naming authorities

Names split along the same seam as
[the tenant contract](/docs/architecture/tenant/): the substrate names the things it runs, and a
tenant names the things it runs.

{{< mermaid >}}
graph TB
    CLIENT["Any substrate client"] --> RESOLVER["Substrate resolver<br/>site.deevnet.net"]
    RESOLVER -->|"substrate names"| SUB["Answered directly<br/>records generated from inventory"]
    RESOLVER -->|"tenant zone"| AUTH["Tenant authoritative service"]
    AUTH --> TEN["Answered from the tenant's zone<br/>records written by the tenant"]
{{< /mermaid >}}

**The substrate resolver** answers for substrate names. Its records are generated from inventory by
the same automation that generates the reservations, so the address and the name cannot disagree —
they come from one declaration.

**A tenant's names live in a separate authoritative service.** The substrate runs that service and
creates each tenant's zone, but it never writes a record into one. Records are tenant content
([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).

This is the point of the arrangement. If tenant names lived in the substrate resolver, then either
tenants would need to commit to a substrate repository to publish a name, or substrate
reconciliation would be free to delete records it did not create. Separating the zone removes the
conflict rather than managing it.

---

## How a query reaches a tenant name

This is the part worth being precise about, because the common shorthand is misleading.

A substrate client asks the substrate resolver for everything. When the name falls inside a tenant's
zone, the resolver **forwards the query** to the tenant authoritative service and returns its
answer.

{{< mermaid >}}
sequenceDiagram
    participant C as Client
    participant R as Substrate resolver
    participant A as Tenant authoritative service
    C->>R: api.tenant.site.deevnet.net?
    R->>A: forwarded — this zone is yours
    A->>R: answer from the tenant's zone
    R->>C: answer
{{< /mermaid >}}

### Forwarding is not referral

The resolver is configured with a rule of the form *"for this zone, ask that server"*. It is **not**
following a delegation: no parent zone contains a referral to the tenant's servers, and the
resolver never asks the tenant zone which servers are authoritative for it.

That distinction has real consequences, and they are easy to miss:

- **The tenant zone's own apex records are never consulted on this path.** A zone missing the
  records that name its own servers still resolves perfectly through the resolver, because nothing
  on this path ever looks at them. The defect is invisible from the client's point of view — which
  is exactly how it went unnoticed until
  [ADR-0005](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/).
- **Resolution depends on configuration, not on the DNS hierarchy.** Anyone querying the tenant
  authoritative service directly gets the same answers; anyone querying the public hierarchy for
  these names gets nothing. These are internal names and that is intended.
- **Anything that does validate the hierarchy will not be satisfied by this.** A second
  authoritative server, a resolver that checks a child's servers against its parent, or a genuine
  referral would all need the zone apex to be correct. Which is why it is maintained even though
  this path never reads it.

Calling it a *delegation* is fair as a description of ownership — the tenant owns the zone. It is
inaccurate as a description of mechanism, and the difference is where the surprises live.

---

## Two write paths

The same split appears in how records get written.

| | Substrate names | Tenant names |
|---|---|---|
| **Source of truth** | Inventory | The tenant's own IaC |
| **Written by** | Substrate automation, reconciling | The tenant, at deploy time |
| **Transport** | The resolver's own configuration interface | Dynamic update, over the network |
| **Authorisation** | Access to the substrate repository | A credential scoped to that tenant's zones |
| **Blast radius of a mistake** | The substrate zone | That tenant's zone only |

The tenant's credential is the part that makes the boundary real. It is issued per tenant and
accepted only for that tenant's zones, so a tenant writing outside its namespace is refused by the
server rather than trusted not to try.

One qualification, recorded because the table above reads stronger than the truth: the credential is
scoped to a **zone**, not to individual records within it. Everything inside a tenant's own zone —
including the apex records the substrate maintains — is writable by the tenant holding that
credential. The namespace boundary is enforced; the boundary *within* a zone is a convention. See
[ADR-0005](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/).

---

## Reverse names

Reverse lookup follows the same shape. Each tenant gets a reverse zone alongside its forward zone,
derived from the same tenant index, forwarded the same way, and populated — or not — by the tenant.
Substrate reverse records are generated from inventory with everything else.

---

## What this arrangement guarantees

- **A rebuilt host returns to its own address and name**, because both derive from a declaration
  rather than from anything that happened at runtime.
- **A rebuilt tenant restores its own names**, with no substrate change, because the records were
  never substrate content.
- **A rebuilt resolver loses no tenant names.** Its share of the arrangement is one forwarding rule
  per tenant zone, regenerated from inventory; the records themselves were never in it.
- **Neither side can quietly overwrite the other.** They do not share a zone, so there is no
  reconciliation that could.

The cost is one more service to run and one more thing to be down. Tenant names depend on the
authoritative service being up; substrate names do not, and continue to resolve if it is not.
