---
title: "CHG-0061: The Core Router Restored From Its Vaulted Backup"
weight: -61
---

# CHG-0061: The Core Router Restored From Its Vaulted Backup

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Change type** | Configuration |
| **Classification** | Disruptive |
| **Status** | Planned |
| **Window** | 2026-11-11, with the operator at the router's web UI. One router reboot: no routing, DNS or DHCP for the site for a few minutes |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router) |
| **Automation** | `ansible-inventory-deevnet` `backups/mobile/dv02cor002p01/config.xml.vault`, written by `make backup-router` in `deevnet.net`; `ansible-vault decrypt` |
| **Risk** | Medium. Most likely to go wrong: the router reboots into a configuration that does not bring the management segment up, which leaves only the console |
| **Related changes** | [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (the firewall role's pre-apply snapshot) |
| **Related incidents** | None |
| **Related runbooks** | [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/), [Console Recovery: Core Router](/docs/runbook/substrate/recovery/console-recovery/core-router/) |

---

## Summary

The core router's configuration is backed up vault-encrypted into the inventory, at
`backups/mobile/dv02cor002p01/config.xml.vault`. The first backup was taken on 2026-11-11 at 12:12.
No restore has been done from it yet, so nobody knows whether it would bring the router back.

This change restores that backup onto the running router, following steps 2–5 of
[Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/). The backup is
decrypted from a fresh clone of the inventory taken from GitHub, not from the Builder. Step 1, the
OPNsense reinstall, is left out: the router keeps its install, and only its configuration is
replaced. The backup is minutes old, so the router should come back as it was.

## Goal

- The backup decrypts from a fresh GitHub clone, with the vault password alone.
- The router accepts it, reboots, and comes back on `10.20.99.1` and every VLAN.
- The network checks match the baseline taken before the change.
- The plaintext the decrypt produced is deleted, as are the older plaintext copies in
  `migration-logs/`.

## Scope

**In scope:** decrypting the backup, the restore from the web UI, and the reboot and checks.
**Out of scope:** reinstalling OPNsense. That path's own steps are unchanged, and the reinstall
itself stays unrehearsed.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The restored configuration does not bring management up | the router | The configuration in use before the restore stays in the router's own history (`/conf/backup`). [Console Recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/) restores it with **Restore a backup**; its file name is noted in Step 1 |
| The router changed after the backup, and the restore undoes it | the router | Step 1 checks that the newest revision in the router's history is the one from before the backup. If a newer one exists, take a new backup first |
| The decrypted `config.xml` outlives the change | the operator's computer | Step 5 deletes it and the clone. It holds the router's private keys |
| The site is offline during the reboot | every segment | Expected, and the reason this change is Disruptive. Nothing is mid-deploy |

## Prerequisites

- [ ] The backup on GitHub: `router-config-backup` branch of `ansible-inventory-deevnet` (PR #97)
- [ ] Console cable and a terminal ready for the router, in case management does not come back
- [ ] On the computer whose browser does the restore: `git`, `ansible-vault`, and the vault password
- [ ] Baseline from the Builder, taken 2026-11-11 12:16: the web UI answers; `dv02hyp001p01` and
      `api` resolve through `10.20.99.1`; `10.20.25.20` and `1.1.1.1` answer ping; HTTPS to
      GitHub works. Already failing before the change: a ping to `10.20.30.11`, and
      `tdemo-1.tdemo` returns no address

## Procedure

### Step 1: Note the revision to undo to

**Run:** in the web UI, open **System → Configuration → History**.

**Verify:**

1. Note the newest revision's date and file name: that is the configuration running now, and the
   one to pick at the console if the restore needs undoing.
2. It is no newer than the backup (2026-11-11 12:12). If it is, stop and take a fresh
   `make backup-router` first.

**Undo:** nothing to undo.

### Step 2: Decrypt the backup from GitHub

Not disruptive.

**Run:**

```bash
git clone -b router-config-backup https://github.com/deevnet/ansible-inventory-deevnet.git ~/rehearsal
cd ~/rehearsal
ansible-vault decrypt --output ~/rehearsal/config.xml backups/mobile/dv02cor002p01/config.xml.vault
```

**Verify:**

1. `grep -c '<opnsense>' ~/rehearsal/config.xml` prints `1`.

**Undo:** `rm -rf ~/rehearsal`.

### Step 3: Restore it

Disruptive: the router reboots.

**Run:** in the web UI, open **System → Configuration → Backups**. Under **Restore**, choose
**All** as the area, pick `~/rehearsal/config.xml`, keep **Reboot after a successful restore**
selected, and restore.

**Verify:**

1. The page reports the restore succeeded before the router reboots.

**Undo:** [Undo Step 3](#undo-step-3).

### Step 4: Check the site

**Run:** from the Builder, the baseline checks again, once the web UI answers.

**Verify:**

1. Every check that passed in the baseline passes again.
2. The firewall role's plan shows no drift. It reports and writes nothing without
   `firewall_apply=true`:

   ```bash
   cd ansible-collection-deevnet.net
   ANSIBLE_ASK_VAULT_PASS=true make migration-opnsense-firewall
   ```

**Undo:** [Undo Step 3](#undo-step-3).

### Step 5: Delete the plaintext

**Run:**

```bash
rm -rf ~/rehearsal                                            # the operator's computer
rm /srv/dvnt/migration-logs/*-pre-firewall-*.xml              # the Builder
rm /srv/dvnt/ansible-collection-deevnet.net/migration-logs/*-pre-firewall-*.xml
```

**Verify:**

1. No `*.xml` is left in either `migration-logs/` directory.

**Undo:** no undo. The vaulted backup replaces them, and Step 4 proves it restores.

## Verification

The router came back from the vaulted backup alone, and the site matches the baseline.

## Undo

### Undo Step 3

If the web UI answers, restore the revision noted in Step 1 from **System → Configuration →
History**. If it does not, follow
[Console Recovery: Core Router](/docs/runbook/substrate/recovery/console-recovery/core-router/):
**Restore a backup** at the console, choosing that revision.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the revision to undo to noted, and no newer than the backup
- [ ] Step 2: the backup decrypted from a fresh GitHub clone
- [ ] Step 3: the backup restored, the router rebooted
- [ ] Step 4: the baseline checks pass again, the firewall plan shows no drift
- [ ] Step 5: the decrypted copy and the old plaintext copies deleted

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ]
