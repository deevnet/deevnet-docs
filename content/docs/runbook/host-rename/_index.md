---
title: "Host Rename"
weight: 9
bookCollapseSection: true
---

# Host Rename

Procedures for migrating the estate to the naming scheme in
[ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) — fixed-width hostnames
(`dv02hyp001p01`), site codes, and the `home` / `mobile` DNS zones.

[Change Management](/docs/runbook/change-management/) classifies this as a **Disruptive** change:
staged rollout, dry run before apply, and a documented rollback per step. It also states that
*"manual changes without validation are considered defects"* — every manual step below carries its
own verification for that reason.

{{< hint warning >}}
**Three things that will bite.** Read these before starting any phase.

1. **A rename orphans its DNS record.** `opnsense_dns` has no delete task — the `dns_delete_unmanaged`
   step its own header describes was never implemented. Renaming 17 hosts leaves 17 stale A records
   resolving to the same addresses, and ambiguous PTRs with them. Phase 4 fixes this, and it must
   land before Phase 8.
2. **Automation never renames a Proxmox VM.** `proxmox_vm` decides existence by name, so a renamed
   host looks new and it attempts a clone onto an occupied VMID. `vm_identity`'s audit fails first,
   which is the safety net — but clearing it means `qm set <vmid> --name` by hand (Phase 7).
3. **`git mv` the whole `host_vars/<host>/` directory.** Moving only `vars.yml` and leaving
   `identity.yml` behind makes the allocator treat the host as new: fresh VMID, fresh MAC, duplicate
   DHCP reservation, orphaned VM. Nothing asserts against this.
{{< /hint >}}

---

## What is not as bad as it looks

- **The inventory directory rename has no runtime effect.** Nothing on any running host reads the
  inventory path. It is a `git mv` and six line edits, fully independent of the zone rename.
- **DHCP reconciles on MAC**, which a rename does not change, so reservations update in place with
  no duplicates and no orphans. dnsmasq is a whole-file template, and GRUB configs are keyed by MAC,
  so both regenerate cleanly.

---

## Order

Least risky first. Each phase lands on its own and is verified before the next begins.

| # | Phase | Touches |
|---|-------|---------|
| 1 | Accept the ADR, update the standards, write this runbook | Docs only |
| 2 | Rename the inventory directories | Control plane only |
| 3 | Give `home` its site identity | Empty site |
| 4 | Fix the defects that make the rename survivable | Shared roles |
| 5 | Destroy tdemo | The only live tenant |
| 6 | Rename mobile hostnames in inventory | Inventory only, no live change |
| 7 | Rename the VMs in Proxmox | Out-of-band |
| 8 | Apply to live DNS and DHCP | **First live change** |
| 9 | OS hostnames | Managed hosts |
| 10 | Appliance hostnames | Manual, per device |
| 11 | The zone rename | Atomic, cross-repo |
| 12 | Documentation and residue | Docs, filesystem paths |

Phases 2–3 are reversible with a `git revert`. Phase 8 is the first change a user could notice.
