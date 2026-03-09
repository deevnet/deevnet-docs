---
title: "Addressing"
weight: 2
---

# Addressing

Defines the IP addressing convention for Deevnet sites.

---

## Addressing Convention

Each site is assigned a /16 block from the 10.0.0.0/8 RFC1918 space:

| Site | Site ID | Address Block |
|------|---------|---------------|
| **dvnt** | 10 | 10.10.0.0/16 |
| **dvntm** | 20 | 10.20.0.0/16 |

The addressing pattern is: `10.{site_id}.{vlan_id}.0/24`

- The second octet identifies the site
- The third octet matches the VLAN ID for that segment
- Each segment subnet is a /24 within the site's /16

This creates a predictable, self-documenting address scheme where any IP immediately reveals which site and segment it belongs to.

---

## Gateway Convention

Each subnet uses `.1` as the gateway address:

- `10.10.30.1` — dvnt IoT segment gateway
- `10.20.99.1` — dvntm management segment gateway

---

## Host Addressing Ranges

| Range | Purpose |
|-------|---------|
| .1 | Gateway (core router VLAN interface) |
| .2-.49 | Static infrastructure hosts |
| .50-.59 | Tenant-reserved addresses |
| .60-.69 | Reserved for future use |
| .70-.79 | Experimental/lab use |
| .100-.200 | DHCP dynamic pools (where applicable) |

Infrastructure hosts (routers, hypervisors, provisioners, switches, APs) receive static assignments in the low range. DHCP pools are used for segments with dynamic devices (trusted, IoT, guest).

---

## WAN Operation Modes

The dvntm site operates in two WAN modes depending on physical location:

### Travel Mode

dvntm operates behind `edge-rt01` (travel router) with outbound NAT to upstream networks (hotel, tethered phone, etc.).

- `edge-rt01` WAN: DHCP from upstream
- `edge-rt01` LAN: 192.168.8.0/24 (unchanged, travel-router-local)
- All dvntm traffic NATs through `edge-rt01`

### Home Dock Mode

When dvntm is co-located with dvnt, the dvntm WAN connects to dvnt's trusted segment:

- dvntm WAN IP: assigned from 10.10.10.0/24 (dvnt trusted)
- dvnt routes 10.20.0.0/16 to dvntm's WAN IP
- NAT is disabled on dvntm's WAN — traffic flows with clean source IPs
- Both sites can communicate with full visibility

This allows dvntm devices to be reachable from dvnt without double-NAT, while dvntm retains its own addressing and can undock at any time.

---

## Reserved VLAN Ranges

| VLAN Range | Purpose |
|------------|---------|
| 10-40 | Core segment types (trusted, storage, platform, IoT, guest) |
| 50-59 | Tenant segments |
| 60-69 | Reserved for future segment types |
| 70-79 | Experimental/lab segments |
| 99 | Management |
