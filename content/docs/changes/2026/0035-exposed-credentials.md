---
title: "CHG-0035: Previously Exposed Credentials Checked and Rotated"
weight: -35
---

# CHG-0035: Previously Exposed Credentials Checked and Rotated

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. The check is read-only; a rotation, if any, is per device |
| **Site** | mobile |
| **Systems** | Whatever the check finds still live: devices, services and their vault entries. Every public `deevnet` repository, for the scan |
| **Automation** | A local comparison script, run on the control node; the devices' own interfaces or their roles, for rotation; a secret-scan workflow per repository |
| **Risk** | Low. Most likely to go wrong: a comparison that prints a value. The script compares digests and prints only names and match/no-match |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/) |

---

## Summary

Some credentials were committed unencrypted earlier in the site's life, before the pre-commit hook
existed, and whether each has since been replaced is not recorded
([R-15](/docs/policies/risk-management/risk-register/)). This change finds out, replaces any that are
still in use, and adds a secret scan so the next slip is caught when it is pushed. History is not
rewritten: copies may already exist elsewhere, so replacing the credential is the fix
([2026-10 review, A1](/docs/architecture/reviews/2026-10-rebuild-and-access/#a1-exposure-tracking)).

## Goal

- Every credential ever committed unencrypted is listed by name (never by value) in the operator's
  own notes, with **live** or **replaced**.
- None is live.
- Every public repository runs a secret scan on push and on pull requests.
- R-15 is closed.

## Scope

**In scope:** the inventory repository's history and the docs repository's history; the devices and
services those credentials belong to; a secret scan in each public repository.
**Out of scope:** rewriting history; credentials never committed in plaintext.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A value is displayed during the check | control node | The script hashes both sides and prints only the variable name and the result |
| A rotation locks automation out of a device | the device | Rotate one device at a time, with console access ready, and update the vault in the same step |
| The scan blocks legitimate content (fingerprints, hashes) | CI | Start in report-only mode; add an allowlist before making it blocking |

## Prerequisites

- [ ] Vault decrypted on the control node
- [ ] Console access to any device the check finds live

## Procedure

### Step 1: Compare, without displaying

For every vault file ever committed unencrypted, and the one credential found in the docs history,
compare each historical value with the current vault value by digest. Read-only.

**Verify:** a list of names, each **replaced** or **live**.

### Step 2: Rotate what is live

One credential at a time: change it on the device or service, write the new value into the vault,
encrypt, commit and push (the lock-in in [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/)),
then confirm the automation that uses it still works. Document how each was rotated
([A8](/docs/architecture/reviews/2026-10-rebuild-and-access/#a8-rotation)).

**Verify:** Step 1 run again reports every name **replaced**.

### Step 3: Scan on every push

Add a secret-scan workflow (gitleaks or similar) to each public repository, report-only first, then
blocking once its allowlist covers the site's published fingerprints and hashes.

**Verify:** a test branch with a fake key fails the check; `main` passes.

### Step 4: Close the risk

Set R-15 to Closed, pointing at this record.

## Verification

Step 1 reports nothing live, the scan runs on every repository, and R-15 is closed.

## Undo

Rotation is not undone; the previous values are the exposed ones. The scan workflow can be removed.

## To discover

- Which credentials the history holds beyond the ones already known.
- Whether the old lab devices those files belonged to are still in service at all.
