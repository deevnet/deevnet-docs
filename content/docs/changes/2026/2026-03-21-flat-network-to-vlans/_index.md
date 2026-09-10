---
title: "2026-03-21 — Flat Network → VLANs"
weight: 20260321
bookCollapseSection: true
aliases:
  - /docs/migrations/2026-03-21-vlan-migration/
  - /docs/runbook/network-migration/
---

# 2026-03-21 — Flat Network → VLANs

{{< hint info >}}
**Retrospective change record.** This was rebuilt after the fact from the runbook that drove
the change, the per-step automation logs in `ansible-collection-deevnet.net/migration-logs/`,
and git history. The procedure pages are the plan as it was run. Where execution departed from
it, [Outcome](#outcome) says so.

Host names follow ADR-0008. At the time they were `core-rt02`, `access-sw01`, `ap01` and
`provisioner-ph01`, which is how they appear in the logs. The inventory was then `dvntm`; it has
since been renamed `mobile`.
{{< /hint >}}

| | |
|---|---|
| **Change type** | Migration |
| **Classification** | Disruptive |
| **Status** | Complete. Executed 2026-03-21 to 2026-03-24, closed 2026-03-25. |
| **Site** | mobile |
| **Systems** | Core router `dv02cor002p01` (OPNsense), access switch `dv02acc001p01` (SG2218), AP `dv02wap001p01` (EAP650-Outdoor), builder `dv00bld001p01` with the Omada controller, hypervisor `dv02hyp001p01` |
| **Automation** | `ansible-collection-deevnet.net`, `make migration-*` targets, run against a target inventory `dvntm-new` |
| **Risk** | High. The builder's own network path moves mid-change, and a console cable is required. |
| **Related changes** | [2026-03-26 — Authority Transition Rework](/docs/changes/2026/2026-03-26-authority-transition-rework/), which repaired the authority transition playbooks this change left non-functional |
| **Related incidents** | None |
| **Related runbooks** | [Build Network](/docs/runbook/building-recovery/build-network/), whose network phase is this procedure; [Console Recovery](/docs/runbook/recovery/console-recovery/) |

---

## Summary

The mobile site ran as one flat network on 192.168.10.x. Router management, hypervisors, IoT
devices and guests shared a single broadcast domain and a single level of trust. This change
split that network into the segments the
[Network Segmentation](/docs/standards/network-segmentation/) standard defines. Each segment
got its own VLAN and `10.20.<vlan>.0/24` subnet, with traffic between them routed by the core
router under default-deny zone policy.

The change was built to be additive for as long as possible. The new VLANs, interfaces and
trunk tagging went in alongside the flat network. The switch was reachable on both old and new
management addresses before the builder moved. The flat network was removed only after
everything had moved across.

## Goal

The end state that counts as done:

- **VLANs** 10, 20, 25, 30, 31, 35, 40, 50, 51, 52 and 99 exist on the core router and in the
  switch's VLAN database. Each routed segment has a `10.20.<vlan>.1` gateway on the router.
- **The switch uplink** `gi1/0/1` carries every VLAN tagged, with native VLAN **999**
  (blackhole), so untagged traffic reaches nothing.
- **Management is VLAN 99**, all static: router `10.20.99.1`, switch `10.20.99.10`, AP
  `10.20.99.9`, hypervisor `10.20.99.21`, builder `10.20.99.95`.
- **Kea DHCP** serves each DHCP segment, and static reservations follow inventory.
- **Traffic between segments** is default-deny, with explicit zone allows from
  `group_vars/all/firewall.yml`.
- **Every access port** is on the VLAN its host declares in `host_vars/dv02acc001p01.yml`.
  VLAN 1 is gone from the ports and from switch management.
- **SSIDs map to segments:** `DVNTM` → 10, `DVNTM-IOT` → 30, `DVNTM-IOTV` → 31,
  `DVNTM-GUEST` → 40.
- **Inventory describes the new network:** `dvntm-new` is promoted to `dvntm`, and nothing is
  left on 192.168.10.x.

VLANs 50–52 were per-tenant segments at the time. On 2026-08-30 they were replaced by the tenant
fabric's transport segments ([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)).
The [network reference](/docs/runbook/network/network-reference/) has the current table.

## Scope

**In scope:** the core router, the access switch, the AP, the builder, and the hypervisor's
management address on the mobile site. **Out of scope:** the home site.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The builder loses its own path. It runs Ansible, the Omada controller, the artifact server and PXE, and it changes both IP and VLAN. | Phase 3, steps 5c–5d | The switch is dual-homed on VLAN 1 and 99 first (5b). The builder is on an ethernet cable, never wireless. Console access is available. |
| A trunk change cuts switch management | Phases 2, 4 | The native VLAN stays 1 until the router answers on tagged VLANs (9b). A console cable is on hand. |
| Wireless clients drop when the AP's port moves | Phase 5, step 10 | The SSIDs are reconfigured in step 13 |
| New addresses do not resolve in DNS | Phases 3–5 | Ansible uses inventory IPs, and so does manual checking. DNS is refreshed post-migration. |
| Router or switch configuration is lost | Throughout | The switch `running-config` and an OPNsense configuration download are taken in preflight |

---

## Prerequisites

The plan required these before step 2 ([phase 1](prerequisites/) has the detail): the vault
decrypted; the switch `running-config` saved; an OPNsense configuration backup downloaded;
console access to the switch and the router; the builder cabled to `gi1/0/16`, never on
wireless; the physical port map traced against `host_vars/dv02acc001p01.yml`; and a passing
`make preflight`. The logs record only the last of these: preflight passed on 2026-03-21 at
13:51.

## Procedure

{{< mermaid >}}
flowchart TD
    A["<b>1. Prerequisites & Preflight</b><br/>Vault, backups, connectivity checks"]
    B["<b>2. VLAN Foundation</b><br/>OPNsense VLANs, switch database, trunk uplink"]
    C["<b>3. Builder Cutover</b><br/>OPNsense interfaces, switch dual-mgmt,<br/>builder IP & port move"]:::critical
    D["<b>4. Services & Routing</b><br/>DHCP, firewall rules, trunk PVID"]
    E["<b>5. Port Migration & Wireless</b><br/>Access ports, management cutover,<br/>Omada adoption, SSIDs"]
    F["<b>6. Post-Migration</b><br/>Validation, DNS refresh, cleanup"]

    A --> B --> C --> D --> E --> F

    classDef default fill:#2d333b,stroke:#539bf5,color:#adbac7
    classDef critical fill:#3d1f00,stroke:#d29922,color:#e6c068
{{< /mermaid >}}

| Phase | Steps | Disruption |
|---|---|---|
| [1. Prerequisites & Preflight](prerequisites/) | 1 | None; read-only |
| [2. VLAN Foundation](vlan-foundation/) | 2–4 | None; additive only |
| [3. Builder Cutover](builder-cutover/) | 5a–5d | The builder is unreachable between 5c and 5d |
| [4. Services & Routing](services-and-routing/) | 6–9b | Untagged trunk traffic is blackholed from 9b |
| [5. Port Migration & Wireless](port-migration/) | 10–13 | Each port as it moves; wireless until 13 |
| [6. Post-Migration](post-migration/) | — | None |

## Verification

The plan's acceptance criteria were `make postcheck` passing on every host (see
[post-migration](post-migration/)), which covers OPNsense VLANs, the switch database and trunk,
device reachability, gateway IPs, and builder state; and a client on each SSID getting a lease
on that SSID's segment and reaching the internet. [Outcome](#outcome) records what was actually
checked.

## Undo

[Undo Procedure](undo/) backs the steps out in reverse order. Step 11 is where undo stops being
practical, and it has no written undo.

---

## Outcome

The change completed. The final postcheck, at 2026-03-24 08:10, passed on every host.

| When | Steps | What the logs and history show |
|---|---|---|
| 03-21 13:51 | 1 | Preflight passed on all four hosts |
| 03-21 14:06–14:58 | 2, 3, 4 | Steps 2 and 4 each passed on their second run. Step 3 took six runs; its failure was `cli_config` rejecting the SG2218 platform (`diff_match` unsupported). |
| 03-21 15:21–17:46 | 5a–5d, 7, 8 | 5a needed the manual GUI step. 5c ended in the expected timeout when the interface reloaded. 5d has no log. 8 ran and changed nothing, because 5a had already set the IPs. |
| 03-23 07:57–08:43 | 9, 9b, 10, 11 | Inventory promoted at 08:19. DHCP re-run: Kea subnets were now created from `deevnet_vlans`, and Kea was enabled on every VLAN interface. |
| 03-23 17:17 – 03-24 06:21 | 12, 13 | The Omada controller was reinstalled on 6.1. `migration-omada-ssids` ran four times; the SSIDs ended up set on the AP itself. |
| 03-24 07:44–08:10 | Post | Six postcheck runs while the postcheck itself was fixed. The last passed everywhere. |
| 03-24 16:57 | 9 | Firewall policy re-applied |
| 03-25 | — | Change closed |
| 09-04 | 11, cleanup | `dvntm-old` removed from inventory |

Checked from clients at the time: `DVNTM` handed out `10.20.10.100` (VLAN 10), and `DVNTM-GUEST`
handed out `10.20.40.50` (VLAN 40).

### Departures from the plan

- **Step 5a:** OPNsense has no API to assign interfaces or to set interface IPs. Both were done
  in the GUI, with the playbook pausing for it.
- **Step 5a2:** the temporary pass rules saved through the filter API but never compiled into
  pf. They were loaded with `pfctl` over SSH instead.
- **Step 5d:** the port move was finished by hand. The playbook's removal of VLAN 1 did not
  reliably leave VLAN 99 as a member.
- **Step 6:** skipped. The builder cutover had already proven the VLAN 99 path end to end.
- **Step 7:** Kea listened only on `re0`, so the new segments got no leases. Fixed by
  enabling Kea on every VLAN interface, now done by the `opnsense_dhcp` role.
- **Step 12:** controller 5.12.7 does not listen on TCP 29814, which the AP's adoption needs.
  The controller was reinstalled fresh on 6.1.
- **Step 13:** Omada 6.1 would not push VLAN-tagged SSIDs to AP firmware 1.0.4. The SSIDs were
  configured in the AP's standalone web UI.
- **Cross-VLAN routing:** the switch had no default route, so replies to other segments were
  dropped. Fixed with a default gateway, which inventory now declares.

## Follow-ups

**Knock-on effect.** The change left the authority transition playbooks non-functional on the new
network. `bootstrap-auth` no longer enabled DHCP and would have handed out the wrong gateway.
Nothing in this plan covered them. A review found it the day after the change closed, and it was
fixed the same morning: [2026-03-26 — Authority Transition Rework](/docs/changes/2026/2026-03-26-authority-transition-rework/).

The AP was forgotten from the controller on 2026-03-24 with a configuration reset, and has been
pending since. The switch was never adopted. Both still run their 2023–2024 firmware. The rest
of the automation backlog is in [Issues & Follow-ups](troubleshooting/).
