---
title: "CHG-0053: OpenBao Sealed by Shamir Shares"
weight: -53
---

# CHG-0053: OpenBao Sealed by Shamir Shares

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/) and [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/); one OpenBao role run, then a seal and unseal |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao), `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet.mgmt` `playbooks/openbao.yml` |
| **Risk** | Medium. Most likely to go wrong: the shares are made but a pair is never proven, and the store cannot be opened when it matters. Every pair is proven before the old seal key is removed |
| **Related changes** | [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/) (required first), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/), [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/) |

---

## Summary

OpenBao unseals itself today with a static seal key held in the vault and on the identity VM, so
every key in it is open whenever the kit is on.
[ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §1–§2
replace that with Shamir shares and a work session: the operator unseals at the start of a visit's
work and seals at its end ([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P2).

**The rule after this change:** no unseal material is on the kit; OpenBao is open only for a work
session.

## Goal

- Three unseal shares, any two of which unseal OpenBao. One is held in the vault; the other two are
  held apart, encrypted at rest. No single machine holds both the vault password and another share.
- Every pair of shares is proven by unsealing with it.
- The static seal key is gone from the identity VM and the vault.
- Ansible's OpenBao plays stop with a plain error naming the seal when OpenBao is sealed.
- A make target opens a work session and another closes it.
- The runbook describes a work session.

## Scope

**In scope:** the seal change, the shares, the work-session targets, the plays' sealed stop, the
runbook.
**Out of scope:** the keys OpenBao uses (CHG-0036, done first, so a fresh initialization costs
nothing).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The store cannot be opened | OpenBao | Every pair proven before the static seal key is removed; the store can be rebuilt from the vault (CHG-0036) |
| A share written only to a local file | control node | The lock-in rule: the vault's share encrypted, committed and pushed before the initialization output is deleted |
| Tenants damaged by a sealed store | the API | CHG-0052 first: the API refuses rather than forgets |
| A play run against a sealed store half-configures it | OpenBao | The sealed stop is the play's first task |

## Prerequisites

- [ ] CHG-0052 and CHG-0036 complete
- [ ] A place for each of the other two shares, apart from the vault and from each other, encrypted at rest
- [ ] Vault decrypted; collections built

## Procedure

### Step 1: Migrate or initialize

Migrate the static seal to Shamir in place if the running OpenBao supports it; otherwise initialize
a fresh store and let the role import everything from the vault, which CHG-0036 made routine.

**Verify:** `bao status` reports a Shamir seal, three shares, threshold two.

### Step 2: The shares

Write one share into the vault and lock it in. Hold the other two apart, encrypted at rest.

**Verify:** each of the three pairs unseals the store.

### Step 3: The static seal key removed

Delete it from the identity VM and the vault.

**Verify:** a reboot of the identity VM leaves OpenBao sealed; the API's `/readyz` reports it sealed;
every tenant's workload and every device keep running.

### Step 4: The plays and the targets

The role's first task stops with a plain error if OpenBao is sealed. Targets open and close a work
session.

**Verify:** a play against the sealed store stops with that error and changes nothing.

## Verification

V13 and V14 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan)
pass: sealed, devices and workloads continue, a tenant request is refused cleanly, the play stops;
every pair unseals; no share or seal key is found on the kit.

## Undo

Until Step 3, the static seal key is still in the vault, and the store can go back to it. After
Step 3, a rebuild from the vault with a static seal is the way back.

## To discover

- Whether OpenBao migrates a static seal to Shamir in place on the running version, from its
  current documentation.
