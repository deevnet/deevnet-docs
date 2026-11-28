---
title: "ADR-0047: Mobile-to-Home Site Link"
weight: -47
---

# ADR-0047: The Mobile Site Reaches Home's Block From the Operator's Seats, by a Declared One-Way Link

|  |  |
|--|--|
| **Status** | Proposed (2026-11-28) |
| **Date** | 2026-11-28 |
| **Scope** | Traffic from the mobile site to the home site: which mobile zones may start it, which home networks it may reach, how it is routed, and how the hosts and clients that need it are told. Not home's own policy for what it accepts from mobile, which is home's to declare once home is built; not traffic from home to mobile, which this record does not allow |
| **Related** | [Naming and Addressing → WAN Operation](/docs/architecture/naming-and-addressing/#wan-operation) (*"Linking the sites is a decision … made as a declared site link with its own policy"*), [Network Segmentation standard → Site Independence](/docs/standards/network-segmentation/#site-independence), [CHG-0023](/docs/changes/2026/0023-internet-means-internet/) (the wide internet rule trusted and management kept), [Declarative Reconciliation plan](/docs/roadmap/infrastructure/substrate/reconciliation/plan/#settings-that-exist-only-in-the-running-config-) (the trusted subnet's classless route), [Home Site](/docs/roadmap/site-work/home-site/) and [CHG-0057](/docs/changes/2026/0057-build-the-home-site/) (the Builder builds home from mobile, over this link) |

---

## Context

**Mobile is the contractor van.** The mobile kit travels, and one of the places it goes is home:
it is meant to carry out deployments and maintenance there, the way a contractor's van brings
its tools to a site. That needs the operator, at a mobile seat, to reach home's networks:
`192.168.2.0/24`, the home network as it is today, and `10.10.0.0/16`, the block
[Naming and Addressing](/docs/architecture/naming-and-addressing/) reserves for the home site once it is
built.

**The architecture says no such path exists.** Naming and Addressing says *"There is no
connectivity between sites … Linking the sites is a decision for when there is a reason to, and
would be made as a declared site link with its own policy."* The contractor van is that reason,
and this record is that decision. Building home depends on it: in
[CHG-0057](/docs/changes/2026/0057-build-the-home-site/) the Builder comes home and applies the
home site from mobile.

**The path works today, but only by accident, in four undeclared pieces:**

| Piece | Where | What it does |
|---|---|---|
| Firewall | trusted's and management's internet rules pass to `!10.20.0.0/16` (CHG-0023 kept them wide, for the edge router's admin) | Lets both home networks through, because they are outside mobile's block. Nothing says they may be reached; narrowing the internet rule, as CHG-0023 did for every other zone, would cut the van off without anyone deciding to |
| Routing | none on the core router; traffic leaves by the default route, NATed to the WAN address | Reaches `192.168.2.0/24` when the van's upstream is the home network. Reaches `10.10.0.0/16` only if the upstream routes it, and nothing declares that it does |
| Builder | `10.10.0.0/16 via 10.20.99.1` on `dv00bld001p01` (`mobile/host_vars/dv00bld001p01.yml`) | Keeps the Builder's home traffic on the management NIC rather than its transit NIC's default route. Declared, but on one host and with no decision behind it |
| Operator clients | `option_data.classless_static_route` `10.0.0.0/8 - 10.20.10.1` on the trusted subnet, set by hand and in no declaration | Option 121 for laptops on `DVNTM`: Deevnet space through the mobile router, even for a laptop that is also on another network. Its likely origin is a laptop on both `DVNTM` and the home network sending home traffic out the wrong way. It carries no default entry, and RFC 3442 tells a client that receives option 121 to ignore option 3 (the router), so a strict client may be left with no default route |

**Each site must stand on its own.** The Network Segmentation standard says cross-site
communication *"MUST traverse external routing"* and allows *"No implicit dependencies between
site segments"*. A link that runs over the upstream, through each site's own edge, keeps to both;
a tunnel or a shared segment would not.

## Options considered

**A. Leave it as it is.** The van works today. But it works because of a rule kept wide for another
reason, a route on one host and a DHCP option no one wrote down, and the first person to tidy any
of them breaks it without knowing. Rejected.

**B. No link: the van's operator works on home from a home seat.** Keeps the sites fully apart, and
defeats the purpose of the van, whose tools (the Builder, the control node, the inventory) are on
mobile. Rejected.

**C. A tunnel between the two core routers.** Routes both blocks without depending on the upstream,
and works from anywhere the van is. It is also a cross-site dependency the standard rules out, a
second path that has to be secured and watched, and more than "the van is parked at home" needs.
Not now; a later record can choose it if the van has to reach home from elsewhere.

**D. A declared one-way link over the upstream.** Name home's networks once, let the operator's
zones reach them by a rule of their own, route them out the WAN as today, and tell the hosts and
clients that need it from inventory. The pieces that exist become declarations, and the internet
rule can then be narrowed without cutting the van off. **Chosen.**

## Decision

### 1. Home's networks are named once

Mobile's inventory names the networks of the home site as one list, `10.10.0.0/16` and
`192.168.2.0/24`, and the core router holds them as one alias, `deevnet_home`. Every rule and route
in this record refers to the alias or the list, never to an address. When home is built and the
home network moves into `10.10.0.0/16`, the list changes and nothing else does.

### 2. Only the operator's seats start it

Mobile's **management** and **trusted** zones may reach `deevnet_home`, on any port: these are the
seats deployments and maintenance are done from, and they already reach every mobile segment. No
other mobile zone may: guest, IoT, platform and the tenants keep "internet means internet"
(CHG-0023), and `deevnet_private` covers both home networks for them.

The permission is its own rule on each of the two zones, ahead of the internet rule, named for this
record. It does not ride on the internet rule. Trusted's and management's internet rules may then
be narrowed to `!deevnet_private`, with an explicit pass for the upstream equipment those seats
administer, without touching the van (§6).

### 3. One way only

Nothing on mobile accepts a connection started from home. Replies to the van's own connections
return by the router's state, as every outbound connection's do. Home reaching mobile is a separate
decision.

### 4. Over the upstream, through each site's own edge

Traffic to `deevnet_home` leaves mobile's core router by its WAN, NATed to the WAN address, as all
outbound traffic does now. Home sees the van as one client of its network. For
`192.168.2.0/24` that is all it takes when the van's upstream is the home network. For
`10.10.0.0/16`, once home is built, either the upstream routes the block to home's core router or
mobile's core router gets a declared static route to home's core router's upstream address
(open question 1). Nothing turns NAT off and nothing renumbers.

### 5. Hosts and clients are told from inventory

- **Dual-homed mobile hosts**, such as the Builder with its transit NIC, carry a route for each
  network in the list via their management gateway, rendered from the list rather than written per
  host.
- **Operator clients** on trusted (and on management, if it serves DHCP clients) get option 121
  declared on the VLAN in `deevnet_vlans` and converged by `opnsense_dhcp`. That means mobile's own
  block, each home network, and a default entry, all via the subnet's gateway. The default entry
  keeps a strict client's default route (open question 2). The hand-set `10.0.0.0/8` value is
  replaced by the declared one.

### 6. The wide internet rule closes once the link is declared

`firewall_internet_private_zones` exists so the operator's seats can reach private space upstream.
With §2 in place, its remaining use is the upstream equipment those seats administer, such as the
edge router's admin. That becomes an explicit, named pass, and the two zones join every other on
`!deevnet_private`.

## Consequences

- The van's access to home is a decision with a name, so changing it is a change, not a tidy-up.
- `192.168.2.0/24` is a common network number. When the van is parked somewhere whose network uses
  it too, §2 lets the operator's seats reach *that* network. Today's wide rule already does, so
  this is no worse, but it is now visible (open question 3).
- Option 121 on trusted becomes something inventory controls, so a client that loses its default
  route over it is found from a declaration, not by guessing at the router.
- The architecture pages change: Naming and Addressing's WAN Operation names this link as the one
  exception to "no site routes to another", and the Network Segmentation pages list the rule.

## To accept

**This record is accepted when every item below is done.**

- [ ] The scope agreed: management and trusted to `10.10.0.0/16` and `192.168.2.0/24`, one way, over the upstream (2026-11-28, the owner)
- [ ] Open questions 1–3 answered
- [ ] `deevnet_home` declared in mobile's inventory, held as an alias by `opnsense_firewall`, with a pass rule for management and for trusted, applied by change record
- [ ] Option 121 declared on trusted in `deevnet_vlans`, with the default entry, and converged by `opnsense_dhcp`; the hand-set `10.0.0.0/8` value replaced
- [ ] The Builder's home route rendered from the list
- [ ] Trusted and management moved to `!deevnet_private` with an explicit pass for the upstream equipment they administer, and checked from a seat parked at home: `192.168.2.0/24` answers from trusted and management, and not from guest
- [ ] Naming and Addressing and the Network Segmentation pages updated

## Open questions

1. **How does `10.10.0.0/16` get to home's core router?** Through the upstream's routing, or by a
   static route on mobile's core router that only works while the van is parked at home? This is
   not needed until home is built. *Recommendation:* a static route, declared with the other
   gateways, with no monitoring and never the default, the same as `TENANT_FABRIC_GW`. Out of
   home, it points at nothing and does no harm.
2. **Should option 121 carry a default entry?** With it, a laptop that is also on the home network
   gets two default routes and picks one by metric. Without it, a strict client on `DVNTM` alone
   may lose its default. *Recommendation:* carry it. First check what clients on `DVNTM` get
   today: `ip route` or `netstat -rn -f inet` from a laptop on `DVNTM` alone.
3. **Should the link only work at home?** `192.168.2.0/24` at another venue is someone else's network.
   The rule could be limited to times when the WAN's own address is in the home network, or
   `192.168.2.0/24` could drop out of the list once home is built. *Recommendation:* drop it once home is
   built, and until then accept the same exposure the wide rule has today.
