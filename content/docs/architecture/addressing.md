---
title: "Addressing"
weight: 4
---

# Addressing

Defines the IP addressing convention for Deevnet sites.

---

## Addressing Convention

Each site is assigned a /16 block from the 10.0.0.0/8 RFC1918 space:

| Site | Address Block |
|------|---------------|
| **home** | 10.10.0.0/16 |
| **mobile** | 10.20.0.0/16 |

The addressing pattern is: `10.{site_id}.{vlan_id}.0/24`

- The second octet identifies the site
- The third octet matches the VLAN ID for that segment
- Each segment subnet is a /24 within the site's /16

This creates a predictable, self-documenting address scheme where any IP immediately reveals which site and segment it belongs to.

### Splitting the site block

The pattern above describes **substrate segments**, where the third octet is a VLAN ID. Tenant
overlays are not VLANs, so they cannot be described by it. Each site's `/16` is therefore split,
per [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/):

| Block (mobile) | Purpose |
|---------------|---------|
| `10.20.0.0/17` | Substrate segments — third octet = VLAN ID, as above |
| `10.20.128.0/18` | Tenant overlay subnets — `10.20.{128+n}.0/24` for tenant index `n` |
| `10.20.255.0/24` | Tenant fabric loopbacks / VTEP identity |

home mirrors this in `10.10.0.0/16`. Keeping tenants inside the site block means there is still
exactly **one aggregate per site** to route — which matters in home dock mode, where home already
routes `10.20.0.0/16` to mobile and that route keeps covering tenants unchanged.

So the third octet also tells you which side of the line an address is on: below `128` is a
substrate segment, `128` and above is a tenant overlay.

---

## Gateway Convention

Each subnet uses `.1` as the gateway address:

- `10.10.30.1` — home IoT segment gateway
- `10.20.99.1` — mobile management segment gateway

---

## Host Addressing Ranges

| Range | Purpose |
|-------|---------|
| .1 | Gateway (core router VLAN interface) |
| .2-.49 | Static infrastructure hosts |
| .50-.59 | Tenant-reserved addresses |
| .60-.69 | Reserved for future use |
| .70-.79 | Experimental/lab use — `.79` is the transient image-build address (see [tenant hypervisors](/docs/platforms/tenant-compute/tenant-hypervisors/)) |
| .100-.200 | DHCP dynamic pools (where applicable) |

Infrastructure hosts (routers, hypervisors, provisioners, switches, APs) receive static assignments in the low range. DHCP pools are used for segments with dynamic devices (trusted, IoT, guest).

---

## WAN Operation Modes

The mobile site operates in two WAN modes depending on physical location:

### Travel Mode

mobile operates behind `edge-rt01` (travel router) with outbound NAT to upstream networks (hotel, tethered phone, etc.).

- `edge-rt01` WAN: DHCP from upstream
- `edge-rt01` LAN: 192.168.8.0/24 (unchanged, travel-router-local)
- All mobile traffic NATs through `edge-rt01`

### Home Dock Mode

When mobile is co-located with home, the mobile WAN connects to home's trusted segment:

- mobile WAN IP: assigned from 10.10.10.0/24 (home trusted)
- home routes 10.20.0.0/16 to mobile's WAN IP
- NAT is disabled on mobile's WAN — traffic flows with clean source IPs
- Both sites can communicate with full visibility

This allows mobile devices to be reachable from home without double-NAT, while mobile retains its own addressing and can undock at any time.

---

## Reserved VLAN Ranges

| VLAN Range | Purpose |
|------------|---------|
| 10-40 | Core segment types (trusted, storage, platform, IoT, guest) |
| 50-59 | Tenant fabric transport (transit, underlay) — *not* a network per tenant |
| 60-69 | Reserved for future segment types |
| 70-79 | Experimental/lab segments |
| 99 | Management |
