---
title: "Limits"
weight: 5
---

# Limits

The rest of this section describes the architecture as designed. This page describes what the
hardware underneath it cannot do.

Both are true at once, and the second is the easier one to forget, because the first reads
like a datacenter: tenants, fabrics, authority boundaries, everything reproducible from code.
The [design philosophy](/docs/architecture/) already notes that Deevnet operates at a smaller
scale than the platforms it borrows from — but scale is not the interesting constraint.
**Resilience is.** Deevnet runs on consumer hardware with no redundancy anywhere in the
critical path, and its recovery model is *rebuild*, not *failover*.

That is a deliberate trade, and a defensible one for a portable lab. It is written down here
so that nobody reads the architecture and assumes otherwise.

---

## No out-of-band management

There is no IPMI, iDRAC, iLO, or remote KVM on any device in the estate.

When a device is misconfigured badly enough to lose its own management path, recovery is
**physical**: a monitor and a USB keyboard, at the device. Different devices need different
cables — mini DisplayPort for the core router, a DisplayPort→HDMI adapter for the hypervisors
— which is a real operational cost at the moment you can least afford one. See
[Console Recovery](/docs/runbook/console-recovery/).

The nearest substitute is Wake-on-LAN, declared per host (`wol: true`) and driven by
`playbooks/wol.yml`. It is strictly one-way: it can wake a powered-down node, but it cannot
power-cycle a hung one, reset it, or show you why it will not boot.

## Nothing is clustered

The two Proxmox nodes are standalone. There is no cluster, no quorum, no HA manager, and no
automatic failover — a node that is down takes its guests with it until it comes back.

The consequence reaches further than availability. Without a cluster filesystem there is
nothing enforcing VMID uniqueness across the substrate, so inventory does it instead:

> The hypervisors are not clustered, so uniqueness across the substrate is enforced by the
> allocator (`deevnet.mgmt playbooks/vm-identity.yml`), not by Proxmox.
>
> — `mobile/group_vars/all/main.yml`

That is the shape of most compensation here: something the hardware does not provide, rebuilt
in software, in inventory, and in git.

## Storage is local to the node that runs the workload

[Shared storage](/docs/architecture/substrate/storage/) is documented as a planned addition,
not a built one. VM disks live on the hypervisor's own `local-lvm-big-thin`.

So even if the nodes were clustered there would be nothing to migrate to. Losing a hypervisor
is a rebuild-and-restore, not a failover, and the recovery time is however long a rebuild
takes.

## Every network device is singular

| Device | Redundancy | If it fails |
|---|---|---|
| Core router `dv02cor002p01` | None — no CARP pair | Whole site: routing, DNS, DHCP, firewall, egress |
| Access switch `dv02acc001p01` | None — no second L2 path | Whole site's wired connectivity |
| Access point `dv02wap001p01` | None | Wireless only; wired is unaffected |
| Edge router `dv02edg001p01` | None | Upstream connectivity |

Two of those take the entire site with them. This is also why a factory reset of the access
switch is itself an outage rather than a repair — every port returns to VLAN 1 and the uplink
trunk goes with it.

## Consumer NICs, single-homed hosts

The core router's LAN and WAN are Realtek interfaces (`re0`, `re1`) — the `opnsense_vlan_parent`
every VLAN sub-interface is built on.

Both hypervisors are **single-NIC**. On `dv02hyp002p02`, management, tenant transit and the
fabric underlay all ride `eno2` as VLAN sub-interfaces of a VLAN-aware `vmbr0`; `dv02hyp001p01`
is the same shape, which is why adding the MQTT broker to IoT Backend meant converting its
switch port to a trunk rather than using a second port — there isn't one.

There is no bonding, no LACP, and no NIC-level redundancy anywhere. A failed port, cable or
NIC takes the host off the network.

## The rebuild path is duplicated inside the thing it rebuilds

The builder is **not** a single point of failure, and it is the one part of this page that
mostly reads the other way. It is [explicitly a role rather than a
pet](/docs/architecture/builder/) — *"any suitable host can assume it via code — rebuilding or
replacing the provisioner is expected"* — and it is self-contained, portable and air-gapped
capable, able to provision a site from nothing with no upstream dependency. That detachability
is what makes *rebuild rather than failover* a credible strategy at all.

The duties are already spread. `builder` covers three hosts; artifact serving, bootstrap/PXE
and workstation duties each cover two.

The limit is **where** the copies live. Two of the three are management-plane VMs on
`dv02hyp001p01` — inside the substrate they would be used to rebuild. For an everyday failure
that duplication is real. For a substrate-level one it collapses to the third copy, the
physical node you can detach and carry, and there is exactly one of those at the moment it
matters most.

One production role is genuinely single-instance: `dv00bld001p01` is the only
`network_controllers` member, so the Omada controller has no second copy. That costs wireless
and switch *management* rather than wireless or switching — adopted devices keep forwarding
perfectly well without a controller.

{{< hint info >}}
**A caveat about deployment mode, not architecture.** In production the builder sits on the
management segment, so automation runs from *behind* the policy it edits. The builder's own
design allows it to be attached elsewhere — but that does not rescue a router with no rules
loaded, which stays a [console job](/docs/runbook/console-recovery/core-router/).
{{< /hint >}}

## One site has hardware

`home` exists as an inventory skeleton with no hosts. There is no second site to fail over to,
and no cross-site redundancy of any kind.

The mobile rack also travels, which makes availability partly a physical question: anything
depending on the substrate stops when the rack leaves the building. That is not a fault, but
it is a property worth stating — the EdS tenant records it plainly as *"the lights stop when
the rack leaves."*

## Backups live on the thing being backed up

OPNsense keeps its own configuration history on the router, which covers a configuration
mistake but not a failed disk. No collection carries off-box backup automation; the manual
download step in the
[segmentation prerequisites](/docs/runbook/network-migration/prerequisites/) is the whole of
the practice.

---

## What holds this together instead

The compensating controls are real, and they are the reason the trade works:

- **Everything is defined in code.** Every device, service and segment is declared in
  inventory and applied by automation, so a lost device is rebuilt rather than repaired.
  Compute hosts are explicitly [stateless](/docs/architecture/substrate/compute/).
- **Identity is allocated, not discovered.** VMID → MAC → DHCP reservation → DNS record is a
  chain derived from inventory, so a rebuilt host comes back *as itself* rather than as a new
  machine that happens to do the same job.
- **The provisioner is portable and replaceable.** The builder carries its own artifacts, Git
  mirrors and boot infrastructure, provisions any site it is attached to, and is defined as a
  role any suitable host can assume. This is the mechanism behind *rebuild, not failover* —
  without it the rest of this page would be much harder to accept.
- **Recovery is documented per device.** [Console Recovery](/docs/runbook/console-recovery/)
  covers the router, the hypervisors, the switch and the AP, including which cable each needs.
- **The blast radius is understood.** [Network segmentation](/docs/architecture/network-segmentation/)
  bounds what a compromised or misbehaving segment can reach, which matters more when there is
  no redundancy to absorb a mistake.

The honest summary: **Deevnet is designed to be rebuilt quickly, not to stay up through a
failure.** Recovery time is a rebuild, and for a lab that is the right trade — as long as it
is a choice rather than a surprise.

## What it would take to lift each limit

| Limit | What would change it |
|---|---|
| No out-of-band management | Different hardware — server boards with BMCs, or a networked KVM/serial console server |
| Nothing clustered | A third node for quorum, plus shared storage worth failing over to |
| Local storage only | The shared storage already scoped in [Substrate Storage](/docs/architecture/substrate/storage/) |
| Single core router | A second appliance and a CARP pair, with the state sync that implies |
| Single switch / single-homed hosts | A second switch, second NICs, and LACP or MLAG |
| Rebuild path collapses to one physical node | A second detachable builder — the provisioner is already a role, so this is hardware rather than design |
| Single Omada controller | A second controller instance, or accepting that device management is best-effort |
| One populated site | Hardware in `home`, which the inventory skeleton is already shaped for |
| On-box backups only | Off-box config backup automation — the smallest item on this list, and the one with the best return |
