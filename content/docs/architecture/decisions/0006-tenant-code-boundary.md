---
title: "ADR-0006: Tenant Code Boundary"
weight: 6
---

# ADR-0006: Tenant Code Boundary

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-09-03 |
| **Scope** | Where a tenant's code lives, and what it needs from the substrate to stand alone |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/) |
| **Extends** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/) §5 |

---

## Context

[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) §5 drew a line that has held
up well: **onboarding may touch substrate; the recurring lifecycle may not.** Adding a record,
rebuilding, destroying — those are `terraform apply` and nothing else.

It did not say where the tenant's code lives, and the estate has been answering that question two
ways at once. The runbook states the intent plainly:

> a tenant is rebuilt from its own repository, not from a backup

and then instructs the operator to `cp -r tenants/dvntm/t-demo tenants/dvntm/grooveiq` — inside
`deevnet-tenant-factory`, a substrate repository. "Its own repository" has meant "its own directory
in ours." Nothing enforces the boundary the documents assert.

### What is actually tenant-specific

Very little, which is what makes the split cheap. A tenant's root module is around **90%
boilerplate**: the `terraform` block, both provider blocks, the outputs, and the module call are
identical for every tenant. Only `tenant_name` and `tenant_index` genuinely differ.

### What actually couples a tenant to the factory

Three things, all in one file:

1. `module "tenant" { source = "../../../modules/tenant" }` — a filesystem path.
2. `data "terraform_remote_state" "fabric"` reading `fabric/dvntm-hv02/terraform.tfstate` by relative
   path, for `controller_id` and `node`.
3. `path.module` traversal, which is the mechanism for both.

The second is the interesting one, and it is the reason this needs a record rather than a commit.
Three documents currently say a tenant *never hardcodes* the controller or node — but that doctrine
appears in `README.md`, `building.md` and the runbook, and **in no ADR**. Nothing gets superseded
here; three descriptive documents are corrected.

### The doctrine is weaker than it looks

Neither value is discovered. `controller_id` is the literal `"evpn1"` in the fabric configuration;
`node` is a variable whose default is `"pve2"`. What the remote-state read provides is **one place to
keep two constants**, plus a weak apply-ordering signal. It is not dynamic discovery, because there
is none to have on a single-member fabric.

---

## Options considered

### Where the module lives

**Its own repository, consumed by version.** The cleanest boundary on paper. Rejected for now: the
module's *input* contract is the fabric's *output* contract, and when [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)
Phase 2 adds a fabric member, both sides move together — `node` stops being a site constant and
becomes a per-tenant choice. In one repository that is one commit and one review. Across two it is a
release dance. Splitting later costs a `source` string and a re-cut tag, and moves no resource
address, so the option stays open at almost no cost.

**Consumed by git tag from the factory.** Chosen. The registry, the fabric and the module are all
substrate-owned and change at substrate cadence; a tenant repository is tenant-owned. That is the
boundary worth drawing.

### How a tenant obtains the fabric attachment

**Published to the artifact server, read over HTTP.** Rejected. That server is a read-only nginx
distribution point with no write path — every artifact arrives by an Ansible push, so publishing
would be a multi-step manual flow after every fabric apply. Its failure mode is the worst available:
a missed publish leaves a document that looks authoritative and is stale. It would also put the
builder node in the plan-time path of every tenant.

**Read from a remote fabric state backend.** Rejected for now. `terraform_remote_state` copies the
*entire* upstream output set into every consumer — today's tenant state already carries `fabric_id`
and `vtep_loopback`, which it never references. That hands each tenant the whole fabric state to
obtain two constants, and adds a per-tenant backend credential to do it. Revisit if a multi-member
fabric makes `node` genuinely per-tenant.

**Issued by the substrate at onboarding.** Chosen — see below.

---

## Decision

**Each tenant lives in its own git repository, `deevnet-tenant-<name>`. The factory keeps the
fabric, the reusable module, the index registry, and a reference implementation that cannot be
applied.**

### 1. The module is consumed by tag

```hcl
module "tenant" {
  source = "git::ssh://git@github.com/deevnet/deevnet-tenant-factory.git//modules/tenant?ref=tenant-module-v1.0.0"
}
```

Tags are `tenant-module-vMAJOR.MINOR.PATCH` and are **never moved**. MAJOR covers a removed or
renamed variable, a default change that makes an existing tenant's plan non-empty, and any resource
address change.

Every tenant repository commits its `.terraform.lock.hcl`. A module pinned by tag with providers
left to float is half a pin, and the floating half is the dangerous one: the current provider
constraint admits everything below 1.0 on a provider whose own comments call its SDN resources
"still settling."

### 2. The fabric attachment is issued, not read

`controller_id` and `node` are recorded in the substrate's tenant registry and rendered into a
tenant repository at onboarding, beside the TSIG key of ADR-0004 and the egress of
[ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/).

**This is the same category as those two: a thing the substrate issues to a tenant.** It therefore
lands inside ADR-0004 §5 rather than fighting it — onboarding may touch substrate; the recurring
lifecycle still may not.

The doctrine is reworded rather than dropped:

> A tenant never *invents* its controller or node. The substrate issues them at onboarding, in the
> same act that issues its TSIG key and its egress.

Two things keep that honest. The fabric's own `outputs.tf` is **not deleted** — it stops being a
consumed interface and becomes the source of truth. And `make fabric-contract` diffs the issued
values against `terraform output`, so the two cannot drift unnoticed.

### 3. The reference implementation cannot be applied

It lives at `examples/tenant/` — not under `tenants/`, because anything left in a directory of
things you apply will eventually be applied. It is a whole repository skeleton, so onboarding is a
copy into a new repository rather than a copy into this one.

It is guarded mechanically rather than by request: the example carries `tenant_index = 0`, and the
module validates the index against ADR-0002's own range of 1–63. The example therefore *cannot* be
applied — `plan` fails at variable validation with a message that says what to do instead.

Drift is caught in three layers, and each proves something different: `make validate` proves the
module tag resolves and the inputs still exist; `make example-plan` (at the reserved index 63) is a
live API round trip that proves the controller, node and template actually exist, while creating
nothing; and the rebuild-from-scratch drill — already an open roadmap item — proves apply works, at
each MAJOR tag.

---

## Consequences

**A tenant's recurring lifecycle no longer touches a substrate repository at all.** Previously it
required a checkout of one. That is ADR-0004 §5 finally true in the code rather than only in the
prose.

**Onboarding grows a step, and gains a place to fail.** Allocating the index, issuing the key, the
egress and now the attachment are one Ansible run driven from one declared list — but a tenant
repository is created by hand, and nothing yet checks that it was created from the reference
implementation rather than by copying a neighbour.

**`terraform init` now needs GitHub and an SSH agent.** Mitigating fact: the module is vendored into
`.terraform/modules/` on first init and is not re-fetched by `plan` or `apply`. The dependency is
init-time only, and moving to a new tag requires an explicit `terraform init -upgrade` — which is
also the gotcha, because a tenant that never re-inits stays on its old module indefinitely and
nothing says so.

**The fabric and each tenant become fully decoupled.** After this, the fabric's state is read by
nobody and each tenant's state is read by nobody. That is what lets state custody
([ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/)) be decided per repository
rather than as an estate-wide flag day — a benefit that was not the goal.

**The attachment can go stale in a way a state read could not.** A fabric change that is not
reflected in the registry leaves tenants holding old values. This is the cost of the option chosen,
and it is mitigated rather than eliminated: `fabric-contract` detects it, and a wrong value fails
loudly at apply because the PVE API rejects it — unlike a stale published document, which would be
accepted and produce a wrong-but-plausible result.

**Splitting the module out later stays cheap.** A `source` string and a re-cut tag; no resource
address moves, because addresses are `module.tenant.<type>.<name>` regardless of where the source
came from.

---

## Current state

- `t-demo` is the first tenant to move, and it stays live. The acceptance gate for the move is an
  **empty plan** in the new repository: same state, same resource addresses, same running VM, same
  published records, zero API mutations.
- The registry, the reference implementation and the drill index are the factory's; everything a
  tenant recurringly does is its own.
- Provider lock files are committed and `TENANT` no longer defaults to a live workload — both
  prerequisites, both landed before any code moved.
