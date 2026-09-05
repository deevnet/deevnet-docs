---
title: "Declarative Reconciliation"
weight: 6
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 11
---

# Declarative Reconciliation

Close the gap between what inventory declares and what the substrate actually runs. Several roles today reconcile *additively* — they create and update, but never remove — so deleting a host from inventory leaves its live state behind indefinitely.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The substrate is meant to be reconstructible from its declarations. [Building Infrastructure](/docs/runbook/building-recovery/) states that any host can be wiped and rebuilt from source control, and [Naming and Addressing](/docs/architecture/substrate/naming-and-addressing/) makes a host's address "a fact about its declaration, not about the order it booted in".

That holds for creation. It does not hold for deletion. Removing a host from inventory today is a one-way half-operation: the declaration disappears, the live state stays.

This was found concretely on 2026-09-04. `provisioner-vm05` was deleted from inventory during the provisioner rebuild, and left behind a DHCP reservation, a DNS record and four TFTP boot configs — none of which any role will ever remove. The reservation is the dangerous one: because reconciliation keys off the MAC and only ever adds, a renumbered or replaced host can end up with two reservations for one address, and whichever the server consults first wins. That failure looks exactly like success until something tries to reach the host by name.

### Why orphans are worse here than in most estates

Management-plane MACs are a pure function of the VMID, and the allocator hands out the **lowest free** VMID in the range. Deleting a VM therefore punches a hole that a future host will eventually be given — and with it, that host inherits the deleted machine's exact MAC. Orphaned state keyed on a MAC is not inert; it is waiting for its address to be reissued.

The blast radius differs by role, and the differences matter more than the general worry:

- **DHCP self-heals, by luck rather than design.** `opnsense_dhcp` reconciles by MAC, so a recycled MAC matches the stale reservation and takes the *update* path, correcting the address. The orphan is harmless here precisely because the role is additive-by-MAC.
- **PXE boot configs do not.** `grub.cfg-<MAC>` files are only corrected if the `bootstrap` role runs *before* the new VM boots. A recycled MAC that boots first auto-installs from the previous occupant's boot config, unattended, with `timeout=0` and no menu.
- **DNS leaks rather than collides.** Records key on hostname, not MAC, so a recycled VMID does not overwrite anything — the old name simply keeps resolving to an address that now belongs to someone else.

So "we made holes that trigger recycle" is the right instinct, and the ordering constraint it implies is: prune boot configs before the hole is reissued, not merely at some point.

**In Scope**

- Orphan pruning in the roles that write live state to the core router and the PXE server
- A read-only drift report: live state with no matching declaration
- A safety model so a truncated or partially-loaded inventory cannot delete the estate

**Out of Scope**

- Tenant-owned records. Under [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) tenants write their own names over TSIG-signed RFC 2136, and the substrate must not prune what it does not own. Any pruning added here has to be scoped to substrate-managed records specifically.

**Prerequisites**

- [Builder & Core Services](/docs/roadmap/infrastructure/mobile/builder/) — ✅ Complete

---

## Known Orphans ⏳

Live as of 2026-09-04, found by reading the core router's reservations back and comparing them against inventory:

- ⏳ Kea DHCP reservation `BC:24:11:F0:E4:68` → 10.20.99.90 (`provisioner-vm05`, host deleted)
- ⏳ Unbound host override `provisioner-vm05.mobile.deevnet.net` → 10.20.99.90, which still resolves
- ⏳ Four `grub.cfg-bc-24-11-f0-e4-68` files (case and path variants) in the TFTP root
- ⏳ Kea DHCP reservation `BC:24:11:2E:26:4E` → **192.168.10.20**, hostname `vyos-rt01` — a survivor of the pre-VLAN flat network. Neither the address range nor the hostname exists in inventory any more; the host is `core-rt01` today. This one has outlived an entire addressing scheme, which is the clearest possible illustration of why additive-only reconciliation is a problem.

Two further orphans, `BC:24:11:CE:51:EC` → 10.20.99.97 and `BC:24:11:DC:2A:24` → 10.20.99.96, are **not** deferrable drift: they hold the very addresses `provisioner-vm02` and `provisioner-vm03` are being rebuilt onto, under their old Proxmox-assigned MACs. They are removed as part of that rebuild rather than left for this project.

## Reconciliation Gaps ⏳

- ⏳ **`opnsense_dhcp` does not prune.** Its removal list is built only from hosts that explicitly declare `dhcp_reservation: false`; a host deleted from inventory contributes nothing to it, so its reservation is never a candidate for removal.
- ⏳ **`opnsense_dns` does not prune either.** `dns_delete_unmanaged` is named in the role's defaults and referenced in task comments, but no task implements it. The variable reads as a supported switch and is not one.
- ⏳ **`bootstrap` `configure_grub_mac` does not prune.** It renders six filename variants per host to cover firmware differences in `$net_default_mac`, and removes none of them when the entry goes away.
- ⏳ **Decide the safety model before writing any delete path.** Pruning is the one operation where an incomplete inventory is catastrophic rather than merely incomplete. `vm_identity` already sets the precedent worth copying: it surveys every hypervisor and *refuses to act on a partial survey* rather than allocating around the gap.

## Settings That Exist Only in the Running Config ⏳

The mirror image of an orphan: state the substrate depends on that **no declaration describes at all**, so a rebuild of the device silently loses it.

- ⏳ **Kea `next_server` is unmanaged, and is empty on all five VLAN subnets** — trusted (10), iot (30), iot_vendor (31), guest (40) and management (99). `opnsense_dhcp`'s subnet payload sets `pools`, `description` and three `option_data` fields, and never `next_server`, so every subnet the VLAN migration created came into existence without it. This is not a setting that was *lost* in the migration; it was never carried into the new model. Worse, `configure_subnets.yml` only *creates* subnets that do not exist — there is no update path — so adding the field to the payload would not repair the five that already exist.

  Found 2026-09-04 when `provisioner-vm03` PXE-booted and made no TFTP contact whatsoever. With `next_server` empty, Kea advertises its own address in the BOOT header's `siaddr`, and UEFI firmware reads `siaddr` rather than DHCP option 66 — so the client tries to TFTP from the router, which runs no TFTP server. The per-host reservation's `option_data.tftp_server_name` looks like it covers this and does not: it is option 66, and reservations carry no `next_server` field at all, so the subnet is the only place it can live. Same root cause `PXE-TROUBLESHOOTING.md` recorded on 2026-01-10, whose hand-applied fix died with the flat network it was applied to.
- ⏳ Give `configure_subnets.yml` an update path, so subnet settings converge instead of only being seeded at creation.

## Drift Visibility ⏳

- ⏳ Add a read-only drift report that lists substrate-managed live state with no matching declaration — reservations, DNS records and MAC-specific boot configs — so orphans are noticed when they are created rather than months later.
