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
| **Window** | Unscheduled. After [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) and CHG-0037 step 1. OpenBao is down for the migration, minutes; tenant work is refused meanwhile, and nothing deployed stops |
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
- [ ] [CHG-0037](/docs/changes/2026/0037-builds-off-openbao/) step 1: template builds and the tenant fabric read the vault, not OpenBao, so a sealed store does not stop them
- [ ] A place for each of the other two shares, apart from the vault and from each other, encrypted at rest
- [ ] Vault decrypted; collections built

## Procedure

### Step 1: Migrate the seal

**OpenBao migrates an auto seal to Shamir, keeping its data, with the store briefly down.** The static
seal is an auto seal, so the store keeps every tenant secret and needs no import. The migration
gives as many unseal keys as there were recovery keys: one, since the store was initialized with
one. A rekey then splits it into three shares, threshold two, with the store open.

1. Take a dump of the identity VM on its own hypervisor, as the fallback.
2. Add `disabled = "true"` to the `seal "static"` block, leaving the key in place, and restart
   OpenBao.
3. `bao operator unseal -migrate` with the recovery key from the vault. The store comes up on Shamir.
4. `bao operator rotate-keys -init -key-shares=3 -key-threshold=2`, finished with the one key. Its
   output is the three shares.

If the migration fails, initialize a fresh store instead and let the role import everything from
the vault, which CHG-0036 made routine.

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

## Found

**OpenBao migrates an auto seal to Shamir, with the store down while it does**, from its
[seal documentation](https://openbao.org/docs/concepts/seal/), read 2026-11-08 for OpenBao 2.6.2:

- For "Auto seal to Shamir", "add `disabled = "true"` to the old seal block" and "run the unseal
  command on each key, by supplying the `-migrate` flag".
- The recovery keys are supplied "as Shamir unseal keys if the new seal is Shamir".
- The process "cannot be performed without downtime". "Seal migration operation will require both
  old and new seals to be available during the migration", and "A backup should be taken before
  starting seal migration in case something goes wrong."

The [rekey command](https://openbao.org/docs/commands/operator/rekey/) "generates a new set of unseal
keys" and can change the number of shares and the threshold. "This operation is zero downtime, but
it requires the OpenBao is unsealed and a quorum of existing unseal keys are provided." It is
deprecated in favor of `rotate-keys`.

**Inferred, not stated by the documentation:** that the static seal counts as an auto seal for
migration (its own page calls it "a built-in auto-unseal mechanism", and the role's initialization
returned recovery keys, not unseal keys), and that one recovery key becomes one unseal key. Step 1
shows both, and its fallback covers them being wrong.

## To close

**What is left before this change closes, from its procedure and verification.**

- [ ] Step 1: OpenBao on a Shamir seal, three shares, threshold two
- [ ] Step 2: one share in the vault, the other two held apart
- [ ] Step 3: the static seal key removed
- [ ] Step 4: the plays stop with a plain error on a sealed store, and targets open and close a work session
- [ ] Verification: V13 and V14 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass
