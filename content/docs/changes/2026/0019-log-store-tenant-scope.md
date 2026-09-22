---
title: "CHG-0019: Strip the Log Store to Tenant Scope"
weight: 19
---

# CHG-0019: Strip the Log Store to Tenant Scope

| | |
|---|---|
| **Date** | 2026-09-22 |
| **Change type** | Configuration · Decommission |
| **Classification** | Routine |
| **Status** | **Complete 2026-09-22.** |
| **Window** | 2026-09-22 12:45 to 13:00 |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (the store), `dv02nms001v01` (trial leftovers) |
| **Automation** | `deevnet.mgmt` `site.yml --tags log-store`; inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. It only removes things: a listener nothing sends to, users no host holds a live config for, and a trial's leftovers. The one irreversible step is optional: clearing `(0, 0)`. |
| **Related changes** | [CHG-0018](/docs/changes/2026/0018-central-log-store/) (built what this removes) |
| **Related incidents** | [INC-0004](/docs/incidents/2026/0004-core-router-lost/) |
| **Related runbooks** | [ADR-0027: Tenant Log Store](/docs/architecture/decisions/0027-tenant-log-store/) |

---

## Summary

[ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/) makes the central log store
tenants-only. CHG-0018 built it for ADR-0022's wider scope, so it still carries parts only substrate
shipping needed:
- an unauthenticated syslog listener on 6514 and its five source rules
- six vmauth ingest users, one per `log_shippers` host, and their six vault tokens
- on `nms`, the leftovers of a one-host shipping trial

This change removes them. What stays: VictoriaLogs, vmauth over TLS, and the operator's read user.
The tenant-token change will add tenants' users.

## Goal

| | |
|---|---|
| Syslog port 6514 on `obs` | not listening, and no rich rule for it |
| vmauth | exactly one user, `operator-read`; the six former ingest tokens get 401 |
| Inventory | no `log_shippers` group, no `victorialogs_syslog_sources`, no `vault_log_ingest_token` |
| `nms` | no `systemd-journal-remote`, no `/etc/pki/deevnet/site-ca.pem`, no SELinux label on 8427 |
| Branch `journal-upload-wip` | deleted; its tip `7230461` recorded here |
| `(0, 0)` | kept or cleared, as the operator chooses (Step 5) |

## Scope

**In scope:** the role, inventory, vault files, `nms` and the branch listed above.
**Out of scope:** tenant tokens, the API, and the MQTT bridge (ADR-0027 §4). All are later changes.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Removing the syslog listener restarts VictoriaLogs | `obs` | nothing ships to it; a restart loses nothing |
| A leftover rich rule keeps 6514 open | `obs` | the role removes every rich rule for 6514; verified from the Builder and from `hyp001` |
| A vault file deleted by mistake | inventory | only the six files CHG-0018 created, each holding only `vault_log_ingest_token`; deleted with `git rm`, so recoverable from history |

## Prerequisites

- [ ] Operator present for the vault password (ADR-0016 §2): the role reads the operator token and
  OpenBao's AppRole
- [ ] The operator's decision on `(0, 0)` (Step 5)

## Procedure

### Step 1: The role

In `roles/victorialogs`:
- Remove the `-syslog.*` flags, the syslog-sources assert and the rich-rule task.
- Add a task that removes **every** rich rule for 6514 from the zone, so the running host matches.
- Remove the ingest-user loop from `auth.yml.j2`, the ingest-token asserts, and
  `victorialogs_vmauth_ingest_group`.
- The operator user and the token-uniqueness assert, now for one token, stay.

**Verify:** `ansible-playbook --syntax-check`.
**Undo:** revert the commit.

### Step 2: The inventory

- `hosts.yml`: remove `log_shippers`.
- `group_vars/observability_store/vars.yml`: remove `victorialogs_syslog_sources`.
- `git rm` the six `host_vars/dv02{nms,col,idn,prv,obs,msg}001v01/vault.yml`. These are the files
  CHG-0018 created; each holds only `vault_log_ingest_token`.
- The operator's `group_vars/observability_store/vault.yml` stays.

**Verify:**
- no `log_shippers` or `vault_log_ingest_token` remains
- every remaining `vault.yml` starts with `$ANSIBLE_VAULT`

**Undo:** revert the commit; the files come back from history.

### Step 3: Deploy

```bash
ansible-playbook playbooks/site.yml --limit observability_store --tags log-store --ask-vault-pass
```

**Verify:** see *Verification*.
**Undo:** redeploy from the previous commit.

### Step 4: Clean up `nms`

On `dv02nms001v01`:
- `dnf remove systemd-journal-remote`
- remove `/etc/pki/deevnet/site-ca.pem`, and the directory if it is then empty
- `semanage port -d -t journal_remote_port_t -p tcp 8427`

**Verify:** none of the three remains, and `semanage port -l | grep 8427` is empty.
**Undo:** not needed; nothing uses them.

### Step 5: `(0, 0)` — the operator's choice

`(0, 0)` holds `nms`'s trial (about 370,000 lines) and CHG-0018's verification markers. Nothing
depends on them.
- **Keep:** they age out under the 30-day retention.
- **Clear:** stop VictoriaLogs, remove `/srv/victorialogs/data/*`, and start it. VictoriaLogs has no
  deletion unless it is started with `-delete.enable`. Its docs call that off-by-default *"good from
  security PoV - an attacker cannot remove the existing logs"*, so it is not turned on for this.
  Wiping the directory is safe only because no tenant data exists yet.

**Undo:** none if cleared. That's why it's the operator's choice.

### Step 6: The branch

Delete `journal-upload-wip` from the mgmt collection's origin. Its tip, `7230461`, is recorded here.
The three fixes its trial found are also in CHG-0018's departures, so nothing is lost with the branch.

## Verification

1. From the Builder **and** from `dv02hyp001p01`, a formerly allowed source: 6514 on `obs` does not
   answer.
2. `firewall-cmd --list-rich-rules` on `obs` has no rule for 6514.
3. `auth.yml` on `obs` has one user. `nms`'s former ingest token gets **401**, which shows the users
   were really removed and not just unused.
4. No token gets 401, and the operator's token reads `(0, 0)`.

## Undo

Steps back out in reverse order. Only Step 5's clearing cannot be undone.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 2026-09-22 ~12:40 | 1, 2 | Role and inventory changes made and pushed: mgmt [#40](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/40), inventory [#49](https://github.com/deevnet/ansible-inventory-deevnet/pull/49). |
| 2026-09-22 ~12:50 | 3 | Deployed with `--tags log-store`: 8 changes. vmauth's users rewritten, VictoriaLogs recreated without the `-syslog.*` flags, **five rich rules removed**, vmauth restarted. **Before:** 7 users, 5 rich rules, 6514 listening. **After:** 1 user, 0 rich rules, nothing on 6514. |
| 2026-09-22 ~12:55 | 3 | Verification passed; see below. |
| 2026-09-22 ~12:58 | 4 | `nms` cleaned: `systemd-journal-remote` removed, `/etc/pki/deevnet/` removed, the SELinux label on 8427 removed. The unit was already stopped and disabled, and its drop-in removed, when CHG-0018 was rescoped. |
| 2026-09-22 ~13:00 | 5 | **`(0, 0)` cleared**, on the operator's decision: VictoriaLogs stopped, `/srv/victorialogs/data` emptied (32 MB), started. It reads 0 lines. The store now holds nothing. |
| 2026-09-22 | 6 | **Not done, deliberately.** See Departures. |

### Verification results

| | Result |
|---|---|
| 6514 from the Builder, and from `dv02hyp001p01` (formerly allowed) | no answer from either |
| Rich rules for 6514 | none; the zone has no rich rules at all, and exposes only 8427 plus ssh |
| vmauth users | 1 (`operator-read`) |
| A **former** ingest token on `/insert/` | **401** — the users were really removed, not just unused |
| No token on `/select/` | 401 |
| The operator's token | reads; 0 lines after the wipe |
| Listeners on `obs` | `0.0.0.0:8427`, `127.0.0.1:9428`, `127.0.0.1:8426` |

### Departures from the plan

- **The branch `journal-upload-wip` was kept**, against Step 6. The operator chose to keep it: tenant
  workloads may want journal-upload, and the branch carries working code for the three fixes. Its tip
  is `7230461`.
- **The vault was decrypted during the change**, so no `--ask-vault-pass` was needed. The six token
  files were deleted with `git rm -f` because their working copies were plaintext. Nothing was lost:
  the encrypted versions are in history, and the tokens were being retired.
- **`(0, 0)` was cleared rather than left to age out.** It held only CHG-0018's trial. The wipe was a
  directory removal, not a delete API: VictoriaLogs keeps deletion off unless started with
  `-delete.enable`, which its own docs call *"good from security PoV"*, and it stays off here.
- **`/select/tenant_ids` cannot be used through vmauth.** VictoriaLogs requires that endpoint to be
  called with an empty `AccountID` header, and vmauth always sets one. Reaching it means querying
  VictoriaLogs on `obs`'s loopback. Worth knowing when the tenant-token change builds the operator's
  view.

## Follow-ups

- [x] **Branch `journal-upload-wip`** kept by the operator's decision, not deleted.
- [ ] **Tenant tokens and the API**: the store's first real writer.
- [ ] **The MQTT bridge** (ADR-0027 §4), after ADR-0027 is accepted.
