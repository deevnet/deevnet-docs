---
title: "Host Rename"
weight: 9
bookCollapseSection: true
---

# Host Rename

**Completed 2026-09-05.** The migration that brought the estate onto the naming scheme in
[ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) — fixed-width hostnames
(`dv02hyp001p01`), site codes, and the `home` / `mobile` DNS zones.

This page is the record of what was done. The one part still worth following is
[Rename a Proxmox Node](/docs/runbook/host-rename/pve-node-rename/), kept because a node
installed from the Proxmox ISO arrives called `pve` and will need it again.

## The sequence, as executed

Least risky first; each phase landed on its own and was verified before the next began.

| # | Phase | Touched |
|---|-------|---------|
| 1 | Accept the ADR, update the standards, write the runbook | Docs only |
| 2 | Rename the inventory directories | Control plane only |
| 3 | Give `home` its site identity | Empty site |
| 4 | Fix the defects that made the rename survivable | Shared roles |
| 5 | Destroy tdemo | The only live tenant |
| 6 | Rename mobile hostnames in inventory | Inventory only, no live change |
| 7 | Rename the VMs in Proxmox | Out-of-band |
| 8 | Apply to live DNS and DHCP | First live change |
| 9 | OS hostnames | Managed hosts |
| 10 | Appliance hostnames | Manual, per device |
| 11 | The zone rename | Atomic, cross-repo |
| 12 | Documentation and residue | Docs, filesystem paths |
| 13 | Rename the Proxmox nodes | Out-of-band, per hypervisor |

Phases 2–3 were reversible with a `git revert`. Phase 8 was the first change a user could
notice. Phase 13 came last deliberately: the Proxmox node name is the one identifier with no
supported rename, so it waited until the estate around it was already consistent.

## What Phase 4 fixed

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

## Still true for any future rename

Two hazards were worked around rather than fixed, and will be waiting next time.

{{< hint warning >}}
**Automation never renames a Proxmox VM.** `proxmox_vm` decides existence by name
(`selectattr('name', 'equalto', proxmox_vm_name)`), so a renamed host looks new and it
attempts a clone onto an occupied VMID. `vm_identity`'s audit fails first, which is the safety
net — but clearing it means `qm set <vmid> --name` by hand.

**`git mv` the whole `host_vars/<host>/` directory.** Moving only `vars.yml` and leaving
`identity.yml` behind makes the allocator treat the host as new: fresh VMID, fresh MAC,
duplicate DHCP reservation, orphaned VM. Nothing asserts against this.
{{< /hint >}}

## Related

- [Naming standard](/docs/standards/naming/) — the scheme this migration adopted
- [ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) — the decision
