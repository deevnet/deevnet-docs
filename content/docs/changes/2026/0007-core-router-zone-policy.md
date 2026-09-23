---
title: "CHG-0007: Core Router Zone Policy, First Application"
weight: 7
---

# CHG-0007: Core Router Zone Policy, First Application

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Disruptive — it changes what every segment on site can reach, the operator's own path included |
| **Status** | **Complete, 2026-09-19.** All three phases ran. The declared policy is live and enforcement is demonstrated from real clients on three segments, with the drops read from the router's own firewall log. Four items are recorded as untested rather than passed — see [Phase 3](#phase-3--from-clients-2026-09-19). One regression was found and fixed during verification. See [Outcome](#outcome). Pre-change state read on 2026-09-14 (see [Pre-change state](#pre-change-state-read-2026-09-14)). Allow-all removal decided on 2026-09-14: Option A (see [Decision](#decision-removing-the-allow-all-rules)). |
| **Window** | Phase 1: 2026-09-19, no writes. Phase 2: to be scheduled, with the operator at the rack and the router's console connected |
| **Site** | mobile |
| **Systems** | Core router `dv02cor002p01` (OPNsense 26.7.3); control host `dv00bld001p01` |
| **Automation** | `ansible-collection-deevnet.net` role `opnsense_firewall`, run by `playbooks/migration/07-opnsense-firewall.yml` (`make migration-opnsense-firewall`) against `ansible-inventory-deevnet/mobile` |
| **Risk** | High. The policy has never been applied as a whole, and the last unguarded run of this role took the site down. **The savepoint that was to guard phase 2 does not exist** — see [The guard that was not there](#the-guard-that-was-not-there-2026-09-19). |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — the segmentation that declared this policy |
| **Related incidents** | [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) — its open items are this change |
| **Related decisions** | [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) — attachment by trust class depends on this policy; its [Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14) is where the pre-change state was first read |
| **Related runbooks** | [Change Management](/docs/policies/change-management/#validation-checklist); [Console Recovery → Core Router](/docs/runbook/substrate/recovery/console-recovery/core-router/) |

---

## Summary

{{< hint danger >}}
**Demonstrated from a client, 2026-09-18.** During
[CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) phase 5, a device on the IoT segment
(`10.20.30.100`) reached **the Builder on the management segment**. The policy declared in inventory
permits `iot -> iot_backend` and nothing else — no `iot -> management`, no `iot -> tenant_transit`.

This was previously established by a read-only audit ([INC-0001](/docs/policies/incident-management/)).
It has now been shown from a real client, which is stronger evidence. The IoT segment is not a
containment boundary in any sense the network enforces, and tenant Wi-Fi keys — which now work — put
devices onto that segment.
{{< /hint >}}


`mobile/group_vars/all/firewall.yml` declares a default-deny zone policy: **23 entries — 22
inter-zone allows and one intra-zone rule** — plus internet egress for 8 zones. It was 18 when this
record was opened; PRs #37, #40 and #42 added the Deevnet API's paths to the tenant hypervisor and
the wireless controller, the ADR-0018 operator route to `10.20.128.0/18`, and the
`platform -> platform` rule that lets the API reach the core router's own API.
[INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/)
recorded that this policy *"has still never been applied"*, and the router was running whatever a
config backup of unknown vintage put back.

{{< hint info >}}
**The rest of this section describes the situation before the change.** It ran on 2026-09-19 and
the policy is live — 56 managed rules, no allow-all, enforcement observed from real clients. See
[Outcome](#outcome). The past tense below is deliberate; it is what this record was opened to fix.
{{< /hint >}}

**As read on 2026-09-14, that was allow-all.** Every VLAN interface passes any to any, through rules
the automation created and two it didn't
([Pre-change state](#pre-change-state-read-2026-09-14)). No segment boundary on the site was
enforced. That included:
- the IoT segment [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)
  depends on
- the guest and IoT Vendor containment the segmentation standard requires

This change applied the policy for the first time, as a watched change, in three phases:
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

### The 25 rules are 13 descriptions

*Added 2026-09-19, and it matters for Option A.* The 25 rows are **12 descriptions present twice
each, plus one `ansible:test-rule`** — 13 distinct descriptions in all. Re-read from the router on
2026-09-19 and unchanged since 2026-09-14.

`opnsense_firewall` indexed the live rules in a dict keyed on description, so it could only ever
see 13 of the 25 rows. A reconcile built from that index would have deleted 13 rules and left 12
allow-all rules in place — every segment still open, and phase 3's deny rows failing for a reason
nobody would have looked for. Option A's gate, *"the would-delete list must be exactly the 25"*,
was not meetable as the role stood. Fixed before phase 1 ran; the role now keys deletions on
`uuid`, and treats a duplicate copy of a declared rule as a deletion candidate too.

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
- There are no per-interface "conntrack" pass rules. Each zone reaches its own gateway's **DNS,
  NTP and DHCP** through explicit rules instead. *NTP was added on 2026-09-19 after phase 3 found
  it was the one thing the apply broke — see [Phase 3](#phase-3--from-clients-2026-09-19-in-progress).*
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
- **Traffic between two devices on the same VLAN.** *Added 2026-09-19.* See below — this one is
  worth stating rather than leaving to inference.

### What this change cannot enforce

This change makes **inter-zone** policy real. It has no effect whatever on traffic between two hosts
on the *same* segment: those frames are switched at Layer 2 and never reach `dv02cor002p01`, so no
rule here can see them, let alone drop them.

That matters most on the IoT segment, where devices of different owners share VLAN 30. After this
change, `iot -> management` is denied and
[CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) phase 5's demonstrated path is closed —
but two tenants' devices can still reach each other exactly as they do today. CHG-0013 recorded the
same thing when it deferred client isolation: *"Two tenants' devices can talk to each other at
Layer 3 today."*

Intra-segment separation is a different mechanism with a different owner — AP client isolation and
switch port isolation, tracked as
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) open question 4, which
is still unproven. The control that does hold between owners is credentials, not the network:
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §5 requires
every device-facing service to authenticate its callers per device, precisely because zone policy
grants a whole zone.

**So a reader should not conclude "the IoT segment is contained once this lands."** It is contained
*from other segments*. It is not contained from itself.

## Decision: removing the allow-all rules

**Decided 2026-09-14: Option A.** This records the plan for the run. Nothing has been run.

The declared policy only takes effect once the allow-all rules are gone. Applied alongside them, it
changes nothing: they pass everything first.

The role won't remove them as planned. They carry the managed `ansible:` prefix but aren't declared,
so with `firewall_delete_unmanaged: false`, a prerequisite of this change, they are reported and
**left in place**.

| Option | How | Trade-off |
|---|---|---|
| **A — Delete through the role, for this run only** *(chosen)* | Run phase 2 with `-e firewall_delete_unmanaged=true`, **only after** phase 1's would-delete list is exactly the 25 rules above and the protected set is intact | The deletes land in the same apply as the adds, ~~behind the savepoint, so a severed path reverts them too~~ — *the savepoint did not exist ([below](#the-guard-that-was-not-there-2026-09-19)); what the single apply does give is that no window opens in which allow-all is gone and the policy is not yet there.* Deletion stays off by default for every later run. |
| **B — Delete by hand after the apply** *(not chosen)* | Apply the policy with deletion off, verify, then delete the 25 rules in Firewall → Automation → Filter and apply again | The first apply changes nothing observable, so phase 3 can't tell a working policy from an inert one until the second apply. The hand apply has no savepoint. |

**Why A.** Its only risk is deleting something unintended, and phase 1's list rules that out before
anything is written. B's first apply proves nothing, and its second apply has no savepoint.

**What Option A commits this change to:**
- **Phase 1 is the gate.** Its would-delete list must be exactly the 25 `temp-allow-all` and
  `test-rule` entries in [Pre-change state](#pre-change-state-read-2026-09-14), and must include
  none of `firewall_protected_descriptions`. If it lists anything else, phase 2 does not run with
  deletion on. Stop and record it under Outcome.
- **Deletion is enabled only on the phase 2 command line**, as `-e firewall_delete_unmanaged=true`.
  It is never set in inventory, so every later run of the role is back to reporting and leaving
  undeclared rules in place.
- **Phase 2's output is checked against phase 1's list.** The rules the run deleted must be the same
  25.
- **The two rules outside automation are still removed by hand**, as phase 2's last step, with the
  console open, because the role can't reach them.

## The guard that was not there (2026-09-19)

Phase 1's preparation read the router's field behaviour rather than assuming it, and found that
**this change's principal safety mechanism does not exist.**

`opnsense_firewall` requested a rollback savepoint, applied to that revision, and sent
`cancelRollback` once the control path was proven. Every risk row below used to lean on it. None of
those three endpoints is real on OPNsense 26.7.3_11:

| Check | Result |
|---|---|
| `GET /api/firewall/filter/savepoint`, `/cancelRollback`, `/revert` on `dv02cor002p01` | `404 {"errorMessage":"Endpoint not found"}` for each. A POST-only endpoint that *does* exist, `addRule`, answers a GET with `200 {"result":"failed"}`, and an invented path answers the same 404 — so this is route-absent, not method-not-allowed |
| Upstream `FilterController.php` | No `savepoint`, `cancelRollback` or `revert` action. `FilterBaseController::applyAction()` takes no revision: `return ['status' => (new Backend())->configdRun('filter reload skip_alias')];` |
| [OPNsense core firewall API documentation](https://docs.opnsense.org/development/api/core/firewall.html) | Lists twelve `FilterController` endpoints. Neither "savepoint" nor "cancelRollback" appears on the page |

So the savepoint request returned nothing, the role fell through to a plain apply and printed a
notice, and `cancelRollback` went to an endpoint that was never there. The apply has always been
unguarded. This is not a regression — it was written against an API that does not exist, and
INC-0001 listed building the guard as a corrective action without anyone checking the endpoint.

**What replaces it.** The router's own configuration history, `/conf/backup`, is real and reachable:
`core/backup/backups/this` lists 100 revisions each with an `id` like `config-1789702628.4244.xml`,
`core/backup/download/this` returns the running configuration, and `core/backup/revertBackup/<id>`
restores one (`$cnf->restoreBackup($filename); $cnf->save();` → `['status' => 'reverted']`). The role
now:

1. records the newest revision **before** the first write — every API write creates a revision, so
   reading it in the apply handler would be too late — and downloads the running configuration to
   the control host
2. applies, then checks reachability
3. on failure, if the router's API still answers, reverts to that revision and re-applies
4. on failure with the router unreachable, fails naming the exact revision to restore at the console

**Step 4 is the honest limit.** When the severed path is the control host's own, nothing the control
host can send will fix it, and no OPNsense timer will undo it either. The console is the undo. That
is why phase 2 does not run without one.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The apply severs the control host's path to the router | Phase 2 | **No savepoint exists** ([above](#the-guard-that-was-not-there-2026-09-19)). The role records the pre-run configuration revision, downloads the configuration to the control host, and reverts over the API if a path is lost *and the router still answers*. If it does not, the console is the only undo — which is why phase 2 does not run without one. |
| The reachability check passes when a path is down, so nothing is rolled back | Phase 2 | **Fixed.** `failed_when: false` made every result `failed: false`, so the check could never trip; it is now `ignore_errors: true`, which registers the failure and lets the collector see it |
| The router rejects a rule and the run reports success | Phases 1–2 | **Fixed.** `addRule`, `setRule` and `delRule` check the API's `result`, not only HTTP 200, and the loop finishes before failing so the report names every rejected rule with the router's own `validations` |
| Removing the conntrack pass rules breaks DNS to each zone's gateway, which no zone rule covers | Phase 2 | **Fixed.** Per-zone gateway-service rules, 9 DNS and 5 DHCP. This is not hypothetical: the control host's own resolver is `10.20.99.1`. DNS checked from each zone in phase 3. |
| **DHCP clients lose their leases once allow-all goes: nothing lets a VLAN client reach the gateway's DHCP server** | Phase 2 | **Fixed.** The DHCP rule's destination is `any`, not the interface address — DISCOVER goes to 255.255.255.255, which an interface-address rule would not match. A lease is checked from each DHCP zone in phase 3. |
| **The policy is applied but the allow-all rules stay, so nothing is enforced and phase 3's allow tests all pass** | Phase 2 | Option A ([Decision](#decision-removing-the-allow-all-rules)): the role deletes them in the same run. Phase 3's **deny** rows are what prove enforcement. |
| **Half the allow-all rules survive the delete, because the role cannot see duplicate descriptions** | Phase 2 | **Fixed** before phase 1 ran ([The 25 rules are 13 descriptions](#the-25-rules-are-13-descriptions)). Deletions are keyed on `uuid`, and phase 1's list came back as 25 rows with 25 distinct uuids. |
| **A reachability target is down for reasons unrelated to the policy, and the rollback reverts a correct apply** | Phase 2 | Every target must answer *before* phase 2; all six did on 2026-09-19. The broker's `1883` is not a target — the VM is up but VerneMQ has never been deployed, so port 22 on the same host stands in for it. After a rollback the role re-checks and says plainly whether the paths came back, so "the apply broke it" and "it was already down" are distinguishable. |
| **Removing "temp: allow all VLAN 99" takes away a management path the declared rules don't replace** | Phase 2, last step | Removed last, after the automation apply is verified, with the console open. Router 443/22 and the management → zone paths re-checked afterwards. |
| **A tenant workload reaches a tenant-facing service on management directly and is cut off.** Tenant DNS `10.20.99.30` and the state store `10.20.99.31` sit on management, and no `tenant_transit -> management` rule is declared. | Phase 2 | Phase 1 records whether any tenant workload is live and talks to either directly. Tenant Terraform runs from management and isn't affected. |
| The live rule set differs from what the restore is assumed to hold | Phase 1 | Plan mode reports adds, updates (field by field) and would-deletes before anything is written, and is compared with [Pre-change state](#pre-change-state-read-2026-09-14) |
| Unmanaged rules are deleted | All | `firewall_delete_unmanaged: false`, the default, confirmed in the prerequisites. Under Option A it is enabled on the phase 2 command line only, and only after phase 1's would-delete list matches the 25 rules exactly. The protected set is never deleted. |
| The apply lands late in a longer play | Phase 2 | Firewall-only playbook. `opnsense.yml` has no `flush_handlers`, so there the apply runs after DNS and DHCP. |

## Prerequisites

- [x] **`opnsense_firewall` fixed** in `ansible-collection-deevnet.net`, branch
  `chg-0007/firewall-role-prereqs`:
  - [x] a zero-write plan mode, as the default, that names every add, update and would-delete with
    field-level differences. **The switch is `firewall_apply`**, false by default
  - [x] `addRule`/`setRule`/`delRule` fail on `result` other than `saved` (`deleted` for a
    deletion), and print the router's `validations`
  - [x] required fields sent as `any` rather than empty strings. Also fixed: the role stored
    `ipprotocol` under the key `protocol`, so the real protocol was never compared
  - [x] a reachability check that actually fails
  - [x] **the savepoint machinery removed and replaced** — the endpoints do not exist
    ([The guard that was not there](#the-guard-that-was-not-there-2026-09-19)).
    `firewall_use_savepoint` and `firewall_savepoint_timeout` are gone;
    `firewall_rollback_on_failure` and `firewall_config_backup_dir` replace them
  - [x] per-interface conntrack pass rules replaced by per-zone gateway-service rules, **covering
    DHCP as well as DNS** — 9 DNS rules and 5 DHCP rules
  - [x] **a defect the record had not anticipated**: duplicate descriptions were invisible, so the
    delete would have removed 13 of 25 rules
    ([The 25 rules are 13 descriptions](#the-25-rules-are-13-descriptions))
  - [x] the `migration-opnsense-firewall` Makefile target passes `EXTRA_ARGS` through, and sets
    `pipefail` so `tee` stops masking a failed play as a successful `make`
- [x] **Mobile `firewall_reachability_targets`** in `ansible-inventory-deevnet`: six targets, one
  live host on each policy-bearing segment that has one. All six answered on 2026-09-19.
- [x] **The allow-all removal decided:** Option A, on 2026-09-14
  ([Decision](#decision-removing-the-allow-all-rules)).
- [x] **The MQTT broker answering**, or its rows dropped: **dropped.** `10.20.35.20` is up but
  `1883` is closed — the VM exists and VerneMQ has never been deployed. Port 22 on the same host
  stands in for it as a reachability target, and the `1883` rows in
  [Verification](#verification) are marked not tested.
- [ ] **Config backup downloaded** from **System → Configuration → Backups → Download** and kept
  off the router ([Console Recovery](/docs/runbook/substrate/recovery/console-recovery/#before-you-need-any-of-this)).
- [ ] **Console kit at the rack:** mini DisplayPort cable, USB keyboard, and a monitor not on the
  affected network.
- [ ] **Vault decrypted before walking over**, including the router's root password in
  `mobile/group_vars/routers/vault.yml`.
- [x] `firewall_delete_unmanaged` confirmed `false` in the rendered variables — it is set nowhere
  in inventory, so the role default holds. Option A overrides it on the phase 2 command line only.
- [ ] Test clients ready: one each on `DVNTM-GUEST` and `DVNTM-IOTV`, and one on `DVNTM`.

---

## Procedure

### Phase 1: Drift audit · *no writes*

Run the role in its plan mode against the router. **Nothing is written.** The run reads the live
rule table and reports.

**Run:**

```bash
cd ansible-collection-deevnet.net
make migration-opnsense-firewall     # plan mode is the role's default
```

The variable that switches plan mode off is **`firewall_apply`**, false by default and never set in
inventory.

**Verify:**

1. The run made no `addRule`, `setRule` or `apply` call, and the router's rule table is unchanged.
2. Record under [Outcome](#outcome):
   - every add, update (with its differing fields) and would-delete
   - any rule the router holds that inventory doesn't declare
3. **Compare with [Pre-change state](#pre-change-state-read-2026-09-14).** The would-delete list
   should be exactly the 25 `temp-allow-all` and `test-rule` entries, with none of
   `firewall_protected_descriptions` in it. **This list is Option A's gate**
   ([Decision](#decision-removing-the-allow-all-rules)): if it lists anything else, phase 2 does not
   run with deletion on. Confirm the two rules outside automation are still the only others.
   INC-0001's first two open items were settled from the 2026-09-14 read; this only confirms nothing
   has changed since.
4. Record whether any tenant workload is live and reaches `10.20.99.30` or `10.20.99.31` directly
   (see [Risk](#risk-and-impact)).
5. **Stop if the report contains anything unexplained.** The apply is a separate decision.

**Undo:** None needed. Phase 1 writes nothing.

### Phase 2: Watched apply · *disruptive*

With the console connected and the phase 1 report read, apply the declared set. The role takes a configuration snapshot first — there is no savepoint ([below](#the-guard-that-was-not-there-2026-09-19)).

**Run:**

```bash
# Option A: deletion on for this one run, on the command line only - never in inventory.
make migration-opnsense-firewall EXTRA_ARGS="-e firewall_apply=true -e firewall_delete_unmanaged=true"
```

`EXTRA_ARGS` is passed through as of this change, so the run keeps the target's timestamped log.
The two `-e` values are what matter, and neither is in inventory: the next run of the role without
them reports and writes nothing.

**Verify:**

1. The run shows:
   - a pre-apply snapshot: a configuration revision id to roll back to, and the configuration
     downloaded to the control host. **Write the revision id down** — it is what you pick at the
     console if the path is lost, and the console cannot read this log
   - the adds, and **deletes that are exactly phase 1's would-delete list** (the 25 rows, by uuid).
     Any other delete means stop
   - the apply
   - all six reachability targets answering
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
| Control host (management) | Exit node `10.20.50.22` 22 (tenant_transit) | Answers | `management -> tenant_transit` |
| Control host (management) | `services.eds.mobile.deevnet.net` `10.20.130.10` 22 | Answers | `management -> tenant_transit: tenant overlay (ADR-0018)` |
| Control host (management) | Pi `10.20.30.11` 22 (iot) | Answers | `management -> iot` |
| Control host (management) | `10.20.35.20` 22 (iot_backend) | Answers | `management -> iot_backend` |
| Control host (management) | Broker `10.20.35.20` 1883 | **Not tested** — VerneMQ is not deployed, the port is closed | `management -> iot_backend` |
| `DVNTM` client (trusted) | `dv00bld001p01` `10.20.99.95` 22 | Answers | `trusted -> management` |
| `DVNTM` client (trusted) | `10.20.31.x` host (iot_vendor), if one exists | Denied | not declared |
| `DVNTM-GUEST` client | `10.20.99.95` 22 (management) | **Denied** | not declared |
| `DVNTM-GUEST` client | `10.20.30.11` 22 (iot) | **Denied** | not declared |
| `DVNTM-GUEST` client | `1.1.1.1` | Answers | internet egress |
| `DVNTM-IOTV` client | `10.20.99.95` 22, `10.20.30.11` 22 | **Denied** | not declared |
| `DVNTM-IOTV` client | `1.1.1.1` | Answers | internet egress |
| A client on `DVNTM-IOT` (iot) | `10.20.99.95` 22 (management) | **Denied** | prohibited by the standard. This is the path CHG-0013 phase 5 demonstrated open |
| A client on `DVNTM-IOT` (iot) | `10.20.35.20` 22 (iot_backend) | Answers | `iot -> iot_backend` |
| Pi `10.20.30.11` (iot) | anything | **Not tested** — the Pi does not answer at all; a PPSK Wi-Fi client stands in for it | — |
| A client in each zone | Its own gateway, DNS 53 | Resolves `dv00bld001p01.mobile.deevnet.net` | gateway-service rule |
| A client in each DHCP zone (trusted, iot, iot_vendor, guest) | Its own gateway, DHCP | Renews a lease | gateway-service rule |

At the router's console, `pfctl -sr | grep -c .` gives a rule count to compare with the phase 1
report.

## Undo

### Undo phase 2

**There is no self-reverting timer.** Nothing on the router undoes this on its own
([The guard that was not there](#the-guard-that-was-not-there-2026-09-19)). Waiting is not a
recovery step.

1. **If a path is lost but the router's API still answers:** the role has already reverted to the
   pre-run revision and re-applied, and its failure message says whether the paths came back. If
   they did not, the apply is probably not what broke them — check the target hosts.
2. **If the control host's own path is lost:** the revert cannot be sent from here. Follow
   [Console Recovery → Core Router](/docs/runbook/substrate/recovery/console-recovery/core-router/) and
   restore the revision the run printed before applying — under **Restore a backup**, matched by
   its `config-<timestamp>.xml` name. A copy of that configuration is also on the control host,
   under `migration-logs/`.
3. **If every path survived but the verification table fails:** disable the offending `ansible:` rule
   under Firewall → Automation → Filter and apply, or restore the downloaded backup. Record which,
   under Outcome.
4. **If removing the two rules outside automation cut a path:** at the console, restore the
   configuration revision taken just before that removal. The automation apply stays in place.

There is no point of no return. The downloaded configuration restores the pre-change rule set at
any time, from the console if not over the network.

**Delete the downloaded configuration when this change closes.** It is the whole router
configuration, secrets included. `migration-logs/` is gitignored in the collection, which stops it
being committed, not from sitting on disk.

---

## Outcome

### Phase 1 — 2026-09-19, passed

Run as `make migration-opnsense-firewall` with `firewall_apply` at its default `false`.
**`changed=0`, and the router still holds 25 managed rules after the run** — the plan wrote
nothing, confirmed by re-reading `searchRule`.

| Gate | Expected | Got |
|---|---|---|
| Would-delete | exactly the 25 `temp-allow-all` and `test-rule` rows | **25 rows, 25 distinct uuids**, every one reported as "not declared in inventory" |
| Protected set in the delete list | none | none. All three protected descriptions listed and excluded |
| Adds | the declared set and nothing else | **47**: 2 anti-lockout + 14 gateway-service (9 DNS, 5 DHCP) + 23 zone policy + 8 internet |
| Updates | empty | **0 of 0** — no declared rule is present on the router yet |
| Router rule table | unchanged | 25 before, 25 after |

Nothing unexplained. The gate for Option A is met: phase 2 may run with deletion on.

**Tenant workloads and the management-resident services** (risk row, and phase 1 step 4):
`10.20.99.30` and `10.20.99.31` do not answer ICMP from the control host. Tenant DNS and the state
store have moved to the domain VMs — `dv02idn001v01` `10.20.25.21` and `dv02tob001v01`
`10.20.25.22`, both on **platform**, which `tenant_transit -> platform` already declares. The risk
this row was written for has been designed out; the [follow-up](#follow-ups) about where
tenant-facing services live is settled in practice and only needs recording.

### Router field behaviour, read 2026-09-19

Read from `dv02cor002p01` before the role was changed, so none of the fixes rests on inference:

| Question | What the router returned |
|---|---|
| Blank rule template | `source_net: "any"`, `destination_net: "any"`, `destination_port: ""`, `protocol` a select with `any` chosen, `direction` `in`, `ipprotocol` `inet` |
| Existing rules read back | `protocol: "any"`, `source_net: "any"`, `destination_net: "any"`, `destination_port: ""` — so comparing against `''` made every rule read as changed |
| Combined TCP and UDP | `TCP/UDP` is a valid `protocol` value, so a DNS rule is one rule, not two |
| Interface-address destination | `opt1ip` … `opt10ip` and `lanip` all appear in `firewall/filter/listNetworkSelectOptions`, alongside `any` and `(self)` |
| A rejected write | HTTP 200 with `{"result":"failed"}`. Even a `GET` to `addRule` answers `200 {"result":"failed"}` |
| Savepoint | Does not exist — see [The guard that was not there](#the-guard-that-was-not-there-2026-09-19) |

### Phase 2 — 2026-09-19, applied

**The declared policy is live. The router is no longer allow-all.**

| | |
|---|---|
| Result | `Added 8, updated 0, deleted 25.` then `Applied, and all 6 required path(s) still answer.` |
| Rule table after | **47 managed rules — exactly the declared set.** Zero `temp-allow-all`, zero `test-rule` |
| Rollback | Not needed. Every rollback handler skipped, so no required path was lost |
| Snapshot taken | `config-1789867120.9272.xml` (2026-09-20T01:18:40Z), configuration also downloaded to the control host |

Per-interface, live: management 14, Trusted 10, platform 5, iot 4, tenant_transit 4, guest 3,
iot_vendor 3, iot_backend 3, storage 1.

Verified from the control host after the apply: router 443/22, platform, iot_backend,
tenant_transit, both tenant workloads (`10.20.129.10`, `10.20.130.10`), the wireless controller
`10.20.99.40:8043`, both Proxmox nodes on 8006, tenant DNS and observability on platform, DNS
resolution through `10.20.99.1`, and internet egress. All answered.

#### It took two attempts, and the guards are why that was safe

**Attempt 1 failed at the snapshot**, before a single write: `_fw_backups.json.items` resolves to
Python's `dict.items` method in Jinja rather than the JSON key. Nothing written, `changed=0`.

**Attempt 2 failed after 39 of 47 additions**, on the new API-result check. The router rejected all
eight internet rules:

```
'rule.destination_net': '!10.20.0.0/16 is not a valid source IP address or alias.'
```

The `!` prefix is the **web UI's** syntax for a negated network. The API expects the separate
`source_not` / `destination_not` booleans. **This is the defect the result check existed to catch.**
The old role accepted any HTTP 200, and OPNsense answers a rejected rule with 200 and
`{"result":"failed"}` — so it would have reported eight successful additions, deleted the
twenty-five allow-all rules in the same run, and left every segment on the site with no route to
the internet, with the play reporting success.

Because the play failed before the handler, the apply never fired: 39 rules sat in the
configuration, unapplied, and the running filter was untouched. The resumed run found all 39
already matching inventory — **0 updates** — added the 8, deleted the 25, and applied once.

#### The two rules outside automation

Both removed, and it was not the manual step this record assumed. On OPNsense 26.7.3_11 the
classic per-interface rule pages are read-only pending migration: the rows show a *"lookup rule
reference"* link and a migration notice, with **no delete control**. They live in the legacy
`<filter><rule>` section, which `Firewall → Automation → Filter` does not manage.

The supported route is `firewall/migration/flush`, and it is **all-or-nothing** —
`delItem('filter.rule')` removes every legacy rule. There were four:

| Interface | Rule | |
|---|---|---|
| `lan` | Default allow LAN to any rule | removed |
| `lan` | Default allow LAN IPv6 to any rule | removed |
| `opt1` Trusted | *(no description)* `any -> 10.20.99.0` | **target** |
| `opt8` Management | `temp: allow all VLAN 99` `any -> any` | **target** |

Flushed all four, then applied. Legacy rule count is now **0**.

Losing the two LAN defaults costs nothing and improves the posture — they were two more undeclared
allow-alls. Checked first: nothing is on the untagged LAN (`192.168.10.0/23` ARP shows only `re0`
itself), and **the anti-lockout rule is not a legacy rule** — it is absent from `<filter><rule>`,
`noantilockout` is unset, and it is still present after the flush. So the LAN recovery path still
reaches the router's own UI and SSH, which is what it is for. What it no longer does is route
onward from LAN, which nothing used.

### Phase 3 — from clients, 2026-09-19

Taken from real clients and corroborated against the router's own firewall log, not from the
control host. Passes are not logged, so an allowed path shows as the *absence* of a block.

Counts are from the router's rolling firewall log, read shortly after each test; the buffer ages
out, so they record what was observed rather than a running total.

**Trusted.** A workstation on `10.20.10.100`, associated to `DVNTM`, reached `dv00bld001p01`
on `10.20.99.95:22` and held the session — after allow-all was deleted **and** after the legacy
`any -> 10.20.99.0` rule was flushed. So `ansible: trusted -> management` is carrying that
traffic on its own. This is the lab exception the segmentation standard does not grant by
default, and it works.

**IoT.** A Mac joined `DVNTM-IOT` with a tenant PPSK key and took `10.20.30.101` from the
DHCP pool — which is itself the first exercise of `ansible: gateway services DHCP iot`, a rule
that replaced the conntrack rules and had never carried a real lease. `management -> iot` was
confirmed in the other direction by ping from the control host.

| From `10.20.30.101` | Observed | Rule |
|---|---|---|
| `10.20.99.95:22` — the Builder | **7 packets blocked**, `Default deny / state violation rule` on `vlan04` | not declared |
| `10.20.99.22:8006` — Proxmox | **33 blocked** | not declared |
| `10.20.130.10:80` — **eds, on the tenant overlay** | **30 blocked** | not declared, and [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §4 forbids declaring it |
| `10.20.30.255:137` — NetBIOS broadcast | 18 blocked | not declared |
| `10.20.35.0/24` — iot_backend | no blocks | `iot -> iot_backend` |
| internet | no blocks | `iot -> internet` |

**The first row closes the hint at the top of this record.** On 2026-09-18, CHG-0013 phase 5
showed a device on `10.20.30.100` reaching the Builder on management. On 2026-09-19 a device on
`10.20.30.101` cannot, and the router logs the drop.

**The eds row is evidence ADR-0020 did not have.** A device attempting to reach its owner's
tenant workload directly was dropped — which is that record's §4 enforced rather than asserted.
It is not a gap: §1 supports direct access, but §3 and §5 place the device-facing endpoint on
IoT Backend, and ADR-0020 records that none of it is built yet.

#### One regression, found and fixed: NTP to the gateway

A sweep of 2000 firewall log entries found exactly one kind of internal traffic being dropped that
should not have been:

```
2026-09-20T02:09:59  block  vlan011  10.20.99.97:59547 -> 10.20.99.1:123
```

`dv02bld001v01` and one DHCP-pool host reaching the router on **NTP**. The gateway-service rules
covered DNS and DHCP because that is what [Goal](#goal) asked for; the router also runs `ntpd` on
every interface, and a DHCP client with no explicit `ntpserver` option falls back to its gateway.
Removing allow-all took time sync away **silently** — clocks drift rather than anything failing
outright, so this would not have surfaced for days.

It matters most where there is no alternative: `storage` is deliberately absent from
`firewall_internet_zones`, so its gateway is the only time source a host there can have.

Fixed by adding a third gateway-service rule per zone, UDP 123 to the interface address — nine
rules, purely additive: `Added 9, updated 0, deleted 0`, and all six paths still answered. Verified
by an actual exchange from `dv02bld001v01`: *"System clock wrong by -0.004222 seconds"*. No further
`:123` blocks. The managed set is now **56 rules**.

Nothing else in the sweep was being dropped.

#### Guest: contained, but this change cannot take the credit

A Mac joined `DVNTM-GUEST` and leased `10.20.40.50`, the first address in the pool — so
`ansible: gateway services DHCP guest` works. Its attempts to reach management and iot_backend
hung, and `1.1.1.1:443` succeeded, which is the expected shape.

**But the denials are not attributable to this change.** `DVNTM-GUEST` is the only SSID on the
controller with `guestNetEnable: true` — read from the Omada Open API on 2026-09-19 — and Guest
Network blocks a client from every local subnet at the access point. Those packets most likely
never reached `dv02cor002p01`: the firewall log shows nothing from `10.20.40.50`, neither blocks
nor passes.

The corroborating observation is that `management -> guest` in the *other* direction was passed by
the router (`pass vlan07 10.20.99.95 -> 10.20.40.50`) and still did not reach the client. The zone
policy did its part; the AP dropped it.

So the guest segment is contained by two overlapping mechanisms, and the zone policy's share is not
separately observable without turning isolation off — which is not worth doing to satisfy a test.
Recorded as **contained, attribution shared**, rather than as a clean pass for this change. The
same read produced [evidence for ADR-0011 open question 4](/docs/architecture/decisions/0011-edge-devices-application-owned/),
which is the more useful outcome.

#### IoT Vendor: full containment, and the cleanest result of the change

`DVNTM-IOTV` has `guestNetEnable: false`, so nothing at the access point intervenes and every
verdict below is the zone policy's. A Mac joined and leased `10.20.31.100` — the third
gateway-service DHCP rule to carry a real lease. Captured from the firewall log by polling it every
four seconds during the test, because the buffer holds only about fifty seconds under WAN
background load.

| From `10.20.31.100` | Blocked | Why |
|---|---|---|
| `10.20.99.95:22` — the Builder | **8** | `iot_vendor -> management` not declared |
| `10.20.99.22:8006` — Proxmox | **106** | same |
| `10.20.35.20:22` — iot_backend | **8** | not declared |
| `10.20.30.100:22` — **a live phone on the IoT segment** | **8** | not declared |
| `10.20.25.20:22` — platform | **7** | not declared |
| `10.20.31.255:137` — broadcast | 15 | not declared |
| `1.1.1.1:443` | none — passed | `iot_vendor -> internet` |

Every drop logged as `Default deny / state violation rule`. This is the full containment
[Network Segmentation](/docs/standards/network-segmentation/) requires of the IoT Vendor segment —
*"IoT vendor to any internal segment"* is a prohibited flow, and it now is one.

The `10.20.30.100` row is worth singling out: a real client on the vendor segment could not reach a
real device on the IoT segment. Cross-segment isolation demonstrated between two live hosts rather
than a packet sent into an empty subnet.

The only non-block entries were the access point itself (`10.20.99.9`) sending mDNS and NetBIOS
*to* the client under the stock *"let out anything from firewall host itself"* rule — inbound from
the router, not traffic from a client.

#### Gateway DNS

`dig @10.20.31.1 dv00bld001p01.mobile.deevnet.net` from the vendor segment returned
**`10.20.99.95`**. The gateway-service DNS rule works, and the result is
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §5 made
concrete: the client resolves the Builder's name while being unable to reach it. Resolution and
reachability are separate, and a service that treats the first as evidence of entitlement has no
boundary.

Checked from `iot_vendor` only. The other segments' DNS rules are identical in shape and were
generated by the same loop, but they have not each been exercised.

## Follow-ups

**Done during this change:**

- [x] **INC-0001 closed** ([2026-09-19](/docs/incidents/2026/0001-firewall-policy-deletion/)), with
  its remaining open items resolved and its index row updated. Its preventive action 4 was found
  never to have worked — see
  [The guard that was not there](#the-guard-that-was-not-there-2026-09-19).
- [x] **The other three OPNsense roles carried the same API-result blindness** — `opnsense_dns`,
  `opnsense_dhcp` and `opnsense_vlans` all accepted HTTP 200 without checking the body. Seventeen
  write tasks now assert on `result`. Confirmed first by a GET against each write endpoint, every
  one of which returned `{"result":"failed"}` with HTTP 200.
- [x] **`deevnet_wifi_psk` is now reconciled.** The shared Wi-Fi key was set at SSID creation and
  never checked again, so inventory held an assertion nothing verified — discovered during phase 3
  when a client would not associate and the key had to be compared by hand. `omada-wireless.yml`
  now reads each declared SSID's key and reports drift, with correction behind its own switch
  because re-keying an SSID disconnects every client on it.

**Still open:**

- [ ] Derive the internet rule's destination from the site, so the same role can apply the home
  policy. It hardcodes `!10.20.0.0/16`.
- [ ] Decide which reachability targets stay permanent in inventory, and which were only for this
  change.
- [ ] Record that tenant-facing services now live on **platform**, not management — tenant DNS
  `10.20.25.21` and tenant observability `10.20.25.22`, both reached by the declared
  `tenant_transit -> platform` rule. This follow-up was written when they sat on management and
  depended on allow-all; CHG-0008 moved them, and phase 1 confirmed the old addresses are dead.
  [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) placed its API on platform for
  the same reason.
- [ ] **Four verification rows are untested, not passed.** The broker's `1883` (VerneMQ is not
  deployed), a wired IoT host (`10.20.30.11` is off), a DHCP *renewal* on trusted as opposed to the
  lease that was already held, and gateway DNS from segments other than `iot_vendor`. None is
  blocking; all are recorded so nobody later reads this change as having proven them. Re-run the
  first two once VerneMQ is deployed and the Pi is back.
- [ ] **Guest containment has shared attribution.** `DVNTM-GUEST` runs with Omada Guest Network
  isolation, so its denials cannot be credited to this change. If that isolation is ever turned
  off, the guest rows become testable and should be re-run.
- [ ] **The new API-result guards have not fired.** They only trigger on a rejection, so the next
  real DNS, DHCP or VLAN run is what will exercise them. Recorded rather than assumed, because
  "verified offline" is exactly how INC-0001's preventive action 4 stayed marked Done while being
  fiction.
