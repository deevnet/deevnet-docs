---
title: "2026-03-26 — Authority Transition Rework"
weight: 20260326
aliases:
  - /docs/runbook/authority-transition-gap-analysis/
---

# 2026-03-26 — Authority Transition Rework

{{< hint info >}}
**Retrospective change record.** This was rebuilt from the gap analysis written at the time,
which is kept below as captured, and from the commits that delivered the fixes. The analysis was
first published in the runbook as "Authority Transition Gap Analysis".

Host names follow ADR-0008. At the time the builder was `provisioner-ph01`, the sites were
`dvntm` and `dvnt`, and the site zones were `dvntm.deevnet.net` and `dvnt.deevnet.net`.
{{< /hint >}}

| | |
|---|---|
| **Change type** | Configuration |
| **Classification** | Structural — playbook, role and inventory changes |
| **Status** | Complete. Analysed and fixed on 2026-03-26. |
| **Site** | mobile, and the builder's multi-site design |
| **Systems** | Builder `dv00bld001p01`: the `bootstrap` role and `bootstrap-authoritative.yml` / `core-authoritative.yml` in `ansible-collection-deevnet.builder`; `disable-` / `enable-opnsense-services.yml` in `ansible-collection-deevnet.net`; `group_vars/bootstrap_nodes.yml` |
| **Automation** | Builder `f5d38d6`, net `d37a95f`, inventory `9600744`, docs `9e0b967` |
| **Risk** | Low to the running site. Nothing changes until an authority transition is run, and then the builder's own IP swap is the risky step. |
| **Related changes** | [2026-03-21 — Flat Network → VLANs](/docs/changes/2026/2026-03-21-flat-network-to-vlans/), which left these playbooks non-functional |
| **Related incidents** | None |
| **Related runbooks** | [Authority Transition](/docs/runbook/building-recovery/authority-transition/); [Configure PXE](/docs/runbook/building-recovery/build-sequence/) (`make bootstrap-auth`); [Build Network](/docs/runbook/building-recovery/build-network/) (`make core-auth`) |

---

## Summary

The **authority transition** is how the builder takes over DNS, DHCP and the gateway from the
core router to bootstrap a site (`make bootstrap-auth`), and hands them back afterwards
(`make core-auth`). The [VLAN migration](/docs/changes/2026/2026-03-21-flat-network-to-vlans/)
moved the site onto the segmented 10-space, and nothing in it touched this procedure.

On 2026-03-26, the day after that migration closed, the runbook was compared against the
automation. It turned out the playbooks were, in the fix commit's words, *"non-functional after
the move to segmented VLANs"*: `bootstrap-auth` never enabled DHCP, served no host records, and
handed out the wrong gateway. The review found this on paper; no failed transition is recorded.
It listed ten gaps, and this change fixed them the same morning. It also recorded three design
decisions the fixes depended on.

## Goal

The end state that counts as done:

- `make bootstrap-auth` puts the builder into bootstrap-authoritative mode for the management
  segment: dnsmasq serving DHCP and DNS, with host records and static reservations taken from
  inventory, and the builder as the gateway (`.1`).
- `make core-auth` hands authority back to the core router and returns the builder to its
  reserved address (`.95`).
- Both playbooks swap the builder's IP themselves, validate before the swap, and log each
  transition.
- The revert direction can stop the core router's DNS and DHCP first, so the two do not
  conflict.
- No site-specific value is hardcoded in role or playbook code.

## Scope

**In scope:** the `bootstrap` role and its dnsmasq template, both authority playbooks,
`group_vars/bootstrap_nodes.yml`, the OPNsense service stop/start playbooks, and the Authority
Transition runbook. **Out of scope, per the analysis:** updating the architecture pages that
still use `mgmt.deevnet.net`, which was left for "a separate pass".

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Changing the IP of the host Ansible runs on drops the session mid-play | Gap 2, the IP swap | The swap runs last, fire-and-forget (`async`, `poll: 0`), after all configuration is done |
| The builder and the core router both serve DHCP at once | Revert to bootstrap mode | `disable-opnsense-services.yml` runs before `make bootstrap-auth` |
| The builder enters bootstrap mode with dnsmasq not running | Gap 9 | Validation before the swap fails the play |

---

## Gap analysis

Performed 2026-03-26 against the segmented 10-space (10.20.x.x with per-VLAN subnets).

**Scope of the review:** `bootstrap-authoritative.yml`, `core-authoritative.yml`, the
`bootstrap` role, inventory group_vars, dnsmasq templates, and the OPNsense DNS/DHCP roles in
`deevnet.net`.

### Critical gaps

#### Gap 1: `bootstrap-authoritative.yml` doesn't enable DHCP

**Runbook says:** `make bootstrap-auth` enables DNS/DHCP/gateway on the builder.

**Reality:** The playbook calls `include_role: bootstrap` without overriding
`bootstrap_tftp_backend` or `bootstrap_dnsmasq_dhcp_enabled`. Inventory has both set to their
production values (`tftpd` / `false`), so running the playbook installs standalone tftpd with DHCP
off.

The playbook enables IP forwarding and masquerading but never actually starts dnsmasq or enables
DHCP. The procedure is non-functional.

**Fix:** The playbook needs to pass `bootstrap_tftp_backend: dnsmasq`,
`bootstrap_dnsmasq_dhcp_enabled: true`, and `bootstrap_dnsmasq_service_enabled: true` as vars to
the role include. *Delivered in `f5d38d6`.*

#### Gap 2: No IP reconfiguration during transition — RESOLVED

**Runbook says:** "Reconfigure builder IP — Move the builder from the gateway IP to its reserved
IP" (promote) and the reverse for revert.

**Fix (2026-03-26):** Both playbooks now swap the management interface IP as the final step
using NetworkManager (`nmcli`). The swap uses `async`/`poll: 0` (fire-and-forget) because changing
the IP drops the SSH connection. All configuration work completes first while connectivity is
stable. The playbooks also handle the default gateway: removed in bootstrap mode (builder IS the
gateway), restored in production mode (core router is the gateway). An idempotency check skips
the swap if the target IP is already configured.

#### Gap 3: No DNS host records in bootstrap dnsmasq — RESOLVED

**Runbook/architecture says:** In bootstrap mode, the builder holds all `dvntm.deevnet.net` DNS
records locally.

**Fix (2026-03-26):** Added `gather_hosts.yml` task to the bootstrap role that builds DNS A
records and CNAME records from inventory (same data patterns as the `opnsense_dns` role). The
`dnsmasq.conf.j2` template now renders `address=` lines for host records and `cname=` lines for
aliases. All hosts with `host_a_record: true` are included regardless of segment.

### High-severity gaps

#### Gap 4: DHCP gateway points to reserved IP

**Runbook says:** In bootstrap mode, the builder IS the gateway.

**Inventory has:** `bootstrap_dhcp_gateway: "10.20.99.95"` — the reserved (production) IP.
Should be `10.20.99.1` in bootstrap mode.

DHCP clients would receive the wrong gateway. This is related to Gap 2 (the IP never changes),
but even if the IP were swapped, this variable would need to change too. *Delivered in inventory
`9600744`, which also moved `dns_servers` to `.1`.*

#### Gap 5: No DHCP static reservations in dnsmasq — RESOLVED

**Runbook says:** Builder carries DHCP configuration with static reservations for every host
MAC.

**Fix (2026-03-26):** The `gather_hosts.yml` task also builds DHCP static reservations from
inventory, filtered to management segment hosts with `dhcp_reservation: true` (same data
patterns as the `opnsense_dhcp` role). The `dnsmasq.conf.j2` template now renders `dhcp-host=`
entries for each reservation.

### Medium-severity gaps

#### Gap 6: Single-VLAN bootstrap vs. multi-VLAN 10-space — RESOLVED

The segmented model has 9+ VLANs. The bootstrap playbook assumes a single flat management
segment — dnsmasq serves DHCP on one interface for one subnet.

**Decision (2026-03-26):** Bootstrap mode is management-VLAN-only (10.20.99.0/24). The builder
provides DNS/DHCP/gateway for the management segment only — enough to PXE-boot the core router
and any management-plane hosts. Once OPNsense is online, it takes authority for all VLANs. Other
segments (trusted, storage, IoT, etc.) are created by the OPNsense and switch playbooks after the
core router exists.

This keeps dnsmasq simple (one interface, one subnet) and avoids replicating VLAN trunking and
multi-scope DHCP on the builder. The switch and OPNsense VLAN configuration remain
manual/semi-automated steps in the build sequence.

#### Gap 7: No OPNsense disable automation (revert direction) — RESOLVED

**Runbook says:** "Disable production DNS/DHCP on router (if it is still operational)"

**Fix (2026-03-26):** Added `disable-opnsense-services.yml` and `enable-opnsense-services.yml`
playbooks to the `deevnet.net` collection. These use the OPNsense API (`kea/service/stop`,
`unbound/service/stop` and their start counterparts) to stop/start DNS and DHCP services. The
authority transition runbook now documents running `disable-opnsense-services.yml` before
`make bootstrap-auth` as a separate step (since it requires vault credentials and targets a
different collection).

#### Gap 8: Hardcoded WAN interface

Both playbooks hardcode `bootstrap_wan_interface: wifi`. The dvnt provisioner (AOOSTAR N1 PRO)
has dual Ethernet and no WiFi. This should come from inventory. *Delivered in `f5d38d6` (WAN
discovered from inventory) and `9600744` (`bootstrap_wan_interface_key`).*

### Low-severity gaps

#### Gap 9: No validation steps automated — RESOLVED

The runbook specifies validation checkpoints at each step.

**Fix (2026-03-26):** Both playbooks now include validation tasks before the IP swap:
- `bootstrap-authoritative.yml`: verifies dnsmasq is running and TFTP port 69 is listening.
  Fails before IP swap if dnsmasq didn't start.
- `core-authoritative.yml`: warns if dnsmasq is still running, verifies TFTP port 69 is
  listening.
- Post-swap validation remains manual (operator reconnects at new IP and runs verification
  commands documented in the runbook).

#### Gap 10: No transition logging — RESOLVED

The runbook says "Record transition with timestamp and operator."

**Fix (2026-03-26):** Both playbooks append a timestamped entry to
`/var/log/authority-transitions.log` with the transition direction, operator (`$USER`), and
hostname.

---

## Procedure

The analysis planned the fixes in five chunks:

- **Chunk A — Make bootstrap-auth functional (Gaps 1, 4, 8).** Fix the playbook vars overrides
  and inventory so `make bootstrap-auth` actually enters bootstrap mode. Low risk, high value.
- **Chunk B — DNS and DHCP content (Gaps 3, 5).** Extend `dnsmasq.conf.j2` to render host
  records and static DHCP reservations from inventory. Requires template work, and possibly a
  gather-hosts task similar to the OPNsense DHCP role.
- **Chunk C — IP reconfiguration (Gap 2).** Automate the interface IP swap. The riskiest chunk:
  modifying the IP of the host you're running Ansible on can break the connection.
- **Chunk D — Architectural decision (Gap 6).** Decide the multi-VLAN bootstrap scope. A design
  decision rather than a code change, but it shapes Chunks B and C.
- **Chunk E — Polish (Gaps 7, 9, 10).** OPNsense disable automation, validation steps,
  transition logging.

## Verification

The plan's checks are the playbooks' own validation before the IP swap (Gap 9): dnsmasq running
and TFTP listening. After the swap, the operator reconnects at the new address and runs the
verification in the [Authority Transition](/docs/runbook/building-recovery/authority-transition/)
runbook.

## Undo

Not recorded. The changes are commits, so reverting them undoes them mechanically, but that
restores playbooks that did not work.

---

## Outcome

All five chunks landed together in one sitting on 2026-03-26, within a minute of each other:

| Time (EDT) | Commit | Repo | Delivers |
|---|---|---|---|
| 07:42:00 | `f5d38d6` | builder | Gaps 1, 2, 3, 5, 8, 9, 10 |
| 07:42:09 | `d37a95f` | net | Gap 7 |
| 07:42:19 | `9600744` | inventory | Gap 4, and the WAN key for Gap 8 |
| 07:42:36 | `9e0b967` | docs | Authority Transition runbook rewritten; this analysis published |

The inventory commit also added one unrelated firewall rule, `trusted -> management`, as a lab
convenience. That is the operator path the
[2026-09-07 incident](/docs/incidents/2026/2026-09-07-firewall-policy-deletion/) later deleted,
and which is now protected from deletion.

As published, the analysis's summary table marked all ten gaps resolved, but gaps 1, 4 and 8
carried no note of their fix. The commits above confirm all three.

The record does not show a full `bootstrap-auth` → `core-auth` cycle being run to prove the
result end to end.

### Decisions

The analysis recorded three decisions that the fixes depended on. Where each stands now:

| Decision | Now |
|---|---|
| **Multi-site provisioner model.** The builder is an appliance: it plugs into one site's management VLAN at a time, with no dual-homing and zero config changes between sites. Every site-specific value comes from inventory, and switching sites means selecting another inventory directory. | Settled by [ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) as the roaming appliance, site code `00`. |
| **Drop `mgmt.deevnet.net`.** Use site-scoped zones only. During bootstrap the builder's dnsmasq serves records in the site zone; in production OPNsense is authoritative for the same zone. | In effect: the site zone is `mobile.deevnet.net` since ADR-0008. The documentation pass it called for is still open (see Follow-ups). |
| **Bootstrap is management-VLAN-only** (Gap 6). | Unchanged. |

## Follow-ups

- [ ] **Remove `mgmt.deevnet.net` from the architecture docs** — the "separate pass" the
  analysis deferred. It is still used in `architecture/builder.md`,
  `architecture/substrate/management-plane/core-services.md` and
  `platforms/management-plane/core-services.md`.
- [ ] **Run a full transition cycle** on the segmented network and record the result, since
  none is recorded.
