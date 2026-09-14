---
title: "CHG-0007: Core Router Zone Policy, First Application"
weight: 7
---

# CHG-0007: Core Router Zone Policy, First Application

| | |
|---|---|
| **Date** | Not yet scheduled |
| **Change type** | Configuration |
| **Classification** | Disruptive — it changes what every segment on site can reach, the operator's own path included |
| **Status** | **Planned**, after the `opnsense_firewall` fixes and the mobile reachability targets (see [Prerequisites](#prerequisites)). Pre-change state read on 2026-09-14 (see [Pre-change state](#pre-change-state-read-2026-09-14)). |
| **Window** | To be scheduled, with the operator at the rack and the router's console connected |
| **Site** | mobile |
| **Systems** | Core router `dv02cor002p01` (OPNsense 26.7.3); control host `dv00bld001p01` |
| **Automation** | `ansible-collection-deevnet.net` role `opnsense_firewall`, run by `playbooks/migration/07-opnsense-firewall.yml` (`make migration-opnsense-firewall`) against `ansible-inventory-deevnet/mobile` |
| **Risk** | High. The policy has never been applied as a whole, and the last unguarded run of this role took the site down. |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — the segmentation that declared this policy |
| **Related incidents** | [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) — its open items are this change |
| **Related decisions** | [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) — attachment by trust class depends on this policy; its [Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14) is where the pre-change state was first read |
| **Related runbooks** | [Change Management](/docs/runbook/change-management/#validation-checklist); [Console Recovery → Core Router](/docs/runbook/recovery/console-recovery/core-router/) |

---

## Summary

`mobile/group_vars/all/firewall.yml` declares a default-deny zone policy: 18 inter-zone allows and
internet egress for 8 zones. [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/)
records that this policy *"has still never been applied"*. The router is running whatever a config
backup of unknown vintage put back.

**As read on 2026-09-14, that is allow-all.** Every VLAN interface passes any to any, through rules
the automation created and two it didn't
([Pre-change state](#pre-change-state-read-2026-09-14)). No segment boundary on the site is
enforced. That includes:
- the IoT segment [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)
  depends on
- the guest and IoT Vendor containment the segmentation standard requires

This change applies the policy for the first time, as a watched change. It happens in three phases:
- a drift audit that writes nothing
- a guarded apply with the console open
- verification taken from the network

It can't run yet. A review on 2026-09-13 found that the role has no way to audit without writing,
and that its safety net doesn't work as written. Those fixes are prerequisites.

## Pre-change state (read 2026-09-14)

This is from read-only automation API calls made from `dv00bld001p01`, with no writes. Phase 1
repeats the read to confirm nothing has changed since.

**Automation filter rules (25), none of them the declared policy:**

| Rules | Interfaces | What they do |
|---|---|---|
| `ansible:temp-allow-all-opt1` … `-opt10` | Every assigned VLAN interface: Trusted, storage, platform, iot, iot_vendor, iot_backend, guest, management, blackhole, tenant_transit | Pass `any` → `any`, `inet`, quick, keep state. **Each exists twice.** |
| `ansible:temp-allow-all-opt11`, `-opt12` | `opt11`, `opt12`, which are no longer assigned | The same, twice each. Stale. |
| `ansible:test-rule` | management | A leftover test rule |

**Rules outside the automation API (2).** These appear in the router's full rule listing, but not
as automation rules, so `opnsense_firewall` can't see, change or delete them:

| Rule | Interface | What it does |
|---|---|---|
| *"temp: allow all VLAN 99"* | management | Pass `any` → `any` |
| (no description) | Trusted | Pass `any` → `10.20.99.0` |

**What the router generates on its own.** These are the stock automatic rules: default deny, the
anti-lockout on the untagged LAN, and bogon and private blocks on WAN. **None allows a VLAN client
to reach its gateway's DHCP server.** The only automatic DHCP rules are the client rules on WAN.
*Observed on the rule listing; not from vendor documentation.*

**Field behaviour, for the role fix.** On a blank rule template, the router defaults `protocol`,
`source_net` and `destination_net` to `any`, and `ipprotocol` to `inet`. Existing rules read back
as `any`, not as empty strings.

## Goal

- The router's Automation filter rules match the declared set, as reported by the role's plan
  mode, with no unexplained extras. **The allow-all, stale and test rules above are gone.**
- The two allow rules outside automation are gone.
- There are no per-interface "conntrack" pass rules. Each zone reaches its own gateway's **DNS and
  DHCP** through explicit rules instead.
- Every allowed path in [Verification](#verification) answers, and every denied path doesn't.
- The control host still reaches the router on 443 and 22, and `cancelRollback` was sent only
  because the reachability check actually passed.
- INC-0001's open items are closed or re-recorded here.

## Scope

**In scope:**
- the `ansible:` automation filter rules on `dv02cor002p01`, **including removing the 25 undeclared
  ones listed under [Pre-change state](#pre-change-state-read-2026-09-14)**
- **removing, by hand, the two allow rules outside automation**, as the last step of phase 2

**Out of scope:**
- VLANs, interface addresses, DNS and DHCP. Their roles are not run, which is why `opnsense.yml`
  is not used.
- The home site. Its policy has the same shape, but the role's internet rule hardcodes
  `!10.20.0.0/16`.
- Any other rule not prefixed `ansible:`.

## Decision needed before phase 2: removing the allow-all rules

The declared policy only takes effect once the allow-all rules are gone. Applied alongside them, it
changes nothing: they pass everything first.

The role won't remove them as planned. They carry the managed `ansible:` prefix but aren't declared,
so with `firewall_delete_unmanaged: false`, a prerequisite of this change, they are reported and
**left in place**.

| Option | How | Trade-off |
|---|---|---|
| **A — Delete through the role, for this run only** | Run phase 2 with `-e firewall_delete_unmanaged=true`, **only after** phase 1's would-delete list is exactly the 25 rules above and the protected set is intact | The deletes land in the same apply as the adds, **behind the savepoint**, so a severed path reverts them too. Deletion stays off by default for every later run. |
| **B — Delete by hand after the apply** | Apply the policy with deletion off, verify, then delete the 25 rules in Firewall → Automation → Filter and apply again | The first apply changes nothing observable, so phase 3 can't tell a working policy from an inert one until the second apply. The hand apply has no savepoint. |

**Recommended: A.** Its only risk is deleting something unintended, and phase 1's list rules that
out before anything is written. The two rules outside automation are removed by hand under either
option, last, with the console open, because the role can't reach them.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The apply severs the control host's path to the router | Phase 2 | Savepoint armed: the router reverts on its own unless `cancelRollback` arrives. The role must fail, not fall back, when no savepoint is issued. Console connected. |
| The reachability check passes when a path is down, so the rollback is cancelled anyway | Phase 2 | Prerequisite fix: today `failed_when: false` makes every result `failed: false`, so the check can never trip |
| The router rejects a rule and the run reports success | Phases 1–2 | Prerequisite fix: `addRule`/`setRule` must check the API's `result`, not only HTTP 200 |
| Removing the conntrack pass rules breaks DNS to each zone's gateway, which no zone rule covers | Phase 2 | Prerequisite fix: explicit per-zone gateway-service rules. DNS checked from each zone in phase 3. |
| **DHCP clients lose their leases once allow-all goes: nothing lets a VLAN client reach the gateway's DHCP server** | Phase 2 | Gateway-service rules cover DHCP as well as DNS (prerequisite). A lease is checked from each DHCP zone in phase 3. |
| **The policy is applied but the allow-all rules stay, so nothing is enforced and phase 3's allow tests all pass** | Phase 2 | [Decision above](#decision-needed-before-phase-2-removing-the-allow-all-rules). Phase 3's **deny** rows are what prove enforcement. |
| **A reachability target is down for reasons unrelated to the policy, and the rollback reverts a correct apply** | Phase 2 | Every target must answer *before* phase 2. On 2026-09-14 the broker `10.20.35.20` didn't answer at all, so it is not a target until it does. |
| **Removing "temp: allow all VLAN 99" takes away a management path the declared rules don't replace** | Phase 2, last step | Removed last, after the automation apply is verified, with the console open. Router 443/22 and the management → zone paths re-checked afterwards. |
| **A tenant workload reaches a tenant-facing service on management directly and is cut off.** Tenant DNS `10.20.99.30` and the state store `10.20.99.31` sit on management, and no `tenant_transit -> management` rule is declared. | Phase 2 | Phase 1 records whether any tenant workload is live and talks to either directly. Tenant Terraform runs from management and isn't affected. |
| The live rule set differs from what the restore is assumed to hold | Phase 1 | Plan mode reports adds, updates (field by field) and would-deletes before anything is written, and is compared with [Pre-change state](#pre-change-state-read-2026-09-14) |
| Unmanaged rules are deleted | All | `firewall_delete_unmanaged: false`, the default, confirmed in the prerequisites. Enabled for phase 2 only under Option A, after phase 1's list is checked. |
| The apply lands late in a longer play | Phase 2 | Firewall-only playbook. `opnsense.yml` has no `flush_handlers`, so there the apply runs after DNS and DHCP. |

## Prerequisites

- [ ] **`opnsense_firewall` fixed and merged** in `ansible-collection-deevnet.net`:
  - [ ] a zero-write plan mode, as the default, that names every add, update and would-delete with
    field-level differences
  - [ ] `addRule`/`setRule` fail on `result` other than `saved`, and print the validation errors
  - [ ] required fields sent as `any` rather than empty strings. *The live release's behaviour was
    confirmed read-only on 2026-09-14 ([Pre-change state](#pre-change-state-read-2026-09-14)); the
    role change itself is still to do.*
  - [ ] a reachability check that actually fails
  - [ ] failure, not a plain apply, when savepoint is requested and no revision comes back;
    `firewall_savepoint_timeout` implemented or removed
  - [ ] per-interface conntrack pass rules replaced by per-zone gateway-service rules, **covering
    DHCP as well as DNS**
- [ ] **Mobile `firewall_reachability_targets`** in `ansible-inventory-deevnet`, beyond the router's
  own 443 and 22. **Each target must answer before phase 2.** The broker didn't on 2026-09-14.
- [ ] **The allow-all removal decided** ([Decision](#decision-needed-before-phase-2-removing-the-allow-all-rules)).
- [ ] **The MQTT broker answering**, or its rows dropped from [Verification](#verification) and
  recorded under Outcome.
- [ ] **Config backup downloaded** from **System → Configuration → Backups → Download** and kept
  off the router ([Console Recovery](/docs/runbook/recovery/console-recovery/#before-you-need-any-of-this)).
- [ ] **Console kit at the rack:** mini DisplayPort cable, USB keyboard, and a monitor not on the
  affected network.
- [ ] **Vault decrypted before walking over**, including the router's root password in
  `mobile/group_vars/routers/vault.yml`.
- [ ] `firewall_delete_unmanaged` confirmed `false` in the rendered variables.
- [ ] Test clients ready: one each on `DVNTM-GUEST` and `DVNTM-IOTV`, and one on `DVNTM`.

---

## Procedure

### Phase 1: Drift audit · *no writes*

Run the role in its plan mode against the router. **Nothing is written.** The run reads the live
rule table and reports.

**Run:**

```bash
cd ansible-collection-deevnet.net
make migration-opnsense-firewall     # plan mode is the role's default once the fix merges
```

The variable that switches plan mode off is named by the role fix. Record it here when that merges.

**Verify:**

1. The run made no `addRule`, `setRule` or `apply` call, and the router's rule table is unchanged.
2. Record under [Outcome](#outcome):
   - every add, update (with its differing fields) and would-delete
   - any rule the router holds that inventory doesn't declare
3. **Compare with [Pre-change state](#pre-change-state-read-2026-09-14).** The would-delete list
   should be exactly the 25 `temp-allow-all` and `test-rule` entries. Confirm the two rules outside
   automation are still the only others. INC-0001's first two open items were settled from the
   2026-09-14 read; this only confirms nothing has changed since.
4. Record whether any tenant workload is live and reaches `10.20.99.30` or `10.20.99.31` directly
   (see [Risk](#risk-and-impact)).
5. **Stop if the report contains anything unexplained.** The apply is a separate decision.

**Undo:** None needed. Phase 1 writes nothing.

### Phase 2: Watched apply · *disruptive*

With the console connected and the phase 1 report read, apply the declared set behind the savepoint.

**Run:**

```bash
make migration-opnsense-firewall     # with the role's apply switch on, as named by the fix,
                                     # and deletion as decided above
```

**Verify:**

1. The run shows:
   - a savepoint revision issued
   - the apply to that revision
   - every reachability target answering
   - `cancelRollback` sent
2. From the control host: `curl -sk -o /dev/null -w '%{http_code}\n' https://10.20.99.1/` returns an
   HTTP code, and SSH to `10.20.99.1` answers.
3. **Last step: remove the two rules outside automation**, *"temp: allow all VLAN 99"* on
   management and the Trusted pass to `10.20.99.0`, at the router's UI with the console open. Then
   repeat step 2, and check management → iot from the control host.

**Undo:** [Undo phase 2](#undo-phase-2)

### Phase 3: Verification from the network

See [Verification](#verification). Take results from clients on each segment, not from Ansible.

---

## Verification

**Allowed paths should answer. Denied paths should time out, not be refused by the target.** While
any allow-all rule remains, every allow row passes whether or not the policy works. The **Denied**
rows are what prove enforcement.

| From | To | Expect | Rule |
|---|---|---|---|
| Control host (management) | Router `10.20.99.1` 443, 22 | Answers | anti-lockout |
| Control host (management) | Pi `10.20.30.11` 22 (iot) | Answers | `management -> iot` |
| Control host (management) | Broker `10.20.35.20` 1883 (iot_backend) | Answers, **if the broker is running** | `management -> iot_backend` |
| `DVNTM` client (trusted) | `dv00bld001p01` `10.20.99.95` 22 | Answers | `trusted -> management` |
| `DVNTM` client (trusted) | `10.20.31.x` host (iot_vendor), if one exists | Denied | not declared |
| `DVNTM-GUEST` client | `10.20.99.95` 22 (management) | **Denied** | not declared |
| `DVNTM-GUEST` client | `10.20.30.11` 22 (iot) | **Denied** | not declared |
| `DVNTM-GUEST` client | `1.1.1.1` | Answers | internet egress |
| `DVNTM-IOTV` client | `10.20.99.95` 22, `10.20.30.11` 22 | **Denied** | not declared |
| `DVNTM-IOTV` client | `1.1.1.1` | Answers | internet egress |
| Pi `10.20.30.11` (iot) | `10.20.99.95` 22 (management) | **Denied** | prohibited by the standard |
| Pi `10.20.30.11` (iot) | Broker `10.20.35.20` 1883 | Answers, **if the broker is running** | `iot -> iot_backend` |
| A client in each zone | Its own gateway, DNS 53 | Resolves `dv00bld001p01.mobile.deevnet.net` | gateway-service rule |
| A client in each DHCP zone (trusted, iot, iot_vendor, guest) | Its own gateway, DHCP | Renews a lease | gateway-service rule |

At the router's console, `pfctl -sr | grep -c .` gives a rule count to compare with the phase 1
report.

## Undo

### Undo phase 2

1. **If the control path is lost and a savepoint was issued:** wait. The router reverts on its own
   when the rollback window lapses. Don't re-run the role.
2. **If the path is lost and no savepoint was issued, or it didn't revert:** follow
   [Console Recovery → Core Router](/docs/runbook/recovery/console-recovery/core-router/). Restore
   the last configuration revision **before** this change, then verify with its reachability pings.
3. **If the path survived but the verification table fails:** disable the offending `ansible:` rule
   under Firewall → Automation → Filter and apply, or restore the downloaded backup. Record which,
   under Outcome.
4. **If removing the two rules outside automation cut a path:** at the console, restore the
   configuration revision taken just before that removal. The automation apply stays in place.

There is no point of no return. The downloaded backup restores the pre-change rule set at any time.

---

## Outcome

Not yet run. The pre-change state was read on 2026-09-14 and is recorded
[above](#pre-change-state-read-2026-09-14).

## Follow-ups

- [ ] Update INC-0001's remaining open items and status, and its row in the incidents index. Its
  first two open items were settled on 2026-09-14.
- [ ] Derive the internet rule's destination from the site, so the same role can apply the home
  policy.
- [ ] Decide which reachability targets stay permanent in inventory, and which were only for this
  change.
- [ ] Decide where tenant-facing services live. Tenant DNS and the state store sit on management,
  reachable from tenant workloads today only because of allow-all. The proposed ADR-0012 (IoT
  platform API, under review) places its API on the platform segment for this reason.
