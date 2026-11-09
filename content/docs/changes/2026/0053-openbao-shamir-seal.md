---
title: "CHG-0053: OpenBao Sealed by Shamir Shares"
weight: -53
---

# CHG-0053: OpenBao Sealed by Shamir Shares

| | |
|---|---|
| **Date** | 2026-11-08 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **Complete, 2026-11-08.** OpenBao is on three Shamir shares, threshold two, every pair proven; the static seal key is gone from the identity VM and the vault; plays stop on a sealed store; `make bao-open` and `bao-close` open and close a work session. The shares were rotated the same day after share 1 reached an AI agent's session transcript |
| **Window** | 2026-11-08, 17:17 to 17:19 for the migration (OpenBao down under a minute); the lock-in and the share rotation followed that evening, after the kit moved site |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao), `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet.mgmt`: `make bao-seal-migrate` (once), `make bao-open`, `bao-close`, `bao-status`, `bao-rotate-shares`, and the `openbao` role's sealed stop ([#104](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/104), [#105](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/105), [#106](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/106)); inventory [#94](https://github.com/deevnet/ansible-inventory-deevnet/pull/94), [#95](https://github.com/deevnet/ansible-inventory-deevnet/pull/95), [#96](https://github.com/deevnet/ansible-inventory-deevnet/pull/96) |
| **Risk** | Medium. Most likely to go wrong: the shares are made but a pair is never proven, and the store cannot be opened when it matters. Every pair is proven before the old seal key is removed |
| **Related changes** | [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/) (required first), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [OpenBao's Keys: the unseal shares](/docs/runbook/substrate/building-recovery/openbao-keys/#the-unseal-shares), [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/), [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/) |

---

## Summary

OpenBao unsealed itself with a static seal key held in the vault and on the identity VM, so every
key in it was open whenever the kit was on.
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

- [x] CHG-0052 and CHG-0036 complete
- [x] [CHG-0037](/docs/changes/2026/0037-builds-off-openbao/) step 1: template builds and the tenant fabric read the vault, not OpenBao, so a sealed store does not stop them
- [x] A place for each of the other two shares, apart from the vault and from each other, encrypted at rest
- [x] Vault decrypted; collections built

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

**State, 2026-11-08:** done, by `make bao-seal-migrate`, which carries out steps 2 to 4 above through
OpenBao's API (`sys/unseal` with `migrate`, then `sys/rotate/root`). The dump in step 1 was replaced
by a copy of OpenBao's data directory taken with it stopped, which took seconds; it was deleted once
the migration was proven.

| Time | Event |
|---|---|
| 17:17:46 | OpenBao stopped, its data copied, started again: unsealed itself on the static seal |
| 17:18:03 | `make bao-seal-migrate` starts: the static block disabled, OpenBao restarted, sealed |
| — | Unsealed with the recovery key and `migrate`: the seal is Shamir, one share |
| — | The one share rotated into three, threshold two, written at once to the control node |
| — | The Shamir configuration written and the static key deleted from the VM |
| — | Each of the three pairs proven: restart, sealed; unseal with the pair, open |
| 17:18:55 | Done: 41 tasks, no failure; OpenBao open on a Shamir seal, 2 of 3 |

The two inferences under [Found](#found) held: the static seal migrates as an auto seal, and its one
recovery key became one unseal key.

### Step 2: The shares

Write one share into the vault and lock it in. Hold the other two apart, encrypted at rest.

**Verify:** each of the three pairs unseals the store.

**State, 2026-11-08:** done. Every pair was proven by the migration, and again by the rotation below.
`make bao-open` then opened the store through its everyday path, the vault's share and one the
operator typed. Share 1 is in the vault; shares 2 and 3 are the operator's.

### Step 3: The static seal key removed

Delete it from the identity VM and the vault.

**Verify:** a reboot of the identity VM leaves OpenBao sealed; the API's `/readyz` reports it sealed;
every tenant's workload and every device keep running.

**State, 2026-11-08:** done. The key was deleted from the VM by the migration; the identity VM's
OpenBao secrets directory is empty and its configuration has no seal block. The vault's
`vault_openbao_seal_key`, `_seal_key_id` and the recovery key, which the rotation replaced, were
removed ([inventory #95](https://github.com/deevnet/ansible-inventory-deevnet/pull/95)).

| Check | Result |
|---|---|
| A restart leaves OpenBao sealed | Pass: the kit was powered off to move site, and OpenBao came back sealed, Shamir, 2 of 3 |
| The API's `/readyz` reports it sealed | Pass: HTTP 503, `{"database":"ok","openbao":"sealed","status":"unavailable"}`; `/healthz` 200 |
| Tenant workloads and devices keep running | Not tested on its own. Nothing a tenant workload or device connects to reads OpenBao; the API's refusal was tested by CHG-0052 |

### Step 4: The plays and the targets

The role's first task stops with a plain error if OpenBao is sealed. Targets open and close a work
session.

**Verify:** a play against the sealed store stops with that error and changes nothing.

**State, 2026-11-08:** done. The sealed stop is the first task of the `openbao` role, of the two
CA-only plays and the Tenant Service CA's verify play, and of the `deevnet_api` role's OpenBao step.

| Check | Result |
|---|---|
| A play against the sealed store stops and changes nothing | Pass: `playbooks/tenant-service-ca-verify.yml` stopped at its first check, *OpenBao on dv02idn001v01 is sealed. Nothing was changed.*, `changed=0` |
| `make bao-close` refuses a static seal | Pass, before the migration: it stopped before restarting anything |
| `make bao-open` and `bao-close` | Pass: opened with the vault's share and one typed; closed by a restart, sealed |

## Verification

V13 and V14 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan)
pass: sealed, devices and workloads continue, a tenant request is refused cleanly, the play stops;
every pair unseals; no share or seal key is found on the kit.

**State, 2026-11-08:** passed, V13 with the device half resting on design (Step 3). For V14, the
Builder was searched for every share in plaintext after the migration: the copies found were the
shares file itself, three copies the collection build had packed (below), and the transcript
copy of share 1 (below); all were removed or made void by the rotation. After the rotation, no share
file is on the kit by name or in the built collection, and the identity VM holds no unseal material.
The old static seal key is left only in the vault's encrypted git history.
**Inferred, not tested:** that it opens nothing now, since the store's root key is no longer sealed
by it.

**Two things were found and fixed on the way.**

- **The collection build packed `.openbao/`.** `ansible-galaxy build` packs the whole directory, and
  `.openbao/` is git-ignored but not build-ignored; `.ansible/`, the install tree, nested a copy of
  the collection inside itself on every build. Every `make` target builds, so the shares file was
  copied three times and into the tarball. All were shredded, and `build_ignore` now excludes both
  ([#105](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/105)).
- **Share 1 reached an AI agent's session transcript.** The agent had inspected the openbao vault
  file through shell commands, and wrote share 1 into it with a script; when the operator later
  decrypted the vault, the agent's harness recorded the file's change into the session. One share
  opens nothing, but the transcript and one more share would, without the vault password. **The
  shares were rotated** (`make bao-rotate-shares`, [#106](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/106)),
  every new pair proven, and the old ones unseal nothing. The new share 1 went into the vault with
  `ansible-vault edit`, the file encrypted on disk throughout
  ([inventory #96](https://github.com/deevnet/ansible-inventory-deevnet/pull/96)). The runbook now
  says to keep share and vault work out of an agent's session.

## Undo

A rebuild from the vault with `openbao_seal_type: static` and a new seal key is the way back: the
role initializes an empty store and imports every key from the vault (CHG-0036).

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

- [x] Step 1: OpenBao on a Shamir seal, three shares, threshold two, 2026-11-08
- [x] Step 2: one share in the vault, the other two held apart, every pair proven, 2026-11-08
- [x] Step 3: the static seal key removed, from the identity VM and the vault, 2026-11-08
- [x] Step 4: the plays stop with a plain error on a sealed store, and targets open and close a work session, 2026-11-08
- [x] Verification: V13 and V14 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass, 2026-11-08
