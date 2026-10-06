---
title: "CHG-0039: Backup to an Attached SSD"
weight: -39
---

# CHG-0039: Backup to an Attached SSD

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. Needs the drives; needs [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01` (the drives), `dv02prv001v01` (what is backed up) |
| **Automation** | A new `backup` role in `deevnet.mgmt`; a systemd timer |
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
| The backup key is lost | the vault | It lives in ansible-vault, which is locked in like any other secret |
| Restore rehearsal disturbs the live site | `dv02prv001v01` | Rehearse on a declared, rebuildable substrate VM, never an ad-hoc one; experiments don't run on the hypervisors |

## Prerequisites

- [ ] Two USB SSDs bought
- [ ] CHG-0036 complete (the Transit key in the vault)
- [ ] Vault decrypted; collections built

## Procedure

### Step 1: The drives

Attach one drive to the management hypervisor, label both, and record in inventory how the attached one
is found. Its filesystem is plain; the backup files are encrypted.

### Step 2: The backup role

A role that, nightly, dumps the database and mirrors the state bucket, encrypts both with a key from the
vault (`age` or `restic`), writes them to the drive, keeps a set number of copies, and fails visibly if
the drive is absent.

**Verify:** a run writes encrypted files; unplugging the drive makes the next run fail.

### Step 3: Rehearse a restore

Restore onto a freshly built provisioning VM, then `make reconcile --all`.

**Verify:** every tenant's plan is clean, and its devices still connect.

### Step 4: The docs

Recovery and the recovery chart describe the backup as a shortcut, and how to restore.

## Verification

Step 3 passes, and the job has run unattended for a week.

## Undo

Remove the role and the timer; the drives keep what they hold until wiped.

## To discover

- Whether the job runs on the provisioning VM, with the drive passed through to it, or on the
  hypervisor, with the provisioning VM pushing to it. The first keeps substrate data off the host; the
  second survives the VM.
- `age` or `restic`: restic adds deduplication and retention, age is simpler.
- Which declared VM the restore rehearsal uses.
