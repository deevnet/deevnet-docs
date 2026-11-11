---
title: "CHG-0062: Router and Wi-Fi Controller Backed Up After Every Change"
weight: -62
---

# CHG-0062: Router and Wi-Fi Controller Backed Up After Every Change

| | |
|---|---|
| **Date** | 2026-11-11 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | 2026-11-11. No outage: one sshd reload on `dv02nms001v01`; the rehearsal runs on the Builder's stopped cold controller, not the live one |
| **Site** | mobile |
| **Systems** | `dv02nms001v01` (Omada controller and its host); `dv02cor002p01` (core router, read only); `dv00bld001p01` (the Builder's cold controller) |
| **Automation** | `deevnet.net`: roles `omada_backup` and `opnsense_backup`, `scripts/seal-backups.py`, `make backup-wireless`, `make backup-router`, `make seal-backups`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: the sshd drop-in that lets the controller log in over SFTP also allows password logins for other accounts. The role checks with `sshd -T` before reloading and backs the drop-in out if the check fails |
| **Related changes** | [CHG-0061](/docs/changes/2026/0061-core-router-restore-rehearsal/) (the router's backup, restored) |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (why nothing here crosses the core router) |
| **Related runbooks** | [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/), [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/) |

---

## Summary

The core router's configuration is backed up, vault-encrypted, into the inventory, and a restore from
it was proven in CHG-0061. Until now the backup ran only before a firewall apply, so `make opnsense`,
`make dns` and `make dhcp` changed the router without one. The Wi-Fi controller's only backup is a
single snapshot of its data directory, taken by hand on 2026-10-06.

The site is mostly built, so the rule is simple: **a device is backed up when something changes it,
after the change.** The copy in the inventory is then the device as it is. Rollback does not need it,
because the router keeps its own revision history and the firewall role records which revision to
go back to.

This change:

- **Ends every play that writes to the router with a backup.** That covers the DNS, DHCP, routes,
  Wake-on-LAN and certificate plays, the full `opnsense` play, and the firewall play after an apply.
- **Backs up the Wi-Fi controller's settings the same way**, after `make wireless APPLY=1` and with
  `make backup-wireless`. The controller's documented Open API can only send a backup to a file
  server, so it sends it over SFTP to a dedicated account on its own host. The account has no shell,
  is chrooted, can log in with a password only from the host itself, and is locked except while a
  backup runs, with a new random password each time.
- **Seals each backup into the inventory**, encrypted with the vault password, at
  `backups/mobile/<host>/`. A backup that has not changed since the committed one is not rewritten.
- **Rehearses a restore of the controller's backup** on the Builder's cold controller. The live
  controller is not touched.

## Goal

- `make backup-wireless` stages and seals `backups/mobile/dv02nms001v01/omada-backup.cfg.vault`, and
  leaves the `omada-backup` account locked and its upload directory empty.
- On `dv02nms001v01`, password logins are allowed only for `omada-backup` from 127.0.0.1, and are
  still refused for every other account and address.
- A router play that changes nothing leaves nothing to commit.
- The Builder's cold controller, restored from the vaulted backup decrypted from GitHub, shows the
  live controller's site, networks, SSIDs and PPSK profiles.
- The cold controller is returned to its never-configured state afterwards.

## Scope

**In scope:** `deevnet.net` PR (`device-backups-after-change`); the first controller backup; one router
play run as a no-change test; the rehearsal on the Builder; the runbooks.
**Out of scope:** restoring onto the live controller; the tenant Wi-Fi keys a controller restore loses
if they changed after the backup (a tenant's next `terraform apply` puts them back); a timer.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The sshd drop-in opens password logins wider than intended | `dv02nms001v01` | `sshd -T -C` checks four connections before reload; on a failure the drop-in is removed and sshd is not reloaded. Matching was tested on OpenSSH 10.0: the Match block ends with its file |
| The account is left unlocked, or a backup left in its upload directory | `dv02nms001v01` | The role locks the account and empties the directory in an `always` block, whether or not the backup worked |
| The Open API client lacks the permission the backup call needs ("Global Other Setting Modify") | the controller | The call fails and the role reports the controller's error; nothing else changes |
| The restored cold controller manages the live devices | the Builder | Adopted devices report to the controller at `10.20.99.40`, not the Builder. The cold controller runs only for the rehearsal and is stopped straight after |
| A decrypted backup outlives the change | the operator's computer | Step 4 deletes it |

## Prerequisites

- [ ] `deevnet.net` checked out on `device-backups-after-change` on the Builder
- [ ] On the computer whose browser does the rehearsal: `git`, `ansible-vault`, and the vault password

## Procedure

### Step 1: The first controller backup

Not disruptive: one sshd reload on `dv02nms001v01`.

**Run:**

```bash
cd /srv/dvnt/ansible-collection-deevnet.net
ANSIBLE_ASK_VAULT_PASS=true make backup-wireless
```

**Verify:**

1. The four `sshd -T` checks pass.
2. The run reports the backup's size, and the seal step writes
   `backups/mobile/dv02nms001v01/omada-backup.cfg.vault`.
3. On `dv02nms001v01`, `sudo passwd -S omada-backup` reports the account locked, and
   `/var/lib/omada-backup/upload` is empty.

**Undo:** [Undo Step 1](#undo-step-1).

### Step 2: A router play that changes nothing

**Run:** `ANSIBLE_ASK_VAULT_PASS=true make dns`

**Verify:**

1. The play ends with the backup role, and the seal step reports the router's backup unchanged since
   the committed one.

**Undo:** nothing to undo.

### Step 3: Commit the controller's backup

**Run:** commit the sealed file on a branch from `main` in `ansible-inventory-deevnet`, and open a pull request.

**Verify:**

1. The pre-commit hook accepts it as vault ciphertext.

**Undo:** close the pull request.

### Step 4: Rehearse a restore on the Builder's cold controller

Not disruptive: the live controller is untouched.

**Run:**

1. Keep the cold controller's never-configured state:
   `sudo tar --selinux --xattrs --acls -czpf /opt/omada-controller-backup/cold-empty-2026-11-11.tar.gz -C /opt omada-controller`
2. Decrypt the backup from GitHub on the operator's computer:
   `ansible-vault decrypt --output ~/rehearsal/omada-backup.cfg backups/mobile/dv02nms001v01/omada-backup.cfg.vault`
3. Start the cold controller: `sudo systemctl start omada-controller` on the Builder.
4. At `https://10.20.99.95:8043/`, restore from `~/rehearsal/omada-backup.cfg` instead of running
   the setup wizard.

**Verify:**

1. The restored controller shows the live controller's site, its LAN networks, SSIDs and PPSK
   profiles, and the AP as a known device that is not connected.

Then: `sudo systemctl stop omada-controller` on the Builder, return it to its never-configured state
from the tar, and `rm -rf ~/rehearsal` on the operator's computer.

**Undo:** [Undo Step 4](#undo-step-4).

### Step 5: Runbooks

Rebuild the Core Router and Omada Controller Recovery describe the backups as they now are; the
patching, controller upgrade and console recovery pages take a backup after a change made by hand
or by an upgrade.

**Undo:** revert the docs pull request.

## Verification

The controller's backup restores onto a controller that has never been configured, and a router play
that changed nothing leaves nothing to commit.

## Undo

### Undo Step 1

On `dv02nms001v01`: `sudo rm /etc/ssh/sshd_config.d/10-omada-backup.conf && sudo systemctl reload sshd`,
then `sudo userdel omada-backup && sudo rm -rf /var/lib/omada-backup`.

### Undo Step 4

`sudo systemctl stop omada-controller` on the Builder, then
`sudo rm -rf /opt/omada-controller && sudo tar --selinux --xattrs --acls -xzpf /opt/omada-controller-backup/cold-empty-2026-11-11.tar.gz -C /opt && sudo restorecon -R /opt/omada-controller`.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the first controller backup sealed; the account locked, the upload directory empty
- [ ] Step 2: a router play that changed nothing left nothing to commit
- [ ] Step 3: the controller's backup committed through a pull request
- [ ] Step 4: the backup restored onto the Builder's cold controller, which is back to never-configured
- [ ] Step 5: the runbooks describe the backups as they are

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ]
