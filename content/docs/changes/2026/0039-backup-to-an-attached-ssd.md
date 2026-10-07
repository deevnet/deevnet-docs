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
| **Status** | In Progress. Steps 1 and 2 are done on one USB flash drive: backups reach the drive and read back. The restore rehearsal, the second drive and the SSDs are outstanding |
| **Window** | Started 2026-10-07 with one USB flash drive standing in for the SSDs. A restore is readable in full only after [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01` (the drives), `dv02prv001v01` (what is backed up) |
| **Automation** | The `backup` role and `proxmox_vm`'s USB pass-through in `deevnet.mgmt`, a systemd timer, and `make backup-status`, `backup-now`, `backup-dry-run`, `backup-verify`, `backup-drive` |
| **Risk** | Low. Most likely to go wrong: a drive knocked loose on a mobile kit, so backups silently stop. The job fails loudly when the drive is absent |
| **Related changes** | [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (the Transit key in the vault, which makes a restored database readable) |
| **Related incidents** | None |
| **Related runbooks** | [Backup and Restore](/docs/runbook/substrate/recovery/backup-and-restore/), [Recovery](/docs/runbook/substrate/recovery/) |

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
- A job that runs **whenever the site is up and the newest backup is older than a day**, and on demand,
  writes a database dump and a mirror of the state bucket to the attached drive,
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
| The schedule | No fixed hour. A check runs ten minutes after every boot and hourly while the VM is up, and takes a backup when the newest good one is older than 24 hours. `make backup-now` takes one regardless | The kit is mobile and off most of the time, so a set hour is rarely met. A nightly timer was built first and replaced the same day |
| What counts as overdue | A backup is due and the VM has been up two hours without taking it | Time spent powered off is not a failure. `make backup-status` fails on this and nothing else |
| How the drive reaches the VM | A Proxmox USB resource mapping by vendor and product ID, declared in the VM's `mgmt_vm.usb` | Automation's API token may not name a raw host device; a mapping is the form it may attach. A second drive of the same model takes the first one's place with no change |
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

**State, 2026-10-07:** done for one drive, a 128 GB USB flash drive. It is passed through to
`dv02prv001v01` by the `deevnet-backup` USB mapping (`mgmt_vm.usb` in the VM's inventory entry,
applied by `playbooks/vm-usb.yml`), erased and prepared. There is no second drive yet, so nothing is
kept away from the kit.

Three things the step found:

- **The VM needed a cold start.** Proxmox does not hot-plug USB into this guest type, so the device
  appeared only after the VM was stopped and started. A drive of the same model plugged in later
  needs nothing.
- **USB 3 has to be asked for.** Proxmox attached the device to the guest's emulated USB 2 controller:
  5 Gb/s on the hypervisor, 480 Mb/s in the guest. The role now sets `usb3=1` unless told otherwise.
- **The job's own check ran during preparation.** It fired ten minutes after the cold start, found the
  freshly labeled drive and took a backup while the preparation still held the mount. Preparation now
  mounts the drive somewhere of its own.

### Step 2: The backup role

A role that, when a backup is due, dumps the database and mirrors the state bucket, puts both in one archive with a
manifest of checksums, encrypts it with `age` to the site's backup key, writes it to the drive, keeps
the newest 30, and fails visibly if the drive is absent.

**Verify:** a run writes encrypted files; unplugging the drive makes the next run fail.

**State, 2026-10-07:** done. The role is deployed to `dv02prv001v01` and the timer is enabled.

| Check | Result |
|---|---|
| `make backup-dry-run` builds and encrypts an archive with no drive | Pass: 72 kB, three state objects |
| The job with no drive attached fails | Pass: the unit is `failed`, with `backup drive absent: no filesystem labeled deevnet-backup` |
| `make backup-now` writes an encrypted archive to the drive | Pass |
| `make backup-verify` decrypts the newest archive on the drive with the key from the vault | Pass: checksums match, the dump is readable, 11 tables with data |
| A check with a fresh backup does nothing and succeeds | Pass: `not due: the newest good backup is 0h old, the interval is 24h` |
| A check with a backup older than the interval takes one | Pass, with the job's record of its last run set back 25 hours by hand |
| The drive is unmounted after every run | Pass |
| Retention removes the oldest | Pass, with the limit lowered to 2 for one run |
| Pulling the drive makes the next due check fail | Not run on a real unplug; the absent-drive path is the one above |

Nothing alerts on a failed check yet
([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)), so a missing
drive is seen by running `make backup-status`.

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
- Whether the two drives in the rotation must be the same model. The mapping names one vendor and
  product ID, so a different model means changing `mgmt_vm.usb`.
- Whether the drive should also be encrypted as a whole. It would hide file names and sizes, and it
  would put an unlock key on the host beside the drive.
