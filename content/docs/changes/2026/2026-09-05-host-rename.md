---
title: "2026-09-05 — Host Rename (ADR-0008)"
weight: 20260905
aliases:
  - /docs/runbook/host-rename/
---

# 2026-09-05 — Host Rename (ADR-0008)

{{< hint info >}}
**Retrospective change record.** This was rebuilt from the runbook page that tracked the rename
as it ran (marked done on 2026-09-08), and from the commits and pull requests across the seven
repos it touched. Times are local (UTC−4), from commit timestamps.
{{< /hint >}}

| | |
|---|---|
| **Change type** | Migration |
| **Classification** | Disruptive |
| **Status** | Complete. Executed 2026-09-05, 08:41–13:55; recorded done 2026-09-08. Four follow-ups open. |
| **Site** | mobile; home received its site identity only, having no hosts |
| **Systems** | Every host in the mobile inventory; DNS and DHCP on `dv02cor002p01`; both Proxmox nodes; the site inventories and every repo that names a host, site or zone |
| **Automation** | Pull requests across `deevnet-docs`, `ansible-inventory-deevnet`, the three collections, `deevnet-image-factory`, `deevnet-tenant-factory` and `deevnet-tenant-tdemo` — see [Procedure](#procedure) |
| **Risk** | High. The first live change was DNS and DHCP (phase 8), and a Proxmox node name has no supported rename (phase 13). |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Renaming Hosts](/docs/runbook/lifecycle/host-rename/); [Rename a Proxmox Node](/docs/runbook/lifecycle/host-rename/pve-node-rename/) |

---

## Summary

The migration that brought the estate onto the naming scheme in
[ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/): fixed-width hostnames
(`dv02hyp001p01`), site codes, and the `home` / `mobile` DNS zones. The site inventories were
renamed with it, from `dvnt/` and `dvntm/` to `home/` and `mobile/`. The ADR was proposed on
2026-09-04 and accepted as the first step of the change.

## Goal

The end state that counts as done:

- Every host carries its ADR-0008 name everywhere: in inventory, DNS, DHCP and its OS
  hostname, on appliances, and — for hypervisors — as the Proxmox node name.
- The site zones are `home.deevnet.net` and `mobile.deevnet.net`, and the inventories are
  `home/` and `mobile/`.
- The home site has its identity declared.
- DNS and DHCP carry only declared names, with no stale records left behind by the rename.

## Scope

All hosts in the mobile inventory, both site inventories, the DNS zones, and every repo that
names a host, a site or a zone. The home site had no hosts to rename.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Every renamed host leaves a stale A record and an ambiguous PTR | Phase 8 | Phase 4 implemented the DNS prune before any live change |
| Automation clones onto an occupied VMID when it meets a renamed VM | Phase 7 | `vm_identity`'s audit fails first; VMs are renamed by hand with `qm set <vmid> --name` |
| The allocator treats a host as new if `identity.yml` is left behind | Phase 6 | `git mv` the whole `host_vars/<host>/` directory |
| A Proxmox node name has no supported rename | Phase 13 | Done last, on standalone nodes only, with an `/etc/pve` tarball as the rollback |

---

## Procedure

Least risky first; each phase landed on its own and was verified before the next began.

| # | Phase | Touched | Landed |
|---|-------|---------|--------|
| 1 | Accept the ADR, update the standards, write the runbook | Docs only | 08:41 — docs `85863b3` |
| 2 | Rename the inventory directories | Control plane only | 08:54 — inventory `269425b`; every other repo re-pointed at 08:55 |
| 3 | Give `home` its site identity | Empty site | 09:10 — inventory `42aae2f` |
| 4 | Fix the defects that made the rename survivable | Shared roles | 09:17 — net `df6d3af` (DNS reconciliation) |
| 5 | Destroy tdemo | The only live tenant | 09:30 — inventory `76911dd`, tenant-factory `bae93e3` |
| 6 | Rename mobile hostnames in inventory | Inventory only, no live change | 09:37 — inventory `0b681e5`, builder `a16ed6b`, image-factory `121e0ec` |
| 7 | Rename the VMs in Proxmox | Out-of-band | Not recorded — done on the node |
| 8 | Apply to live DNS and DHCP | First live change | Not recorded — no commit; the playbook runs left no record |
| 9 | OS hostnames | Managed hosts | Not recorded |
| 10 | Appliance hostnames | Manual, per device | Switch only — 13:14, net `8877a74`. Three appliances outstanding. |
| 11 | The zone rename | Atomic, cross-repo | 10:05 — inventory `edaf750`, image-factory `60e5548`, tenant-factory `68dd220`, tdemo `af97ece`; 10:09 — net `8b8839f` (compare the zone, not just the address) |
| 12 | Documentation and residue | Docs, filesystem paths | 10:24–10:36 — inventory `86620f8`, docs `65e54e5`, builder `0409ffb` (site-agnostic artifact root), tenant-factory `7983010`. Residue outstanding. |
| 13 | Rename the Proxmox nodes | Out-of-band, per hypervisor | 11:20–12:17 — builder `3915d8b` (`proxmox_node_base`), inventory `c85dbd2` and `1a95f60`, image-factory `1cce51e`, tenant-factory `57c2310`, docs `b6078f5` |

Phase 13 came last deliberately: the Proxmox node name is the one identifier with no supported
rename, so it waited until the estate around it was already consistent. It followed
[Rename a Proxmox Node](/docs/runbook/lifecycle/host-rename/pve-node-rename/):

| Host | Node was | Node is |
|------|----------|---------|
| `dv02hyp001p01` | `pve` | `dv02hyp001p01` |
| `dv02hyp002p02` | `pve2` | `dv02hyp002p02` |

### What Phase 4 fixed

The rename could not be done safely until three shared-role defects were dealt with. All
three are resolved; they are recorded here because the reasoning still applies to the roles.

- **`opnsense_dns` had no delete task.** The `dns_delete_unmanaged` step its own header
  described was never implemented, so renaming 17 hosts would have left 17 stale A records
  resolving to the same addresses, with ambiguous PTRs behind them. It is implemented now and
  gates both delete tasks — and it is the precedent
  [`opnsense_firewall` lacked at the time](/docs/incidents/2026/2026-09-07-firewall-policy-deletion/).
- **DHCP reconciles on MAC**, which a rename does not change, so reservations updated in place
  with no duplicates and no orphans. dnsmasq is a whole-file template and GRUB configs are
  keyed by MAC, so both regenerated cleanly.
- **The inventory directory rename had no runtime effect.** Nothing on a running host reads
  the inventory path, so it was a `git mv` and six line edits.

## Verification

Each phase was verified before the next began. The checks used are not recorded, except for
phase 13, whose verification is in
[Rename a Proxmox Node](/docs/runbook/lifecycle/host-rename/pve-node-rename/#verify).

## Undo

Phases 2–3 were reversible with a `git revert`. Phase 8 was the first change a user could
notice. Phase 13 has its own rollback in
[Rename a Proxmox Node](/docs/runbook/lifecycle/host-rename/pve-node-rename/#rollback). No undo
is recorded for the other phases.

---

## Outcome

The rename completed in one morning. Phases 1–13 landed between 08:41 and 13:14, and the last
related change, turning off Unbound's self-registration, at 13:55. The runbook recorded it done
on 2026-09-08.

### Departures from the plan

- **Phase 10 landed out of order, and only in part.** The switch took its new name at 13:14,
  after phase 13. OPNsense, the AP and the travel router still carry their old names, because
  each can only be set through its own web UI and no role sets a device's own hostname.
- **Three stale DHCP reservations were removed by hand:** `vyos-rt01` from the pre-migration
  flat network, `provisioner-vm05`, and the VyOS host as it left. The DHCP role pruned only hosts
  still in inventory, not hosts deleted from it. That gap was closed at 10:59 (net `13490c0`).
- **VyOS was dropped during the change** (10:41–10:53: inventory `dd58fbb`, builder `d749b26`,
  net `5a0d781`). This was not one of the thirteen phases; OPNsense is the committed perimeter.
- **Unbound's self-registration was turned off in code but not applied.** Net PR #15 merged at
  18:15. Applying it while clients still search `deevnet.net` breaks short-name resolution
  estate-wide, so it waits on net #14.

## Follow-ups

| Item | Tracked | Status |
|---|---|---|
| OPNsense, the AP and the travel router still carry pre-ADR-0008 hostnames | net #12 | Open |
| Kea hands clients the root domain as their search domain. Fix this first, let leases renew, then apply PR #15 with `dns.yml --tags registration`. | net #14 | Open |
| Stale `dvnt` / `dvntm` and `pve` / `pve2` tokens in the other repos | docs #19 | Open |
| Tenant offboarding does not exist | mgmt #10 | Open |
| Two hazards were worked around rather than fixed, and wait for the next rename | [Renaming Hosts](/docs/runbook/lifecycle/host-rename/) | Open |
