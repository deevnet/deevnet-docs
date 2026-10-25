---
title: "CHG-0036: OpenBao's Keys From the Vault"
weight: -36
---

# CHG-0036: OpenBao's Keys From the Vault

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/). One issuing-CA ceremony for both tenant CAs; one OpenBao role run; one API deploy |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao), `dv02prv001v01` (the Deevnet API), the offline ceremony machine |
| **Automation** | `deevnet.mgmt` `playbooks/openbao.yml` and `site.yml --tags deevnet-api`; the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony |
| **Risk** | Medium. Most likely to go wrong: switching the Transit key leaves the API's stored copies unreadable until they are resealed or tenants resupply |
| **Related changes** | [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (built the Tenant Device CA inside OpenBao), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) (built the Tenant Service CA inside OpenBao), [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/) (before this), [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/) (after this) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/), [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/) |

---

## Summary

Three keys exist only inside OpenBao: the **Tenant Device CA's** key, generated there by CHG-0033,
the **Tenant Service CA's**, generated there by CHG-0047, and the **Transit key** that seals the
Deevnet API's stored copies of tenant secrets. All three were made non-exportable, so none can be
copied out. Losing OpenBao's storage loses all three: new tenant CAs, and a database nobody can read.
This change replaces each with a key made outside OpenBao, makes the vault the authoritative copy,
and loads them into OpenBao on every build, so a rebuilt OpenBao comes back with the same keys. It
also makes the role stop until a fresh initialization is locked in, and tightens OpenBao's own access
([2026-10 review: R1, T1, R5, A4](/docs/architecture/reviews/2026-10-rebuild-and-access/#responses-so-far);
[2026-10 tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P1).

**The tenant CAs are re-keyed under names without a site**, `Deevnet Tenant Service CA` and
`Deevnet Tenant Device CA`, still signed by the Mobile Site CA, because they serve tenants at every
site ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) §2,
[ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §4).
Devices trust the root, so none is touched. What the old Tenant Service CA issued, `eds`'s console
certificate and CHG-0047's probe certificates, runs to expiry; the Tenant Device CA has issued
nothing.

**The rule after this change:** any key OpenBao uses that can't be re-derived is held in ansible-vault
and loaded as configuration.

## Goal

- The Tenant Device CA's and the Tenant Service CA's keys are in ansible-vault, new and made outside
  OpenBao; each PKI mount holds its key, imported, and the certificate the Mobile Site CA signed for
  it under its site-less name.
- What the old Tenant Service CA issued keeps verifying: a server presents its chain, which needs
  nothing from OpenBao.
- The Transit key the API uses is in ansible-vault, imported into OpenBao; the API's stored copies
  are sealed under it.
- After a fresh initialization, the next run of the role stops until the vault's `ansible` AppRole can
  log in.
- The API's AppRole secret ID is bound to the provisioning VM's address and expires; Ansible's is bound
  to the Builder and the temporary builder.
- A file audit device records every request, on the identity VM's disk, rotated.
- The `ansible` AppRole is described as what it is: root-equivalent, held only in the vault.
- A rebuild drill: OpenBao's storage wiped and rebuilt, and both keys are back without a ceremony;
  the API reads its stored copies.

## Scope

**In scope:** the `openbao` role (PKI import, Transit import, the lock-in stop, CIDR binding, the audit
device); both tenant CAs re-keyed from vault-held keys and renamed; resealing the API's stored copies.
**Out of scope:** device certificates (CHG-0034); the build path (CHG-0037).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Stored copies unreadable after the Transit switch | the API | Import the new key under a new name, reseal every stored copy (decrypt with the old, encrypt with the new), and keep the old key until none remain; tenants' next apply resupplies anything missed |
| A key written only to a local file during the change | control node | The lock-in rule: vault, encrypt, commit, push before the next step |
| A tenant service certificate stops verifying | tenants | Verification needs only the chain the server presents; `eds`'s console checked after Step 1 and after Step 5 |
| The audit device fills the disk | identity VM | Rotation, and a size check in the role |
| A CIDR binding locks Ansible out | OpenBao | Bind to every address the control node uses, including the temporary builder's; the recovery key is the way back |

## Prerequisites

- [ ] Vault decrypted; collections built
- [ ] The offline ceremony machine, with its bootloader reset ([Ceremony](/docs/runbook/root-of-trust/ceremony/))
- [ ] Each tenant's state to hand, in case a stored copy has to be resupplied

## Procedure

### Step 1: Both tenant CAs from vault-held keys

For each of the Tenant Device CA and the Tenant Service CA, generate a key and a request on the
control node, under the CA's site-less name, write the key into the vault and lock it in. Sign both
requests in one [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony, then have the role
import each signed certificate with its key into its PKI mount and make it the default issuer.

**Verify:** each mount's default issuer has a key, chains to the Mobile Site CA, carries its
site-less name, and its key matches the vault's; `eds`'s console still verifies.

### Step 2: The Transit key from the vault

Generate a key, vault it, import it into OpenBao's Transit engine under a new name, point the API at
it, and reseal every stored copy.

**Verify:** the API's `/readyz` is `200`; every tenant's reconcile succeeds; no stored copy is under
the old key.

### Step 3: The lock-in stop

After an initialization, the role checks the vault's `ansible` AppRole can log in, and stops with a
message naming `.openbao/<host>-init.json` if not.

**Verify:** on a scratch run with deliberately stale vault values, the role stops with that message.

### Step 4: OpenBao's own access

CIDR-bind both AppRoles' secret IDs; give the API's an expiry; enable a file audit device with
rotation; correct the `ansible` AppRole's description.

**Verify:** a login from another host is refused; requests appear in the audit file.

### Step 5: The rebuild drill

Wipe OpenBao's storage and rebuild it from the role. Lock in its initialization (the stop in Step 3
enforces it).

**Verify:** both tenant CAs and the Transit key are the vault's; the API reads its stored copies
with no tenant resupplying anything.

## Verification

Step 5 passes, V3 and V12 of the
[tenant PKI validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass,
and the documents describe the new state: ADR-0016's conflict row and ADR-0033's open question 2 are
closed, and *Build-Time Secrets* and the OpenBao drills page say what is true.

## Undo

Until Step 5, each step reverses: the previous tenant CAs and Transit key stay in OpenBao until
the end. After Step 5, the old keys are gone by design.

## To discover

- OpenBao's exact mechanism for importing a Transit key (the "bring your own key" path) and a PKI
  issuer with its key, confirmed against OpenBao's current documentation, not assumed.
- Whether the API can reseal its stored copies itself, or needs a one-off tool.
- Whether CIDR binding of secret IDs behaves as expected through the routing between the Builder and
  the identity VM.
