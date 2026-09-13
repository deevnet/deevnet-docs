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
| **Status** | **Planned**, after the `opnsense_firewall` fixes and the mobile reachability targets (see [Prerequisites](#prerequisites)) |
| **Window** | To be scheduled, with the operator at the rack and the router's console connected |
| **Site** | mobile |
| **Systems** | Core router `dv02cor002p01` (OPNsense); control host `dv00bld001p01` |
| **Automation** | `ansible-collection-deevnet.net` role `opnsense_firewall`, run by `playbooks/migration/07-opnsense-firewall.yml` (`make migration-opnsense-firewall`) against `ansible-inventory-deevnet/mobile` |
| **Risk** | High. The policy has never been applied as a whole, and the last unguarded run of this role took the site down. |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — the segmentation that declared this policy |
| **Related incidents** | [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) — its three open items are this change |
| **Related runbooks** | [Change Management](/docs/runbook/change-management/#validation-checklist); [Console Recovery → Core Router](/docs/runbook/recovery/console-recovery/core-router/) |

---

## Summary

`mobile/group_vars/all/firewall.yml` declares a default-deny zone policy: 18 inter-zone allows and
internet egress for 8 zones. [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/)
records that this policy *"has still never been applied"*. The router is running whatever a config
backup of unknown vintage put back.

Until the policy is in force, **no segment boundary on the site is known to be enforced.** That
includes the IoT segment
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) depends on, and the
guest and IoT Vendor containment the segmentation standard requires.

This change applies the policy for the first time, as a watched change. It happens in three phases:
- a drift audit that writes nothing
- a guarded apply with the console open
- verification taken from the network

It can't run yet. A review on 2026-09-13 found that the role has no way to audit without writing,
and that its safety net doesn't work as written. Those fixes are prerequisites.

## Goal

- The router's Automation filter rules match the declared set, as reported by the role's plan
  mode, with no unexplained extras.
- There are no per-interface "conntrack" pass rules. Each zone reaches its own gateway's DNS through
  an explicit rule instead.
- Every allowed path in [Verification](#verification) answers, and every denied path doesn't.
- The control host still reaches the router on 443 and 22, and `cancelRollback` was sent only
  because the reachability check actually passed.
- INC-0001's open items are closed or re-recorded here.

## Scope

**In scope:** the `ansible:` automation filter rules on `dv02cor002p01`.

**Out of scope:**
- VLANs, interface addresses, DNS and DHCP. Their roles are not run, which is why `opnsense.yml`
  is not used.
- The home site. Its policy has the same shape, but the role's internet rule hardcodes
  `!10.20.0.0/16`.
- Any rule not prefixed `ansible:`.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The apply severs the control host's path to the router | Phase 2 | Savepoint armed: the router reverts on its own unless `cancelRollback` arrives. The role must fail, not fall back, when no savepoint is issued. Console connected. |
| The reachability check passes when a path is down, so the rollback is cancelled anyway | Phase 2 | Prerequisite fix: today `failed_when: false` makes every result `failed: false`, so the check can never trip |
| The router rejects a rule and the run reports success | Phases 1–2 | Prerequisite fix: `addRule`/`setRule` must check the API's `result`, not only HTTP 200 |
| Removing the conntrack pass rules breaks DNS to each zone's gateway, which no zone rule covers | Phase 2 | Prerequisite fix: explicit per-zone gateway-service rules. DNS checked from each zone in phase 3. |
| The live rule set differs from what the restore is assumed to hold | Phase 1 | Plan mode reports adds, updates (field by field) and would-deletes before anything is written |
| Unmanaged rules are deleted | All | `firewall_delete_unmanaged: false`, the default, confirmed in the prerequisites |
| The apply lands late in a longer play | Phase 2 | Firewall-only playbook. `opnsense.yml` has no `flush_handlers`, so there the apply runs after DNS and DHCP. |

## Prerequisites

- [ ] **`opnsense_firewall` fixed and merged** in `ansible-collection-deevnet.net`:
  - [ ] a zero-write plan mode, as the default, that names every add, update and would-delete with
    field-level differences
  - [ ] `addRule`/`setRule` fail on `result` other than `saved`, and print the validation errors
  - [ ] required fields sent as `any` rather than empty strings, after confirming the live release's
    behaviour with read-only `searchRule`/`getRule`
  - [ ] a reachability check that actually fails
  - [ ] failure, not a plain apply, when savepoint is requested and no revision comes back;
    `firewall_savepoint_timeout` implemented or removed
  - [ ] per-interface conntrack pass rules replaced by per-zone gateway-service rules
- [ ] **Mobile `firewall_reachability_targets`** in `ansible-inventory-deevnet`, beyond the router's
  own 443 and 22.
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
3. Settle INC-0001's first two open items from that report: what the restore put back, and what the
   conntrack rules actually were on the router.
4. **Stop if the report contains anything unexplained.** The apply is a separate decision.

**Undo:** None needed. Phase 1 writes nothing.

### Phase 2: Watched apply · *disruptive*

With the console connected and the phase 1 report read, apply the declared set behind the savepoint.

**Run:**

```bash
make migration-opnsense-firewall     # with the role's apply switch on, as named by the fix
```

**Verify:**

1. The run shows a savepoint revision issued, the apply to that revision, every reachability target
   answering, and `cancelRollback` sent.
2. From the control host: `curl -sk -o /dev/null -w '%{http_code}\n' https://10.20.99.1/` returns an
   HTTP code, and SSH to `10.20.99.1` answers.

**Undo:** [Undo phase 2](#undo-phase-2)

### Phase 3: Verification from the network

See [Verification](#verification). Take results from clients on each segment, not from Ansible.

---

## Verification

**Allowed paths should answer. Denied paths should time out, not be refused by the target.**

| From | To | Expect | Rule |
|---|---|---|---|
| Control host (management) | Router `10.20.99.1` 443, 22 | Answers | anti-lockout |
| Control host (management) | Pi `10.20.30.11` 22 (iot) | Answers | `management -> iot` |
| Control host (management) | Broker `10.20.35.20` 1883 (iot_backend) | Answers | `management -> iot_backend` |
| `DVNTM` client (trusted) | `dv00bld001p01` `10.20.99.95` 22 | Answers | `trusted -> management` |
| `DVNTM` client (trusted) | `10.20.31.x` host (iot_vendor), if one exists | Denied | not declared |
| `DVNTM-GUEST` client | `10.20.99.95` 22 (management) | **Denied** | not declared |
| `DVNTM-GUEST` client | `10.20.30.11` 22 (iot) | **Denied** | not declared |
| `DVNTM-GUEST` client | `1.1.1.1` | Answers | internet egress |
| `DVNTM-IOTV` client | `10.20.99.95` 22, `10.20.30.11` 22 | **Denied** | not declared |
| `DVNTM-IOTV` client | `1.1.1.1` | Answers | internet egress |
| Pi `10.20.30.11` (iot) | `10.20.99.95` 22 (management) | **Denied** | prohibited by the standard |
| Pi `10.20.30.11` (iot) | Broker `10.20.35.20` 1883 | Answers | `iot -> iot_backend` |
| A client in each zone | Its own gateway, DNS 53 | Resolves `dv00bld001p01.mobile.deevnet.net` | gateway-service rule |

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

There is no point of no return. The downloaded backup restores the pre-change rule set at any time.

---

## Outcome

Not yet run.

## Follow-ups

- [ ] Update INC-0001's open items and status, and its row in the incidents index.
- [ ] Derive the internet rule's destination from the site, so the same role can apply the home
  policy.
- [ ] Decide which reachability targets stay permanent in inventory, and which were only for this
  change.
