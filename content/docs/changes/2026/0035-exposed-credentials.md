---
title: "CHG-0035: Previously Exposed Credentials Checked and Rotated"
weight: -35
---

# CHG-0035: Previously Exposed Credentials Checked and Rotated

| | |
|---|---|
| **Date** | 2026-10-06 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-10-06.** No previously exposed credential is accepted anywhere: one was still in use and is replaced, and every device refused the old values. All 13 public repositories run a blocking secret scan. R-15 is closed. Wiping the Builder's old controller data removed the site's only Omada snapshot; a new one was taken of the live controller. See [What was done](#what-was-done). |
| **Window** | 2026-10-06. The live Omada controller was stopped from 19:00 to 19:02 EDT for its snapshot |
| **Site** | mobile |
| **Systems** | Whatever the check finds still live: devices, services and their vault entries. Every public `deevnet` repository, for the scan |
| **Automation** | A local comparison script, run on the control node; the devices' own interfaces or their roles, for rotation; a secret-scan workflow per repository |
| **Risk** | Low. Most likely to go wrong: a comparison that prints a value. The script compares digests and prints only names and match/no-match |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/), [Wireless AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/), [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/) |

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

- [x] Vault decrypted on the control node
- [x] Console access to any device the check finds live

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

## What was done

1. **Compared, without displaying.** `scripts/exposure-check.py` in the inventory compares every
   value ever committed in plaintext with the current vault by SHA-256 digest, and searches every
   repository's objects for current vault values. It prints names and counts, never a value.
   The list by name is in the operator's notes. Every credential in the March 2026 plaintext vault
   files had been replaced or removed. The one in the docs history, published by CHG-0005 and
   removed by #281, was still the vault's value.
2. **Tried the old values on the devices.** A new value in the vault does not prove the device
   stopped accepting the old one, so each was checked on its device. Where a login could test it,
   the old value was tried once and refused, beside a control with the current value that
   succeeded. Where it could not, the device's configuration was read: the old account and the
   old enable password are not configured at all.
3. **Rotated the one still in use** (inventory #74), and wrote down how in the
   [Wireless AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/) runbook. Nothing on
   a device changed: only adopting a factory-reset AP uses that credential.
4. **Wiped the Builder's cold-spare Omada controller.** Its data predated the rotations and could
   still have accepted old logins. It was rebuilt empty from the `omada_controller` role, stopped and
   disabled. Its backup directory went with it, and that held **the site's only Omada snapshot**, so:
5. **Snapshotted the live controller.** Stopped for two minutes, archived after a clean MongoDB
   shutdown, restarted, and checked with a `make wireless` plan: the AP connected, nothing differs
   from inventory. The archive is on `dv02nms001v01` with a checksum-verified copy on the Builder.
   It is on 6.3.0.45, so the fallbacks to 6.2 and 6.1, which restored the old 6.1 snapshot, no
   longer exist.
6. **Purged local copies.** Dropped `git stash` commits in the control node's inventory checkout
   held current vault values in plaintext. They had never been pushed: GitHub has none of them.
   They were expired and pruned.
7. **Added the secret scan.** One reusable workflow in `deevnet/.github` (gitleaks, pinned and
   checksum-verified, always redacted), called by every repository. It extends gitleaks' default
   rules with `unencrypted-ansible-vault`, because the default rules do not catch a `vault.yml`
   committed decrypted. Reviewed findings are in each repository's `.gitleaksignore`: placeholders,
   test fixtures, and the March 2026 vault lines, whose credentials were checked in steps 1 and 2.
   The scan ran report-only until every repository was clean, then became blocking.

## Verification

| Check | Result |
|---|---|
| `exposure-check.py` after the rotation | Nothing live; no current vault value in any blob of the 12 local repositories |
| Old values on their devices | None accepted: refused at login, or absent from the configuration |
| Secret scan, every public repository, whole history | 13 of 13 "no leaks found" |
| A test branch with a decrypted `vault.yml` | Failed the blocking check, value redacted in the log; branch deleted |
| Omada controller after the snapshot | Same version and `omadacId`; AP connected; `make wireless` plan: no changes |
| Snapshot copy on the Builder | Checksum matches; the archive lists end to end |

## Undo

Rotation is not undone; the previous values are the exposed ones. The scan workflow can be removed.

## Follow-ups

- [ ] Take Omada snapshots routinely. There is one, taken by hand
      ([roadmap](/docs/roadmap/infrastructure/mobile/management-plane/))
- [ ] The Builder's firewall opens `1025-65535/tcp`, far wider than its services need. Found during
      this change, not changed by it

## Discovered

- **Beyond the known credentials:** none. A pattern scan of every repository's history found only
  placeholders and test fixtures.
- **The old lab devices:** the router, switch and controller those files belonged to are all still
  in service, which is why each old value was tried on the device itself.
