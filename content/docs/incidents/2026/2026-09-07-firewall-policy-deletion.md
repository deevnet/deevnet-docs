---
title: "2026-09-07 — Firewall Policy Deleted, Total Connectivity Loss"
weight: 20260907
aliases:
  - /docs/runbook/rca/2026-09-07-firewall-policy-deletion/
---

# 2026-09-07 — Firewall Policy Deleted, Total Connectivity Loss

| | |
|---|---|
| **Site** | mobile (`dvntm`) |
| **Systems** | Core router `dv02cor002p01` (OPNsense); the `opnsense_firewall` role in `ansible-collection-deevnet.net` |
| **Severity** | Total site outage; physical console access required to recover |
| **Status** | Root cause confirmed. Service restored from config backup. Corrective and preventive actions 1–8 done as of 2026-09-08. Three open items remain. |
| **Times** | UTC (local is UTC−4), as recorded in the session transcript |

{{< hint warning >}}
**The guards are in, but have not yet met the live router.** Since 2026-09-08,
`opnsense_firewall` refuses to reconcile from a broken discovery, withholds deletions by
default, protects the operator's path, and applies behind a rollback savepoint
([Corrective actions](#corrective-actions), [Preventive actions](#preventive-actions)). They
were verified offline against this incident's own input. The zone policy has still never been
applied, so its first real application remains a watched change with the console open.
{{< /hint >}}

---

## Summary

Four ad-hoc runs of the `opnsense_firewall` role against the core router deleted **every**
`ansible:`-prefixed filter rule on it: 18 zone policies, the internet rules for 8 zones, the
per-zone conntrack rules, and both anti-lockout rules. That is the entire inter-VLAN policy.
The role reported success on every run.

It did this because its interface discovery had silently broken, which made the *desired*
rule set empty — and the role treated "nothing desired" as "delete everything managed",
with no guard.

## Impact

- All inter-VLAN routing denied by default. Nothing reached anything across a segment boundary.
- Internet access lost for all 8 zones carrying an internet policy.
- Loss of `trusted -> management`, the operator path to `dv00bld001p01` (10.20.99.95).
- Loss of both anti-lockout rules — management subnet to the router on 443 and 22 — so the
  OPNsense web UI was unreachable and the fault could not be repaired over the network.
- The automation host sits **behind** the policy it was editing, so the role severed its own
  return path mid-sequence. There was no in-band recovery.

## Detection

Nothing detected the outage while it was happening:

- The broken run *looked* converged: `ok`, `changed=0`, `Total desired rules: 0`.
- Gateway pings still answered and were read as reassurance. A router answering on its own
  interface addresses says nothing about the transit policy between segments.
- All five IoT hosts went silent from management — the actual signal — and it was attributed
  to the hosts being powered off.

The record does not say when the outage was first recognised as one.

## Timeline

| Time (UTC) | Event |
|---|---|
| 23:25:03 | `switch-vlans.yml --check --diff` — dry run reviewed |
| 23:26:24 | `switch-vlans.yml` applied: `gi 1/0/15` access-99 → trunk, native 99, +VLAN 35 |
| 23:28:04 | Port state verified; `dv02hyp001p01` still reachable |
| 23:29:17 | `opnsense.yml` (full stack) attempted — **denied by the permission classifier, never ran** |
| 23:30:44 | Ad-hoc `firewall-only.yml` written and run. `ok=18 changed=1`, apply handler fires |
| 23:31:37 | `dns.yml` — `changed=0` |
| 23:32:23 | `firewall-only.yml` re-run, annotated "expect changed=0" — returns `changed=1` |
| 23:33:50, 23:34:16 | Two further re-runs; output filtered away by the grep in use |
| 23:34:28 | `firewall-only.yml` → `ok=16 changed=0`, "Rules to add: 0 / update: 0 / delete: 0" |
| 23:35:34 | Segment gateways still answer ICMP — taken as reassurance |
| 23:36–23:37 | Parse fault root-caused; endpoint probed directly |
| 23:37:49 | Branch `fix-firewall-interface-discovery` created, discovery fix written |
| 23:38:13 | Verified: 9 zones map where 0 did; all 18 policies would build |
| 23:39:03 | **All five IoT hosts silent from management** — recorded as "host may be off" |
| 23:40–00:00 | MQTT broker VM `dv02mqt001v01` created (static 10.20.35.20) |
| 00:02–00:03 | Work committed, including the discovery fix |

The full-stack `opnsense.yml` play was blocked by a permission prompt. The damage came from
the narrower ad-hoc playbook written immediately afterwards, which invoked the same role
without that scrutiny — the guard rail was routed around, not overridden.

## Symptoms

What was observable, in the order it appeared:

- A re-run expected to report `changed=0` reported `changed=1` (23:32:23).
- Discovery skipped every zone as `unmapped`:
  ```
  skipping: [dv02cor002p01] => (item=trusted -> unmapped)
  skipping: [dv02cor002p01] => (item=management -> unmapped)
  ... 11 zones, all unmapped
  ```
- The final run reported `changed=0` and "Rules to add: 0 / update: 0 / delete: 0" — with
  `Total desired rules: 0`.
- Segment gateways kept answering ICMP.
- All five IoT hosts went silent from management (23:39:03).
- From the management segment, the router's web UI and SSH stopped answering, and no zone
  reached the internet.

## Investigation

The parse fault in discovery was found within minutes (23:36–23:37) by probing the interface
export endpoint directly. A fix was written on a branch and verified to map 9 zones where 0 had
mapped, so that all 18 policies would build (23:38:13).

**The first conclusion was wrong.** The discovery-fix commit stated *"Nothing was deleted
either, so the damage was limited to the policy never existing."* That was reached by reading
the **final** `changed=0` run, after the deletions had already completed. Left uncorrected, it
reads as evidence the role is safe.

It was overturned by reading the recaps arithmetically — see the evidence under
[Root cause](#root-cause). The corrected commit message now calls that error *"the most
consequential error in the whole episode."*

## Root cause

Three faults compose. Any one alone is survivable.

**1. Discovery failed silently.**
`roles/opnsense_firewall/tasks/discover_interfaces.yml` reads `/interfaces/overview/export`.
That endpoint returns JSON but labels it `text/html; charset=UTF-8`, so `uri` never populated
`.json`; and it returns a *list* of interface objects, which was being read as a dict keyed by
identifier. Every zone resolved to `unmapped`.

**2. An empty desired set was treated as authoritative.**
With no device map, every rule was filtered out by its own `when`, so `desired_rules` came out
empty. The role did not distinguish *"inventory declares no rules"* from *"discovery failed,
so I computed no rules."*

**3. The reconcile deleted by subtraction, with no floor and no protected set.**
`configure_rules.yml:202` built `rules_to_delete` as every existing managed rule not present
in the desired list. Empty desired means delete all. The `Delete orphaned firewall rules` task
was ungated, and the `apply firewall rules` handler committed it. The anti-lockout rules built at
`configure_rules.yml:80-98` carried the same `ansible:` prefix, so they went with everything else.

{{< hint info >}}
**Evidence that the deletes ran.** The recaps settle it arithmetically. The role is 28 tasks
pre-fix. The `changed=0` run: `ok=16 skipped=12` = 28, no handler. The `changed=1` runs:
`ok=18 skipped=11` = 29 — one extra task executed *plus* the handler. `Add` and `Update` cannot
run when the desired set is empty, which leaves `Delete orphaned firewall rules` as the only
candidate.
{{< /hint >}}

## Recovery

A mini DisplayPort cable to the OPNsense physical console, then a restore from a config
backup. There was no in-band path.

State immediately after recovery, as recorded at the time:

- **Core router:** restored from config backup. No corrective action applied.
- **`ansible-collection-deevnet.net`:** branch `fix-firewall-interface-discovery`, one commit,
  unpushed, and not to be merged alone.
- **Switch `dv02acc001p01`:** `gi 1/0/15` left as a trunk (native 99, +VLAN 35). It was applied
  separately, not implicated in the outage, and unaffected by the router restore.
- **`dv02mqt001v01`:** created on `dv02hyp001p01`, static 10.20.35.20, with no DHCP reservation
  (cloud-init addressing), so unaffected by the router restore.

## Contributing factors

- **`--check` does not protect these roles.** `ansible.builtin.uri` declares
  `check_mode: support: none`, so Ansible *skips* those tasks in check mode rather than
  previewing them. The `--check --diff` dry run required by
  [Change Management](/docs/runbook/change-management/) would have reported zero deletions,
  and then the real run deleted everything. The checklist step is not merely weak here — it is
  actively misleading.
- **`opnsense_firewall` was the outlier in its own collection.** `opnsense_dns` and
  `opnsense_dhcp` both already gated this exact operation behind an opt-in
  `*_delete_unmanaged: false` flag that reports and leaves records in place
  (`opnsense_dns/tasks/configure_unbound.yml:378-417`,
  `opnsense_dhcp/tasks/configure_dhcp_reservations.yml:160-186`). The single role missing that
  guard was the one whose deletions cut the control path.
- **The role had no post-condition.** It verified the API accepted the writes, never that the
  network still worked.
- **The apply was not reversible.** The handler posted a bare `firewall/filter/apply` with no
  savepoint, so recovery depended on a human with physical access.
- **The blast radius was invisible in the output.** Nothing in a `changed=1` recap named what
  was deleted.

## Corrective actions

Actions that fix the faults behind this outage. Actions 1–3 are the ones that would have
prevented it.

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Refuse to reconcile from a degraded discovery — assert the interface list and zone map are non-empty, that every `from_zone` resolved, and that `desired_rules` is non-empty before categorising | `discover_interfaces.yml`, `configure_rules.yml` | **Done** — `1bdba4a` |
| 2 | Make deletion opt-in via `firewall_delete_unmanaged: false`, with the "LEFT IN PLACE" report, following the `opnsense_dns` / `opnsense_dhcp` precedent | `defaults/main.yml`, `configure_rules.yml` | **Done** — `1bdba4a` |
| 3 | Protect the lifeline rules structurally — both anti-lockout rules and `trusted -> management` excluded from `rules_to_delete` even when deletion is enabled | `firewall_protected_descriptions`; mobile adds `trusted -> management` in `group_vars/all/firewall.yml` | **Done** — `1bdba4a` |
| 6 | Correct the discovery-fix commit message before the branch is pushed | `ansible-collection-deevnet.net` | **Done** — `b6dd249` carries the correction |

The discovery fix was held back until the guards were ready. On its own it was *more*
dangerous than the status quo: it made all 18 rules build, and the still-ungated delete would
then have reconciled hard against whatever the config restore put back. The fix and the guards
merged together in `ansible-collection-deevnet.net` PR #16 on 2026-09-08.

### Open items

As recorded at the time, updated only where a later commit settles them:

- **Audit what the restore put back.** The backup was of unknown vintage, so the live rule set
  is not necessarily what `firewall.yml` declares. With deletion now withheld by default, a run
  reports adds, updates and would-deletes without removing anything — that report is the drift
  inventory.
- **Conntrack rules.** `quick` and `state` were built but never sent by `addRule`. `1bdba4a`
  removed them from the rule definition; that changes nothing on the wire. Whether the
  conntrack rules are needed at all is to be settled before the policy is first applied, since
  pf creates state on a passing rule by default.
- **The 18-rule zone policy has still never been applied.** It remains a substantial change to
  inter-VLAN reachability: scheduled, with the console open, the savepoint armed, and the drift
  audit read first.

## Preventive actions

Actions that stop this class of failure recurring, or make surviving it unnecessary.

| # | Action | Where | Status |
|---|--------|-------|--------|
| 4 | Apply behind a rollback savepoint: `savepoint` → `apply/{revision}` → verify → `cancelRollback`, so the router reverts unattended if the control host loses its path | `tasks/apply_rules.yml` | **Done** — `1bdba4a` |
| 5 | Add a reachability post-condition after apply — router 443/22 from management by default; sites add a host per policy-bearing segment | `firewall_verify_reachability`, `firewall_reachability_targets` | **Done** — `1bdba4a` |
| 7 | Record in the Validation Checklist that `--check --diff` is not a dry run for the OPNsense API roles, and name the real pre-flight | [Change Management](/docs/runbook/change-management/) | **Done** |
| 8 | Write the console-recovery procedure — DisplayPort to the OPNsense console, restore config backup | [Console Recovery](/docs/runbook/console-recovery/) | **Done** |

Action 4 is the one that makes surviving the change unnecessary: it does not depend on the
control host staying reachable.

Investigating action 7 turned up a second case: `switch_vlans` uses
`ansible.netcommon.cli_command`, which supports check mode but accepts only `show` commands,
so `--check` there does not skip silently — every configuration line **fails**. Neither role
family gives a usable dry run; the OPNsense one is worse only because it is quiet about it.

## Lessons learned

- **A check mode that skips is not a dry run.** On the `uri`-based roles, a clean `--check`
  means "nothing was examined", not "nothing will change".
- **An empty desired set is a failure signal, not a converged state.** "I computed nothing"
  must never be allowed to mean "delete everything I manage".
- **A gateway answering ICMP proves nothing about policy.** The router replies on its own
  addresses whether or not any transit rule survives.
- **Read the recap arithmetic, not the headline.** `changed=1` in a run where adds and
  updates were impossible could only have been a delete.
- **A guard rail that can be routed around will be.** The blocked full-stack play was
  replaced by a narrower ad-hoc one that invoked the same role without the same scrutiny.
- **Record the wrong conclusion.** The mistaken "nothing was deleted", committed to git, was
  the most consequential error of the incident. It survives here so it is not repeated.

## Related changes

- **The firewall run itself** was ad hoc and had no change record.
- **Same session, not implicated:** switch `gi 1/0/15` moved from access VLAN 99 to a trunk
  (native 99, +VLAN 35); MQTT broker VM `dv02mqt001v01` created.
- **Fix:** `ansible-collection-deevnet.net` PR #16 (2026-09-08) — the discovery fix and the
  guards together.
- **Follow-on:** `ansible-inventory-deevnet` PR #19 — protect the operator path from firewall
  reconciliation.

## Related runbooks

- [Change Management](/docs/runbook/change-management/) — the validation checklist, and why
  `--check --diff` is not a dry run for the network roles
- [Console Recovery → Core Router](/docs/runbook/console-recovery/core-router/) — the
  procedure written because of this incident
