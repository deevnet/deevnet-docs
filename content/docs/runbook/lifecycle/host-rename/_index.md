---
title: "Renaming Hosts"
weight: 4
bookCollapseSection: true
---

# Renaming Hosts

What any rename of a host has to reckon with, whether it is one host or the estate. A rename is a
change: open a [change record](/docs/runbook/change-management/change-record-template/) for it.
The 2026-09-05 host rename, [CHG-0003](/docs/changes/2026/0003-host-rename/), is the worked example,
with the phase order that made it survivable.

A hypervisor installed from the Proxmox ISO arrives named `pve`, and needs
[Rename a Proxmox Node](pve-node-rename/).

---

## Two hazards nothing guards against

Both were worked around in the 2026-09-05 rename rather than fixed, and are waiting for the next
one.

{{< hint warning >}}
**Automation never renames a Proxmox VM.** `proxmox_vm` decides existence by name
(`selectattr('name', 'equalto', proxmox_vm_name)`), so a renamed host looks new and it
attempts a clone onto an occupied VMID. `vm_identity`'s audit fails first, which is the safety
net — but clearing it means `qm set <vmid> --name` by hand.

**`git mv` the whole `host_vars/<host>/` directory.** Moving only `vars.yml` and leaving
`identity.yml` behind makes the allocator treat the host as new: fresh VMID, fresh MAC,
duplicate DHCP reservation, orphaned VM. Nothing asserts against this.
{{< /hint >}}

## What the roles handle, and what they need

- **DNS removes stale names only when asked.** `opnsense_dns` deletes records inventory no
  longer declares only with `dns_delete_unmanaged: true`. The default is `false`, so a rename run
  with the default leaves every old A record and PTR in place, reported but not removed.
- **DHCP reconciles on MAC**, which a rename does not change, so reservations update in place.
  A host *deleted* from inventory is pruned only with `dhcp_delete_unmanaged: true`, which also
  defaults to `false`.
- **dnsmasq and GRUB regenerate cleanly.** dnsmasq is a whole-file template, and GRUB configs are
  keyed by MAC.
- **The inventory path has no runtime effect.** Nothing on a running host reads it.
- **Appliances name themselves.** No role sets a device's own hostname. The switch takes its
  name from `switch_vlans`; OPNsense, the AP and the travel router are set by hand in their web
  UIs.
- **A Proxmox node name has no supported rename** — see [Rename a Proxmox Node](pve-node-rename/).
