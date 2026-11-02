---
title: "ADR-0043: The Terms of the Tenant Contract"
weight: -43
---

# ADR-0043: The Terms of the Tenant Contract

|  |  |
|--|--|
| **Status** | Accepted (2026-11-01) |
| **Date** | 2026-11-01 |
| **Scope** | What the substrate promises tenants about availability, which services every tenant gets, and how changes to the contract are announced. The contract itself is [Substrate and Tenant](/docs/architecture/tenant/boundary/) |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/), [ADR-0015: Tenant Onboarding Through the API](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/), [ADR-0032: Every Device Belongs to a Tenant](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/) |

---

## Context

The boundary between tenants and the substrate had been decided piece by piece, and writing it as one
specification showed three things no record had settled: how available the services are, what makes
a tenant's services optional, and what a tenant is told before the contract changes.

## Decision

### 1. Every service is best effort

The substrate promises no uptime figure and no notice before an outage. The site is run part-time by
one operator, on hardware with single points of failure, and a promise it cannot keep would be worth
less than a plain statement.

### 2. Issued to every tenant, or declared by it

What the first apply creates is the contract's core, and needs nothing further from the tenant.
Everything else exists only if the tenant declares it. Workloads are declared, not core, so a tenant
with only devices conforms ([ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/)).

### 3. A breaking change is announced before it lands

It gets a change record and a release note first. A change is breaking when a conforming tenant must
act to keep working, or when its next apply would replace or reissue something it relies on.

## Consequences

- A tenant that needs more availability than this must not depend on the site alone for it.
- Terms stay simple enough for one operator to keep. They will need revisiting if the site ever has
  tenants it does not own.
- There is no compatibility window. Before 1.0, a minor release may be breaking, as the release notes
  already say.

## Alternatives considered

- **An uptime target.** Rejected: nothing measures it yet, and nothing could be done about a miss.
- **Workloads in the core.** Rejected: `mabell` has none, and a VM nothing runs on only costs memory.
- **A fixed notice period.** Rejected for now: one operator owns every tenant today, and a period
  would delay fixes without protecting anyone.
