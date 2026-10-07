---
title: "CHG-0039: Backup to an Attached SSD"
weight: -39
---

# CHG-0039: Backup to an Attached SSD

| | |
|---|---|
| **Date** | Started 2026-10-07 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | In Progress. The job is installed and proven without a drive; no backup has reached a drive yet |
| **Window** | Started 2026-10-07 with one USB flash drive standing in for the SSDs. A restore is readable in full only after [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01` (the drives), `dv02prv001v01` (what is backed up) |
| **Automation** | The `backup` role in `deevnet.mgmt`, a systemd timer, and `make backup-status`, `backup-now`, `backup-dry-run`, `backup-verify`, `backup-drive` |
| **Risk** | Low. Most likely to go wrong: a drive knocked loose on a mobile kit, so backups silently stop. The job fails loudly when the drive is absent |
| **Related changes** | [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (the Transit key in the vault, which makes a restored database readable) |
| **Related incidents** | None |
| **Related runbooks** | [Recovery](/docs/runbook/substrate/recovery/) |

---

## Summary

The Deevnet API's database (the tenant registry, its audit log and its sealed copies of tenant
secrets) and the state bucket (tenants' Terraform state) sit on the provisioning VM's OS disk, with no
copy. A backup is a **recovery shortcut**: tenants can rebuild from their repositories without one,
but restoring it plus one reconcile brings every tenant back as it was. Until
[CHG-0040](/docs/changes/2026/0040-device-secrets-in-tenant-code/) moves device secrets into tenant
code, it is also the only thing that spares devices a visit when the provisioning VM is lost
([2026-10 review: R2](/docs/architecture/reviews/2026-10-rebuild-and-access/#r2-registry-and-state-on-one-vm)).

## Goal

- Two USB SSDs, one attached to the management hypervisor and one kept away from the kit, swapped on a
  schedule.
- A nightly job writes a database dump and a mirror of the state bucket to the attached drive,
  **encrypted before it reaches the drive** with a key held in ansible-vault. A lost drive is
  ciphertext; a restore needs only the vault.
- **Nothing is ever written to the drive unencrypted.** The drive's filesystem is plain, so every file
  on it is an encrypted archive. Its file names and sizes are readable to whoever holds the drive; its
  contents are not.
- A missing drive fails the job visibly.
- A restore has been carried out once, onto a freshly built provisioning VM, followed by a reconcile.
- Recovery documents the backup as a shortcut, and how to restore it.

## Scope

**In scope:** the API database and the state bucket.
**Out of scope:** whole-VM images; OpenBao (its keys come from the vault after CHG-0036); tenant
bucket contents (tenants' own); Keycloak (not built).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A restore older than a tenant's last apply puts old values back | the API | A restore is always followed by a reconcile, and tenants' next apply resupplies anything newer |
| The backup key is lost | the vault | It lives in ansible-vault, which is locked in like any other secret. No host holds a copy: the job encrypts to the public half |
| Flash wears out or fails silently | the first drive | `make backup-verify` reads the newest archive back from the drive; the SSDs replace it |
| Restore rehearsal disturbs the live site | `dv02prv001v01` | Rehearse on a declared, rebuildable substrate VM, never an ad-hoc one; experiments don't run on the hypervisors |

## Decisions

**Each question the plan left open is settled here.**

| Question | Decision | Reason |
|---|---|---|
| Where the job runs | On the provisioning VM, with the drive passed through to it | The data never leaves the host that holds it, no host gains a credential to reach into another, and the hypervisor gains nothing but a device mapping |
| `age` or `restic` | `age`, encrypting to a public key | The host that writes backups holds only the public half, so it cannot read them and there is no secret on it to steal. `restic` needs its repository password on the host. The archives are tens of kilobytes, so deduplication buys nothing |
| What the state bucket's copy is | Its current objects, read over S3 | A restore does not depend on the store being the same software or version ([ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)). Earlier object versions are not carried; the dated archives are the history |
| How the drive is found | By filesystem label `deevnet-backup`, plus a marker file | Both drives in the rotation carry the same label, so a swap changes nothing. The job refuses a second labelled drive, or one without the marker |
| When the drive is mounted | Only while a run writes | The drive can be pulled at any other time, which is what a swap on a mobile kit needs |
| The schedule | 02:30 nightly, and at the next boot if the kit was off | The kit is often off overnight |
| Retention | The newest 30 archives per drive | Weeks of history at a few megabytes |
| The first drive | A USB flash drive, until the SSDs arrive | A backup on flash now is worth more than one on an SSD later. The drive is not what makes a backup trustworthy; the rehearsal in step 3 is |

## Prerequisites

- [ ] Two USB SSDs bought. Started without them, on one USB flash drive
- [ ] CHG-0036 complete (the Transit key in the vault). Not a blocker for writing backups: until then a
      restored database's sealed tenant secrets are readable only while the same OpenBao survives
- [x] Vault decrypted; collections built

## Procedure

### Step 1: The drives

Attach one drive to the management hypervisor, pass it through to the provisioning VM, and prepare it
with `make backup-drive SERIAL=<serial>`, which erases it, labels it `deevnet-backup` and writes the
marker. Its filesystem is plain; the backup files are encrypted.

**State, 2026-10-07:** not done. The management hypervisor has no USB drive attached. The one USB drive
on the site is in the tenant hypervisor and holds an installer image, so it was left untouched. The
`proxmox_vm` role cannot yet pass a USB device through; that is built and tested when the drive is in
place.

### Step 2: The backup role

A role that, nightly, dumps the database and mirrors the state bucket, puts both in one archive with a
manifest of checksums, encrypts it with `age` to the site's backup key, writes it to the drive, keeps
the newest 30, and fails visibly if the drive is absent.

**Verify:** a run writes encrypted files; unplugging the drive makes the next run fail.

**State, 2026-10-07:** the role is deployed to `dv02prv001v01` and the timer is enabled.

| Check | Result |
|---|---|
| `make backup-dry-run` builds and encrypts an archive with no drive | Pass: 72 kB, three state objects |
| `make backup-verify SOURCE=dry-run` decrypts it with the key from the vault | Pass: checksums match, the dump is readable, 11 tables with data |
| The job with no drive attached fails | Pass: the unit is `failed`, with `backup drive absent: no filesystem labelled deevnet-backup`; `make backup-status` fails with "No backup has ever succeeded" |
| A run writes an encrypted archive to a drive | Not run: no drive |
| Unplugging the drive makes the next run fail | Not run on a real unplug; the absent-drive path is the one above |
| The 31st archive removes the oldest | Not run |

Until step 1 is done the job fails every night. That is the intended signal, and it is the only one:
nothing alerts on it yet ([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)), so it
is seen by running `make backup-status`.

### Step 3: Rehearse a restore

Restore onto a freshly built provisioning VM, then `make reconcile --all`.

`make backup-verify` proves an archive can be read with the key from the vault. It restores nothing;
the restore itself is written and proven in this step.

**Verify:** every tenant's plan is clean, and its devices still connect.

### Step 4: The docs

Recovery and the recovery chart describe the backup as a shortcut, and how to restore.

## Verification

Step 3 passes, and the job has run unattended for a week.

## Undo

Remove the role and the timer; the drives keep what they hold until wiped.

## To discover

- Which declared VM the restore rehearsal uses.
- Whether a replacement drive of a different model needs the device mapping changed, or whether the
  two drives must be the same model.
- Whether the drive should also be encrypted as a whole. It would hide file names and sizes, and it
  would put an unlock key on the host beside the drive.
