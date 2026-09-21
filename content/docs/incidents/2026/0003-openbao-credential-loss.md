---
title: "INC-0003: OpenBao's Recovery Key and AppRole Destroyed by a Git Reset"
weight: 3
---

# INC-0003: OpenBao's Recovery Key and AppRole Destroyed by a Git Reset

| | |
|---|---|
| **Date** | 2026-09-17 |
| **Site** | mobile (`dvntm`) |
| **Systems** | OpenBao on `dv02idn001v01`; the Deevnet API on `dv02prv001v01`; the inventory repository `ansible-inventory-deevnet` |
| **Severity** | Provisioning only. OpenBao kept running and self-unsealing, the Deevnet API kept serving, and both live tenants — `tdemo` and `eds` — were unaffected throughout, including during the rebuild. No client-facing outage. |
| **Status** | **Closed · Completed 2026-09-21.** The cause was a lock-in failure, and the corrective action is the policy: a once-only secret a change generates is encrypted, committed and **pushed** before the change goes any further. That is written into Vault Operations and the change-management checklist (actions 1–2). The rebuild itself was within [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)'s scope — it ran twice, not once. The follow-ups it prompted are improvements rather than incident work, and each is carried by [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/). |
| **Cause** | `git reset --hard` run in a repository whose vault files were decrypted, eight minutes after an initialisation wrote once-only credentials into one of them |

---

## Summary

During [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/), step 3 initialised OpenBao. That run
produces three values that exist nowhere else: the **recovery key**, and the **role ID and secret ID
of Ansible's AppRole**. It writes them to `.openbao/<host>-init.json` on the control node, and the
change record instructs the operator to move them into the inventory vault and delete that file.

They were moved into the vault file — which was **decrypted**, because the inventory had been
unvaulted for the change window, and therefore an uncommitted modification. The init file was deleted
as instructed. Eight minutes later, merging the change's pull requests hit a branch that would not
fast-forward, and `git reset --hard origin/main` was used to resolve it. That discarded every
decrypted vault file and restored the committed versions — in which those three values are still
commented-out placeholders.

Plaintext is never staged in this repository, by design and by pre-commit hook, so the discarded
content was never in the object database. There was nothing to recover.

## Impact

The static seal key was unaffected — it was committed before the window — so **OpenBao continued to
run and to unseal itself**, and the Deevnet API continued to serve both tenants. What was lost was
the ability to *administer* OpenBao:

- Ansible could no longer authenticate, so the `openbao` and `deevnet_api` roles would fail on their
  next run.
- The root token had been revoked at the end of the same initialisation, by design.
- A new root token requires the recovery key.

The instance was working and permanently unadministrable.

## What was ruled out

Every recovery route was checked before deciding to rebuild:

| Route | Result |
|---|---|
| `origin` | Nothing beyond the change's own merge; the last commit to the file predated the init by eight minutes |
| Git object database | 455 blobs scanned for an uncommented value — the plaintext was never staged, so no blob existed |
| `git stash`, reflog, `fsck --lost-found` | Empty; none of them sees unstaged working-tree content |
| Filesystem snapshots | `/srv` is xfs with no LVM or btrfs snapshots |
| A second copy of the init file | Deleted, with `shred` |
| The Deevnet API's own AppRole | Its policy names only its KV path, the Transit key and one PKI role; it cannot read `auth/approle/*` |
| OpenBao's audit log | No audit device was enabled — ADR-0016's own open question 2 |

## Resolution

The rebuild is the path [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/) §6
already described, and the seal key being intact made it straightforward:

1. The API was stopped and the Raft directory **moved aside, not deleted**
   (`/srv/openbao/data.unadministrable-2026-09-17`).
2. `playbooks/openbao.yml` re-initialised on empty storage: new recovery key, new AppRoles, new PKI
   root, new Transit key, root token revoked.
3. **The three values were encrypted, committed and pushed before anything else was done**, and only
   then was the init file deleted.
4. The `deevnet_api` role rewrote KV from the vault, issued a certificate from the new CA and took a
   new AppRole.
5. The new CA was redelivered to both tenant repositories and to the egress agent.
6. Both tenants resupplied their TSIG and state secrets, which are authoritative in their own
   Terraform state (ADR-0015 §4), so the columns are sealed under the new Transit key.

Verified afterwards: OpenBao `sealed:false` on the unchanged seal key, both plays `changed=0`, the API
ready over the new CA, all five tenant names resolving forward and both reverse records naming their
workload, the agent rendering both VRFs, and both tenants' plans clean.

## Three defects the rebuild exposed

None of these were caused by the loss; all three were latent and would have surfaced on any CA or key
rotation.

**The API's certificate was never reissued.** A rebuilt OpenBao generates a new PKI root under the
same common name, so the host's certificate stayed valid for its full term and
`openssl x509 -checkend` was satisfied — while everyone else had been handed the new CA and could not
verify it. The role now also compares the CA the host holds with the one OpenBao serves.

**Handlers flushed after the readiness wait.** A reissued certificate left the container serving the
old one while the wait verified against the new CA, and because the play then aborted the restart
handler never ran — so the next run found nothing changed and failed identically. A deadlock that had
to be broken by hand.

**An unreadable stored secret made the tenant unauthenticatable.** The failed Transit decrypt was
returned from the store, so `Get` errored, the token hash was never compared, and every tenant call
answered `401`. ADR-0016 §6's stated recovery — the tenant resupplies from its own state — was closed
by the very condition it exists for. An unreadable secret now reads as empty and is logged.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Write down the lock-in order for a once-only secret — encrypt, commit, **push**, then delete the source file, as one action — and what must never run while the tree is decrypted, `git reset --hard` first, with the alternative for a blocked pull | [Vault Operations](/docs/runbook/building-recovery/vault-operations/) | {{< action-status "Done" >}} |
| 2 | Put the rule on the checklist, because that is where it bites | [Change Management](/docs/runbook/change-management/) | {{< action-status "Done" >}} |
| 3 | Administer OpenBao without `site.yml --limit` on a host that would also run the `powerdns` per-tenant loop | `playbooks/openbao.yml` | {{< action-status "Done" >}} |
| 4 | Fix the three code defects the rebuild exposed | See [Three defects the rebuild exposed](#three-defects-the-rebuild-exposed) | {{< action-status "Done" >}} |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 5 | An audit device for OpenBao. It would not have recovered these values, but it is the only record of what a token did, and this incident is the second time its absence has been felt | ADR-0016 open question 2 | {{< action-status "Scheduled" >}} [ADR-0016 → Open questions](/docs/architecture/decisions/0016-substrate-secrets-openbao/#open-questions), question 2 |
| 6 | A Raft snapshot, taken and copied off the VM. It would not have held the recovery key either, but it is the missing half of OpenBao's durability | ADR-0014; ADR-0016's last unconfirmed claim | {{< action-status "Scheduled" >}} [ADR-0016 §1](/docs/architecture/decisions/0016-substrate-secrets-openbao/#1-one-instance-in-the-identity-vm): a scheduled snapshot, copied off the VM |
| 7 | Let a tenant tell when its stored secrets are gone, so ADR-0016 §6's recovery is an ordinary `terraform apply` rather than an operator's `curl` | API v0.2.5 `secrets_stored`; provider `ModifyPlan` | {{< action-status "Done" >}} 2026-09-17 |
| 8 | Key-change drill: rotate the keys in place and watch the consumers recover | [OpenBao Drills](/docs/runbook/recovery/substrate-secrets-drills/) | {{< action-status "Done" >}} 2026-09-17; to repeat on a schedule |
| 9 | Snapshot-restore drill: a Raft snapshot onto a fresh instance with the same seal key | ADR-0014; ADR-0016 | {{< action-status "Scheduled" >}} [ADR-0016 → To confirm when building](/docs/architecture/decisions/0016-substrate-secrets-openbao/#to-confirm-when-building); needs 6 |
| 10 | A vault password file, so a rebuild can run without decrypting the repository — the condition that made the loss possible | ADR-0016 §2 | {{< action-status "Declined" >}} — see below |

**7, proven.** Rotating the Transit key past both tenants' stored secrets gave each tenant's plan one
in-place change — the three secrets and the flag, with the index and numbering untouched — and
applying resealed them.

**8 and 9 are not the same exercise.** The three defects above were found because the rebuild
produced **keys the site had never seen before** — not because the credentials were lost, and not
because data was restored.

- **A snapshot restore** (9) proves the data survives: KV, Transit and PKI come back *identically*. It
  would **not** have found any of the three defects, because nothing's key or issuer changes.
- **A key change** (8) is what finds them, and it needs no wipe. It ran on the live site on 2026-09-17,
  passed, and found nothing new — which is the result worth having: it exercises exactly the three
  fixes above, so it is now their regression test. Rotating the PKI root and moving the default issuer
  made the role reissue, flush its handler in time and come back verifiable; rotating the Transit key
  and raising `min_decryption_version` made both tenants' stored secrets unreadable, and the API
  degraded to empty and logged it instead of answering `401`, so both tenants authenticated and
  resupplied, resealing under `v2`.

**10, declined on purpose** (ADR-0016 §2): the vault password unlocks the seal key, the seal key unlocks OpenBao, and OpenBao holds
every runtime credential on the site, so putting that password in a file on the control node would make
shell access to the Builder equivalent to holding every secret here. A human holding it is the one link
automation cannot follow, and that is worth more than an unattended run. The mitigation is a short
decrypted window and immediate lock-in, not a stored password.
