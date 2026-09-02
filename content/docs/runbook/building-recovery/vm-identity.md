---
title: "Allocate VM Identity"
weight: 12
---

# Allocate VM Identity

A management-plane VM's inventory entry exists **before** its MAC does. For bare
metal a MAC is a hardware fact read off a NIC and typed into inventory; for a
cloned VM there is no NIC to read until something creates one. So the MAC is
**derived from the Proxmox VMID** and written into inventory by a tool, rather
than invented by hand.

Adding a management VM is therefore one decision: **allocate a VMID**. The MAC,
the DHCP reservation and the address all follow from it.

**Repository:** `ansible-collection-deevnet.mgmt`

---

## When This Is Required

| Scenario | Action |
|----------|--------|
| New management-plane VM | Allocate identity before first boot |
| Auditing the substrate | Run read-only; reports the next free VMID |
| Suspected drift | Run read-only; fails naming the offending host |
| Renumbering a VM | Delete the old DHCP reservation **first** — see below |

---

## Commands

Read-only. Surveys every hypervisor, audits every MAC in inventory, prints the
next free VMID, and writes nothing:

```bash
cd ~/dvnt/ansible-collection-deevnet.mgmt
make vm-identity
```

Same, then allocates identity for any management VM that has none:

```bash
make vm-identity-assign
```

---

## Order of Operations

Allocation must precede the VM's first boot, with the DHCP reservation in
between:

1. Add the host to `hosts.yml` and create `host_vars/<host>/vars.yml`
2. `make vm-identity-assign` — writes `host_vars/<host>/identity.yml`
3. Run the `opnsense_dhcp` role against the core router
4. Build the VM (`ansible-playbook playbooks/site.yml --limit <host>`)

Step 3 is not optional and is not reorderable. A VM that boots before its
reservation exists takes an address from the management pool instead, and the
build fails several minutes later at the reachability check — reporting only
that the guest "booted but is not on" its expected address.

---

## What Gets Written

`host_vars/<host>/` is a **directory**, not a single file. The hand-written file
keeps the prose; the generated file holds the two allocated values:

```
dvntm/host_vars/tenant-mgmt-vm01/
├── vars.yml       # hand-written
└── identity.yml   # GENERATED - do not edit
```

`vars.yml` references the generated values and defaults them, so the file still
parses before an identity exists:

```yaml
infrastructure:
  interfaces:
    eth0:
      mac: "{{ deevnet_assigned_mac | default('') }}"

mgmt_vm:
  vmid: "{{ deevnet_assigned_vmid | default(0) }}"
```

A VMID of `0` is how the allocator recognises a host that still needs one.

**Do not hand-edit `identity.yml`.** The MAC is a pure function of the VMID, and
the audit fails if the two disagree. To change either value, delete the file and
re-run — after reading the renumbering warning below.

---

## Why Substrate-Wide

The hypervisors are deliberately
[not clustered](/docs/platforms/management-plane/management-hypervisor/), so
Proxmox enforces VMID uniqueness only *within* a single node. The same VMID
really can exist on two nodes at once — several already do.

Because the MAC derives from the VMID, a VMID that was unique only per node
would put two VMs on one MAC, and the DHCP reservation for it would flip between
their two addresses on every run. So the allocator surveys **every** hypervisor
in the substrate — VMs, containers and templates alike — before answering.

If any hypervisor fails to answer, it **refuses to allocate**:

```
hv02 did not answer (1/2 hypervisors reachable). Refusing to allocate or audit
from a partial survey: a VMID free on the hypervisors that did answer may
already be taken on one that did not, and the two VMs would end up sharing a
MAC.
```

Fix reachability or the API token and re-run; do not work around it.

Substrates do not need to coordinate with each other. The environment octet is
part of the namespace, so dvntm's `02:de:20:…` and dvnt's `02:de:10:…` cannot
collide even at identical VMIDs.

---

## Reading the Report

```
VMIDs in use across 2 hypervisor(s):
100  pve   vdvntm-admin-01
100  pve2  fedora-server-44-1.7-precloudinit
...
Declared in inventory (host, vmid, mac):
tenant-mgmt-vm01  200  02:de:20:00:00:c8

Awaiting allocation: none
Range 200-299, namespace 02:de:20
NEXT FREE VMID: 201  ->  02:de:20:00:00:c9
```

Inventory records a VMID for only the VMs we build, so the hypervisor survey —
not inventory — is what makes the "next free" answer trustworthy.

---

## Audit Failures

| Failure | Meaning | Fix |
|---------|---------|-----|
| Stored MAC does not match the MAC derived from the VMID | `identity.yml` was hand-edited, or the VMID changed without regenerating | Delete `identity.yml`, delete the stale reservation, re-run assign |
| Two hosts declare the same VMID | They would derive the same MAC | Reallocate one of them |
| A declared VMID is occupied by a different VM | The clone would fail on a newid collision | Rename the existing VM, or allocate a fresh VMID |
| The same MAC is declared twice | An assigned MAC collides with an observed one | Reallocate the VM |
| MAC not in the required format | Uppercase or dash-separated | Rewrite lowercase, colon-separated |
| VMID outside the allocation range | Derives an address outside the reserved block | Move it into range, or widen `deevnet_mgmt_vmid_range` |
| PXE GRUB config disagrees with host_vars | A MAC was restated instead of referenced | Reference `hostvars[...]` rather than copying the literal |

---

## Renumbering

> **Changing a VMID is a renumbering, not a resize.** It moves the MAC, the DHCP
> reservation and the address together.

The `opnsense_dhcp` role reconciles by MAC and does **not** prune orphans. Delete
the old reservation on the core router *before* re-running, or the DHCP server
ends up holding two reservations for one address.
