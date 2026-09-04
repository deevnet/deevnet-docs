---
title: "ADR-0007: Terraform State Custody"
weight: 7
---

# ADR-0007: Terraform State Custody

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-09-03 |
| **Scope** | Where Terraform state lives, who may read it, and what protects it |
| **Depends on** | [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/) |

---

## Context

State custody was never decided. `architecture/tenant/building.md` offered three bullets —

> Tenant Terraform state should be:
> - Stored in version control (for small deployments)
> - Or in remote backend (for team access)
> - Never edited manually

— which is a menu, not a decision, and it is contradicted on its own page by a `terraform_remote_state`
example. Both state files have been committed to git on the strength of the first bullet.

Two things made the question live.

**[ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/) makes custody a per-repository
question.** Once the fabric's state is read by nobody and each tenant's state is read by nobody, the
stacks are decoupled and can be decided independently rather than together.

**[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) put TSIG-signed updates in
tenant Terraform**, which raises the question of whether state now holds secret material. Today it
does not — verified — but only because the `dns` provider keeps `key_secret` in *provider
configuration*, which Terraform does not persist. That is provider-dependent luck, and nothing in
the repository notices if it changes.

### What the standard actually requires

`standards/secure-identity.md` §4.3 says *IaC MUST reference secret locations, not secret values*.
That governs IaC **source**, and it is satisfied: no `.tf` or `.tfvars` holds a secret. State is not
source; it is the record of an apply, and §4.3 does not reach it directly.

But §1.2 and §4.2 do bear on the consequence, and the invariant they imply is worth stating outright:

> **The moment state contains a secret value, the repository holding it becomes a secret store.**

### What is actually lost if state is lost

This sizes every option, so it is worth being precise. Neither state file contains anything
irreplaceable — no generated credentials, no random resources, nothing data-bearing. Losing state
means Terraform forgets which VMID is which resource; the VM keeps running and the records keep
resolving throughout. Recovery is `terraform import` or a rebuild.

**Losing state costs a rebuild, not a loss** — which is exactly what the architecture's own claim
that a tenant is rebuilt from code, not from a backup, is supposed to guarantee.

---

## Options considered

**Keep state in VCS with an enforced no-secrets invariant.** Better than it gets credit for: `git
clone` yields code *and* state, history yields every prior state, and that is an automatic, versioned,
off-host backup with no restore path to rehearse. What is missing is only that the invariant is
asserted and unchecked. Rejected as the destination, but it remains a valid position for any repository
that declines the store below.

**Local state with an encrypted backup to the artifact server.** Rejected outright. That server has
no write path — it is read-only nginx whose purpose is serving install artifacts to bare metal — so
the push would be an Ansible play a human must remember after every apply. It adds a key to manage
and a restore nobody rehearses, to protect data whose loss costs a rebuild. VCS is already the better
backup.

**An S3-compatible store the substrate runs.** Chosen.

---

## Decision

**The substrate offers an S3-compatible Terraform state store. A tenant may use it or decline it.**

### 1. Offered, not mandated — and that is the load-bearing part

The substrate *guarantees a state store exists*; the tenant chooses whether to use it. A tenant that
declines keeps local state and carries its own custody.

This is what makes the dependency acceptable. A state store is a hard dependency by nature — if it is
down, nothing can plan or apply — and imposing that would be a real availability regression against
ADR-0004 §5's promise that the recurring lifecycle is `terraform apply` and nothing else. **A
dependency the tenant chooses is a different thing from one it inherits.** A tenant that cannot
tolerate it does not use it, and nothing about that is a second-class path.

The alternative framing — that the dependency must exist *somewhere* — is the honest one. State in
git is also a dependency; it simply points at a git host instead, and is familiar enough to feel free.

This puts the state store in the same column as the DNS zone: something the substrate provides and
the tenant fills.

### 2. Ansible-provisioned, Terraform-consumed

`extended-services.md` §5 — *"Terraform is intentionally not used for management-plane workloads"* —
is often misread as blocking this. It does not. It governs how the service is **provisioned**, and a
service provisioned by Ansible and *consumed* by Terraform is precisely the shape ADR-0004 already
blessed for PowerDNS.

That rule is also what prevents a bootstrap cycle. The chain is Ansible → VM → store → state. Had
management-plane VMs been Terraform-provisioned, the store's own state would have had nowhere to
live.

### 3. Its own host

Not co-located with tenant DNS. The two have different failure consequences — DNS down means tenant
names stop resolving; the state store down means tenants cannot change anything at all — and ADR-0004
already named that host's blast radius as its own weakest point.

### 4. Per-tenant credentials, scoped by the server

Each tenant is issued an access key scoped by policy to its own prefix, from the same vault and the
same onboarding act as its TSIG key. This is ADR-0004 §3's argument transplanted: **a tenant is
refused another tenant's state by the server**, not because its Terraform declines to ask.

Repository permissions already separate tenants under ADR-0006, so this is defence in depth rather
than the only control — but it is what keeps the boundary true if two tenants ever share an operator.

### 5. The invariant survives regardless

Wherever state lives, it must not contain secret values. Moving state out of git makes that less
load-bearing; it does not make it untrue, because the store is readable by whoever holds a
credential. The rule stands: **no tenant declares a resource whose value cannot be re-derived from
code.**

---

## Consequences

**Locking exists now, and it is the thing that actually justifies this.** Verified rather than
claimed: with an apply holding the lock, a `.tflock` object appears in the bucket and a concurrent
operation fails with *Error acquiring the state lock*. The store honours the conditional write
Terraform's S3-native locking requires.

Worth being clear about what this fixes, because it is not what it first appears. The local backend
already takes an OS-level file lock, so two concurrent applies *on one machine* were already
prevented. What was unprotected was two **machines**: two clones, two applies, and the second write
silently overwriting the first — orphaning whatever it created, with nothing surfacing the failure
until something is found running that state does not know about. With one operator that cannot
happen. With two it will, and this is the day it stops being possible.

**The store is now a failure domain that did not exist.** If it is down, every tenant using it is
frozen. The opt-out is the mitigation, and it is a real one, but a tenant that has opted in has
genuinely traded availability for locking and isolation.

**Durability moved rather than vanished.** Git gave replication for free; the store's own data now
needs backing up. Bucket versioning is enabled, which turns an overwrite into an undo, but that is
not a backup and should not be mistaken for one. This is the weakest part of the decision and it is
recorded as such.

**State is out of git, so the no-secrets invariant stops being the only thing standing between a
provider change and a repository full of secrets.** It remains stated because repositories that
decline the store still rely on it.

**A second per-tenant secret now exists.** Onboarding issues a TSIG key and a state credential; both
live in the same vault and are issued in the same act, but the per-tenant secret count has doubled.

**`extended-services.md` §5 is honoured, not amended** — for the second time, and by the same
reasoning ADR-0004 used. That is now a pattern rather than a one-off: substrate services that serve
tenants are Ansible-provisioned and may be Terraform-consumed.

---

## Current state

- The store runs on its own management-plane VM, reached by a name rather than an address so it can
  move hosts without every tenant repository being edited.
- One bucket, prefixed per consumer, versioning on. `t-demo` has a credential issued; the fabric's
  state has a prefix reserved.
- Isolation is tested, not assumed: a tenant credential reads its own prefix and is refused both
  another tenant's prefix and the fabric's state.
- Migration of the two existing state files is a separate, reversible step — the repository copy
  stays as rollback until the migrated stack plans empty.
