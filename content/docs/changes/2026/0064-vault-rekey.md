---
title: "CHG-0064: The Inventory Vault Under a New Password"
weight: -0064
---

# CHG-0064: The Inventory Vault Under a New Password

| | |
|---|---|
| **Date** | 2026-11-12 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | In progress |
| **Window** | 2026-11-12 |
| **Site** | mobile |
| **Systems** | `ansible-inventory-deevnet`: every `vault.yml` and every device backup under `backups/` |
| **Automation** | `ansible-vault rekey`, run by the owner in a terminal; [Vault Operations → Changing the vault password](/docs/runbook/substrate/building-recovery/vault-operations/#changing-the-vault-password) |
| **Risk** | Low. Most likely to go wrong: a file left under the old password, which shows as a decrypt failure on the next run that needs it |
| **Related changes** | [CHG-0062](/docs/changes/2026/0062-device-backups-after-change/) |
| **Related incidents** | None |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/) |

---

## Summary

The inventory's vault files move to a new vault password. No secret inside them changes. One
password covers every `vault.yml` and every device backup, so they are rekeyed together, and the
rekey merges before the next device backup seals.

## Goal

- All 14 vault-encrypted files in the inventory (12 `vault.yml`, 2 device backups) decrypt with the
  new password and not the old one.
- The rekey is merged to `main`, so device backups seal under the new password.

## Scope

**In scope:** the password the inventory's vault files are encrypted under.
**Out of scope:** the secrets inside them, and the repository's history.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A file missed by the rekey | inventory | Files listed from git, not by hand; all 14 checked changed and still encrypted |
| A backup sealed under the old password after the rekey | `make backup-*` | The sealing script checks the password against `main`; merge the rekey first |
| A password typed where it could be captured, again | the rekey itself | Run in a terminal, not in a session that records input |

## Prerequisites

- [x] Every vault file encrypted, and the working tree clean on a branch from `main`
- [x] The router backup after [CHG-0063](/docs/changes/2026/0063-retire-flat-lan-address/) committed first, so it is rekeyed too

## Procedure

### Step 1: Rekey

**Run:** as in [Changing the vault password](/docs/runbook/substrate/building-recovery/vault-operations/#changing-the-vault-password).

**Verify:**

1. `git diff --name-only` lists all 14 files, and none lacks the `$ANSIBLE_VAULT` header.
2. Both backups and the inventory decrypt with the new password.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: Merge

Through an inventory pull request, before the next device backup.

## Verification

The next `make backup-router` or `make backup-wireless` seals with the new password.

## Undo

### Undo Step 1

Before the merge, drop the branch. After it, rekey back with the old password, which undoes the
point of the change; only for a password that turns out to be lost.

## To close

**This change closes when every item below is done.** One line each: the steps and the check.

- [x] Step 1: all 14 files rekeyed
- [ ] Step 2: rekey merged (inventory pull request #100)
- [ ] Verification: a device backup sealed with the new password

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 2026-11-12 | Prerequisites | A stray local commit from 2026-11-11, which held only re-encrypted vault files and a backup `main` already supersedes, was left unpushed on its branch. The rekey branch starts from `main`. |
| 2026-11-12 | 1 | The owner ran the rekey. All 14 files changed and kept the vault header; both backups decrypted with the new password. |

### Departures from the plan

- The first backup check used `--output /dev/null`, which `ansible-vault` refuses ("Destination
  '/dev' not writable"). `--output -` to a discarded stdout works; the runbook gives that form.

## Follow-ups

- [ ] None
