---
title: "ADR-0019: Tenant Layer 2 at the Access Edge"
weight: 19
---

# ADR-0019: Tenant Layer 2 at the Access Edge

|  |  |
|--|--|
| **Status** | Accepted |
| **Accepted** | 2026-09-19. It decides *not* to build something, so there is no implementation to wait for. Its one open question was closed by reasoning rather than by experiment — see [The open question, closed](#the-open-question-closed) — and its reconsideration trigger was corrected, because the protocols it first named do not in fact require Layer 2 adjacency. |
| **Date** | 2026-09-18 |
| **Scope** | Whether a tenant's EVPN/VXLAN overlay may be extended to the wireless access network as an 802.1Q VLAN, so that a physical device becomes a Layer 2 member of its tenant's subnet |
| **Re-opens** | [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) Option B, rejected 2026-09-15, in the light of a variation it did not consider: a VLAN range reserved once, so tenant creation needs no switch change |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) |
| **Related** | [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/), [ADR-0009: Network Device Configuration Is Inventory-Owned](/docs/architecture/decisions/0009-network-device-config-ownership/), [ADR-0012: IoT Platform Services Through a Deevnet API](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/0018-operator-access-to-tenants/), [Network Segmentation](/docs/standards/network-segmentation/) §4 |

---

## Context

[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) settled where a
physical device attaches: the access network of its **trust class**, not its owner's tenant fabric.
Its Option B — a per-tenant edge VLAN carried over the AP trunk and bridged into the tenant's VRF —
was rejected on 2026-09-15, and [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) then
built the accepted model: one PPSK key per tenant per trust class, bound by the Deevnet API to that
class's VLAN.

Two things have changed since, and both deserve to be weighed rather than waved off.

**A variation Option B never considered.** Option B was costed as *"every tenant needs edits to two
switch trunks."* But the physical network could instead reserve a VLAN range **once** — say
130–191, with the hypervisor-facing and AP-facing ports permanently trunked for it — and tenant
provisioning would allocate from that pool entirely through automation. Under that variation the
switch configuration never changes after initial setup. This is a materially different proposition
from the one rejected, and it is the question this record was opened to answer.

**The VLAN would not be a tenant network.** In [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)'s
rejected Option A, the VLAN *was* the tenant: the core router owned its gateway, DHCP and firewall.
Here the VLAN would carry no gateway, no DHCP scope and no router interface. It would be a last-mile
access encapsulation for one Layer 2 segment whose authority stays in the overlay. That distinction
is real, and no existing record addresses it.

### What was verified before deciding

This record rests on reading the Proxmox source rather than inferring from behavior. Unless marked
otherwise, each statement below was read from
[`EvpnPlugin.pm`](https://git.proxmox.com/?p=pve-network.git;a=blob_plain;f=src/PVE/Network/SDN/Zones/EvpnPlugin.pm;hb=HEAD)
or from this estate's own code.

| Fact | Source |
|---|---|
| A VNet bridge's ports are generated as `bridge_ports vxlan_<vnetid>` — the VXLAN interface, and nothing else | `EvpnPlugin.pm` `generate_sdn_config` |
| The EVPN zone plugin has **no `dhcp` option**. It is present for Simple zones | `EvpnPlugin.pm` `sub options` |
| Proxmox SDN implements **no EVPN multihoming** — no ESI, no Ethernet Segment, no RFC 7432 Type-4 routes | `EvpnPlugin.pm`, searched |
| VXLAN MTU is the physical MTU − 50, defaulting to 1450 | `EvpnPlugin.pm` MTU computation |
| `bridge-learning off` is set unconditionally on the VXLAN interface; remote MACs come from FRR | `EvpnPlugin.pm` |
| The node's SDN config is generated into `/etc/network/interfaces.d/sdn` and reloaded with ifupdown2 | [pve-docs, SDN](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html) |
| The API creates a tenant zone as `type=evpn` with `vrf-vxlan`, one VNet with a `tag`, and one subnet with `snat=1` | `deevnet-provisioning-api` `internal/backend/proxmox/network.go` |
| A tenant's Wi-Fi key takes its VLAN from the **trust class**, never from the request | `internal/tenant/wifikeys.go` |
| `deevnet_vlans` is the single declaration driving `switch_vlans`, `opnsense_vlans` **and** `opnsense_dhcp` | `ansible-collection-deevnet.net` |
| `dv02hyp002p02` is single-NIC; `vmbr0` is VLAN-aware with `vids: "2-4094"` | `host_vars/dv02hyp002p02/vars.yml` |

For tenant `eds` (index 2) the concrete objects are zone `eds` (`vrf-vxlan 10002`), VNet `eds0`
(tag `20020`), subnet `10.20.130.0/24` with anycast gateway `.1`, and the generated devices
`eds0`, `vxlan_eds0`, `vrf_eds`, `vrfbr_eds`, `vrfvx_eds`.

---

## Options considered

### A — Keep the broker model *(the accepted model)*

A device attaches to its trust class's VLAN and reaches tenant workloads through scoped platform
services: a PPSK key on `DVNTM-IOT`, a broker account, per-topic ACLs under the tenant's prefix.

- **Pros:** needs no VLAN, no switch change, no node-local state, no record superseded. Works for
  tenantless applications. The device survives `dv02hyp002p02` being down, and stays reachable for
  diagnosis.
- **Cons:** devices of different owners share a Layer 2 domain, and the AP cannot separate them —
  the 2026-09-14 validation found no per-SSID client isolation outside Guest Network. Isolation
  between owners is a service-layer property, not a network one.

### B — Bridge the tenant VNet to an access VLAN

`vmbr0.130` is enslaved to the VNet bridge `eds0`. The station is a Layer 2 member of
`10.20.130.0/24` and uses the same anycast gateway as the tenant's workloads.

- **Pros:** the strongest form of the goal. The device is a genuine member of tenant space and can
  use Layer 2 discovery and multicast protocols directly.
- **Cons:**
  - **There is no supported attachment point.** The VNet bridge takes one generated port. Adding
    another is out-of-band kernel state that `interfaces.d/sdn` does not contain, so it is not
    reproduced by a rebuild and is subject to removal whenever the generator runs. Keeping it
    would require a daemon that re-adds the port after every SDN apply.
  - **No DHCP exists in the VNet.** EVPN zones have no DHCP option at all. A device would need a
    tenant-run DHCP server inside its own VNet, a static address in firmware, or a relay pointing
    out of the VRF — the last of which reintroduces the core router.
  - **Station-to-workload traffic is bridged, not routed.** It passes no VRF lookup, no firewall
    and no perimeter. The tenant's Layer 2 domain becomes reachable from the air.
  - **The MTU mismatch is invisible here.** 1450 against the station's 1500. On a single-member
    fabric nothing is encapsulated for this flow, so it works; it breaks when a second member joins.
  - **It cannot be made redundant.** Two hosts attaching the same VLAN to the same VNI is a bridged
    loop through the access switch. The correct answer is EVPN multihoming, which Proxmox does not
    implement.
  - **It inverts ADR-0011 §3**: attachment becomes a function of *owner* rather than *trust class*.

### C — Route the access VLAN into the tenant VRF

`vmbr0.130` holds an address inside `vrf_eds` on a separate subnet. The device is routed into tenant
space rather than bridged into it.

- **Pros:** avoids every Layer 2 hazard in B — no BUM flooding from the air into the VNI, no MTU
  trap, no duplicate MAC learning, no loop surface — and could be made redundant without an
  Ethernet Segment.
- **Cons:** still a VLAN per tenant, still node-local state Proxmox does not model, still
  attachment by owner. And it gives up the one thing B was for: the device is no longer on the
  tenant's subnet, so Layer 2 adjacency — the entire semantic gain — is lost. If adjacency is not
  needed, Option A already serves at lower cost.
- **Verdict:** strictly better than B *as an implementation*, but it pays B's architectural price
  for A's semantics.

### D — A VTEP-capable leaf switch

The AP hands 802.1Q to a switch that participates in EVPN and maps VLAN to VNI itself.

- **Pros:** the textbook design. The boundary sits in a device built to hold it, the hypervisor
  keeps its generated configuration untouched, and multihoming is available.
- **Cons:** the SG2218 cannot do this. It is a hardware purchase, and it moves the fabric edge off
  the hypervisor — a larger change to ADR-0001 than this record's question.
- **Verdict:** the right answer to the general problem; not available at this estate's hardware.

### E — Tunnel capable devices into tenant space

A device that can run WireGuard terminates a tunnel on a tenant workload and becomes a routed member
of tenant space.

- **Pros:** delivers genuine tenant membership with **no** substrate change — no VLAN, no switch
  edit, no node-local bridge, no record superseded. The estate has four Raspberry Pis that could do
  this today.
- **Cons:** does not help an ESP32-class device, which is most of what the IoT trust class holds.

---

## Decision

**Option A. The accepted model stands, and ADR-0011 §3 is reaffirmed: attachment is by trust class,
not by owner.**

This record does not supersede anything. It exists because the question was asked with a variation
worth taking seriously, and the reasoning that answers it should be written down rather than
re-derived the next time it comes up.

### What the variation genuinely fixed

The reserved-pool idea is a real improvement on the framing ADR-0011 rejected, and two of that
record's objections do not survive it:

1. **"Every tenant needs edits to two switch trunks."** Answered. A pool trunked once means tenant
   creation touches no switch configuration.
2. **"Devices inside a tenant are unreachable from management for diagnosis or recovery."** Largely
   answered by [ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/), which
   gives the core router one aggregate route to `10.20.128.0/18` from `management` and `trusted`. A
   device inside a tenant subnet would fall inside that aggregate. ADR-0018 is itself `Proposed`, so
   this relief is conditional on its acceptance.

Two further objections are **not differentiators**, because the accepted model carries them too:
PPSK is WPA2 on this AP either way, and the keys live in the controller's database either way.
CHG-0013 accepted both.

### What remains, and why it decides the question

1. **There is no supported path into an EVPN VNet, and no DHCP there.** Both verified from source.
   This is a property of the software the estate runs, not of the design, and no amount of
   pre-provisioning changes it.
2. **The boundary is node-local state that a rebuild does not reconstitute.** This is
   ADR-0001's build requirement #2 — *no hand-carried node state* — and the estate has already been
   bitten twice by the PVE network API dropping configuration it does not model.
3. **It cannot be made redundant, and it widens the failure domain.** Today an IoT device keeps its
   segment, gateway and internet path when `dv02hyp002p02` is down. Under B or C it does not.
4. **A tenant would still require a VLAN.** [Network Segmentation](/docs/standards/network-segmentation/)
   §4's MUST NOT has three clauses; the pool answers *switch change* and leaves *a VLAN* standing.
5. **Attachment by owner is the inversion ADR-0011 exists to prevent.** Ownership would confer
   network position regardless of what firmware a device runs, inside a Layer 2 domain the AP cannot
   police.

### The test that would change this answer

**A concrete requirement for Layer 2 adjacency** — not a preference for tidiness, and not a protocol
that merely *tends* to be deployed flat.

> **Corrected 2026-09-19.** This originally named **Art-Net and sACN (E1.31)** as the strongest
> examples, *"the multicast LED-control protocols"*. That is wrong, and it matters, because those
> are the protocols an LP-stand application would most plausibly reach for — a future reader could
> have re-opened this record on a false premise. **Both are routable.** sACN receivers are required
> by ANSI E1.31 to process unicast as well as multicast, and Art-Net supports unicast on UDP 6454;
> neither needs a shared Layer 2 domain, only IP connectivity. Correcting this makes the decision
> below **stronger**, not weaker: the set of requirements that genuinely force L2 extension is
> smaller than this record first claimed.

What genuinely does not cross a router is **link-local discovery**: mDNS (224.0.0.251, TTL 1) and
SSDP (239.255.255.250), and Matter commissioning insofar as it depends on mDNS. These are scoped to
the link by design rather than by convention.

Even those do not justify extending the fabric, because a **reflector** solves them — an
Avahi-style mDNS/SSDP repeater with a leg on each segment re-emits the announcements without
joining the two Layer 2 domains. That is cheaper than everything this record rejects, and it is the
first thing to reach for.

So the order of resort, if such a requirement appears:

1. **Reflect the discovery traffic.** A repeater on the two segments, with the services themselves
   reached by ordinary routed IP.
2. **Put the L2-dependent service adjacent to the devices** — on the IoT segment, with its control
   plane reached through a platform service
   ([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/)).
3. **Tunnel capable devices in** (Option E).
4. **Only then reconsider the network edge** — and prefer Option D over B or C, because the
   boundary belongs in a device designed to hold it.

A requirement survives to step 4 only if it is genuinely non-IP, or depends on link-local discovery
that a reflector cannot carry. None is known today.

---

## Consequences

### Positive

- The question is answered with verified facts rather than recollection, and the two objections the
  variation defeated are recorded as defeated rather than repeated.
- Three findings are now written down that no previous record held: EVPN zones have no DHCP option
  in the plugin's schema, Proxmox SDN has no EVPN multihoming, and the VXLAN MTU mismatch is
  invisible on a single-member fabric.
- The order of resort above means a future Layer 2 requirement has a cheaper first answer than
  rebuilding the access edge.

### Negative / accepted

- Cross-tenant isolation between **devices** remains a service-layer property. The AP cannot
  separate clients on one SSID, so two tenants' devices share a broadcast domain and are kept apart
  by per-device credentials and per-owner scopes, not by the network. This is an accepted cost of
  ADR-0011 Option C and this record does not improve it.
- A device still cannot use Layer 2 discovery to reach its tenant. Applications must be written to
  the broker.

### Neutral

- Nothing is built or unbuilt by this record. It closes a question.

---

## The open question, closed

**Would a manually added bridge port survive an SDN apply?** *Closed 2026-09-19, without running
the experiment.*

The draft recorded this as the last inference in the record and proposed a disposable test to
settle it. **The test is not worth running, and persistence was never the acceptance criterion.**

**It would not settle anything if it passed.** Suppose ifupdown2 does preserve the port across a
reload. The port still modifies **an object Proxmox's SDN generator owns and rewrites** — it is not
node state sitting *beside* the generated configuration, it is node state *contradicting* it. There
is no reconciliation for that: the generator's next authoritative render omits the port, so the
running state and the declared state disagree permanently and nothing in the estate can close the
gap. This is the same argument
[ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/) makes for network
devices — the question is who owns the object, not whether an edit happens to stick.

**The distinction matters, and a weaker version of this reasoning would be wrong.** "It isn't in
SDN configuration, therefore it fails the declarative requirement" proves too much:
[ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/) explicitly
refined ADR-0001's build requirement #2 to *no hand-carried node state*, **not** *no node state*,
and this estate legitimately carries Ansible-managed node-local state today — the forwarding
sysctl, the management-routing systemd unit, the agent-rendered FRR file. Node state beside the
generator is fine. Node state inside the generator's own object is not.

**And it would change nothing if it failed.** Option B is rejected on DHCP, on the absence of EVPN
multihoming, and on attachment-by-owner — each independently sufficient, none contingent on this
answer. The draft said as much: *"It does not change the decision."*

So the record carries one honest inference rather than a pending experiment: an out-of-band bridge
port is **expected** to be removed when the generator next runs, and it is **disqualified either
way**. If a future change ever needs the answer for another reason, the disposable procedure is in
this record's git history at `0838098`.
