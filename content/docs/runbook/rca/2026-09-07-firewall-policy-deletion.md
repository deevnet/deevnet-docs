---
title: "2026-09-07 — Firewall policy deleted, total connectivity loss"
---

# 2026-09-07 — Firewall policy deleted, total connectivity loss

**Site:** mobile (`dvntm`) · **Device:** `dv02cor002p01` (OPNsense core router)
**Severity:** total site outage, physical console access required to recover
**Status:** root cause confirmed · service restored from config backup · **corrective actions open**

{{< hint danger >}}
**The role that manages the firewall can delete the entire firewall policy, report success,
and sever its own control path — and this has happened once.** Nothing in
`opnsense_firewall` has changed since. Read [Corrective actions](#corrective-actions)
before running it against a live router.
{{< /hint >}}

Times are UTC (local is UTC−4), as recorded in the session transcript.

---

## Summary

Four ad-hoc runs of the `opnsense_firewall` role against the core router deleted **every**
`ansible:`-prefixed filter rule on it: 18 zone policies, the internet rules for 8 zones, the
per-zone conntrack rules, and both anti-lockout rules. That is the entire inter-VLAN policy.
The role reported success on every run.

It did this because its interface discovery had silently broken, which made the *desired*
rule set empty — and the role treats "nothing desired" as "delete everything managed",
with no guard.

## Impact

- All inter-VLAN routing denied by default. Nothing reached anything across a segment boundary.
- Internet access lost for all 8 zones carrying an internet policy.
- Loss of `trusted -> management`, the operator path to `dv00bld001p01` (10.20.99.95).
- Loss of both anti-lockout rules — management subnet to the router on 443 and 22 — so the
  OPNsense web UI was unreachable and the fault could not be repaired over the network.
- The automation host sits **behind** the policy it was editing, so the role severed its own
  return path mid-sequence. There was no in-band recovery.

**Recovery:** mini DisplayPort cable → OPNsense physical console → restore config backup.

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

## Root cause

Three faults compose. Any one alone is survivable.

**1. Discovery failed silently.**
`roles/opnsense_firewall/tasks/discover_interfaces.yml` reads `/interfaces/overview/export`.
That endpoint returns JSON but labels it `text/html; charset=UTF-8`, so `uri` never populated
`.json`; and it returns a *list* of interface objects, which was being read as a dict keyed by
identifier. Every zone resolved to `unmapped`:

```
skipping: [dv02cor002p01] => (item=trusted -> unmapped)
skipping: [dv02cor002p01] => (item=management -> unmapped)
... 11 zones, all unmapped
```

**2. An empty desired set was treated as authoritative.**
With no device map, every rule was filtered out by its own `when`, so `desired_rules` came out
empty. The role does not distinguish *"inventory declares no rules"* from *"discovery failed,
so I computed no rules."*

**3. The reconcile deletes by subtraction, with no floor and no protected set.**
`configure_rules.yml:202` builds `rules_to_delete` as every existing managed rule not present
in the desired list. Empty desired means delete all. The `Delete orphaned firewall rules` task
is ungated, and the `apply firewall rules` handler commits it. The anti-lockout rules built at
`configure_rules.yml:80-98` carry the same `ansible:` prefix, so they went with everything else.

{{< hint info >}}
**Evidence that the deletes ran.** The recaps settle it arithmetically. The role is 28 tasks
pre-fix. The `changed=0` run: `ok=16 skipped=12` = 28, no handler. The `changed=1` runs:
`ok=18 skipped=11` = 29 — one extra task executed *plus* the handler. `Add` and `Update` cannot
run when the desired set is empty, which leaves `Delete orphaned firewall rules` as the only
candidate.
{{< /hint >}}

## Contributing factors

- **`--check` does not protect these roles.** `ansible.builtin.uri` declares
  `check_mode: support: none`, so Ansible *skips* those tasks in check mode rather than
  previewing them. The `--check --diff` dry run required by
  [Change Management](/docs/runbook/change-management/) would have reported zero deletions,
  and then the real run deleted everything. The checklist step is not merely weak here — it is
  actively misleading.
- **`opnsense_firewall` is the outlier in its own collection.** `opnsense_dns` and
  `opnsense_dhcp` both already gate this exact operation behind an opt-in
  `*_delete_unmanaged: false` flag that reports and leaves records in place
  (`opnsense_dns/tasks/configure_unbound.yml:378-417`,
  `opnsense_dhcp/tasks/configure_dhcp_reservations.yml:160-186`). The single role missing that
  guard is the one whose deletions cut the control path.
- **The role has no post-condition.** It verifies the API accepted the writes, never that the
  network still works.
- **The apply is not reversible.** The handler posts a bare `firewall/filter/apply` with no
  savepoint, so recovery depended on a human with physical access.
- **The blast radius is invisible in the output.** Nothing in a `changed=1` recap names what
  was deleted.

## Why it was not detected

- The broken run *looked* converged: `ok`, `changed=0`, `Total desired rules: 0`.
- Gateway pings still answered and were read as reassurance. A router answering on its own
  interface addresses says nothing about the transit policy between segments.
- All five IoT hosts went silent from management — the actual signal — and it was attributed
  to the hosts being powered off.
- **The conclusion recorded in git was wrong.** The discovery-fix commit states *"Nothing was
  deleted either, so the damage was limited to the policy never existing."* That was reached by
  reading the **final** `changed=0` run, after the deletions had already completed. Left
  uncorrected it reads as evidence the role is safe.

## Corrective actions

{{< hint warning >}}
**Blocking prerequisite.** Do **not** merge `fix-firewall-interface-discovery` on its own. The
discovery fix is correct, but alone it is *more* dangerous than the status quo: it makes all 18
rules build, and the still-ungated delete then reconciles hard against whatever the config
restore put back. The fix and the guards must land together.
{{< /hint >}}

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Refuse to reconcile from a degraded discovery — assert the interface list and zone map are non-empty, that every `from_zone` resolved, and that `desired_rules` is non-empty before categorising | `discover_interfaces.yml`, `configure_rules.yml` | Open |
| 2 | Make deletion opt-in via `firewall_delete_unmanaged: false`, with the "LEFT IN PLACE" report, following the `opnsense_dns` / `opnsense_dhcp` precedent | `defaults/main.yml`, `configure_rules.yml` | Open |
| 3 | Protect the lifeline rules structurally — both anti-lockout rules and `trusted -> management` excluded from `rules_to_delete` even when deletion is enabled | `defaults/main.yml`, `configure_rules.yml:202` | Open |
| 4 | Apply behind a rollback savepoint: `savepoint` → `apply/{revision}` → verify → `cancelRollback`, so the router reverts unattended if the control host loses its path | `handlers/main.yml` | Open |
| 5 | Add a reachability post-condition after apply — router 443/22 from management, control host across the LAN boundary, one host per policy-bearing segment | `opnsense_firewall` | Open |
| 6 | Correct the discovery-fix commit message before the branch is pushed | `ansible-collection-deevnet.net` | Open |
| 7 | Record in the Validation Checklist that `--check --diff` is not a dry run for the OPNsense API roles, and name the real pre-flight | [change-management.md](/docs/runbook/change-management/) | **Done** |
| 8 | Write the console-recovery procedure — DisplayPort to the OPNsense console, restore config backup | This runbook | Open |

Actions 1–3 are the ones that would have prevented this outage. Action 4 is the one that makes
surviving the change unnecessary: it does not depend on the control host staying reachable.

Action 7 is done. Investigating it turned up a second case: `switch_vlans` uses
`ansible.netcommon.cli_command`, which supports check mode but accepts only `show` commands,
so `--check` there does not skip silently — every configuration line **fails**. Neither role
family gives a usable dry run; the OPNsense one is worse only because it is quiet about it.

## Open items

- **Audit what the restore put back.** The backup is of unknown vintage, so the live rule set is
  not necessarily what `firewall.yml` declares. Once action 2 is in, a run with
  `firewall_delete_unmanaged: false` reports adds, updates and would-deletes without touching the
  router — that report is the drift inventory.
- **Conntrack rules are built but not sent correctly.** `configure_rules.yml:120-121` sets
  `quick: true` and `state: "established,related"`, but the `addRule` body (`:226-238`) never
  sends those fields. Fix before the first real apply, not after.
- **The 18-rule zone policy has still never been applied.** It remains a substantial change to
  inter-VLAN reachability: scheduled, console open, savepoint armed, drift audit read first.

## State left behind

- **Core router:** restored from config backup. No corrective action applied.
- **`ansible-collection-deevnet.net`:** branch `fix-firewall-interface-discovery`, one commit,
  unpushed — **must not merge alone**.
- **Switch `dv02acc001p01`:** `gi 1/0/15` left as a trunk (native 99, +VLAN 35). Applied
  separately and not implicated in the outage; unaffected by the router restore.
- **`dv02mqt001v01`:** created on `dv02hyp001p01`, static 10.20.35.20, no DHCP reservation
  (cloud-init addressing), so unaffected by the router restore.
