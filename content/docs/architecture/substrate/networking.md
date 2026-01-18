---
title: "Networking"
weight: 1
---

# Substrate Networking

Defines the network segmentation model for Deevnet substrates.

---

## Purpose

Network segmentation divides each substrate into isolated broadcast domains with controlled routing between them. This provides:

- **Security boundaries** — Limit blast radius when devices are compromised
- **Traffic isolation** — Separate management, storage, and workload traffic
- **Operational clarity** — Each segment has a defined purpose and trust level

---

## Segment Model

Each substrate implements six segment types:

| Segment | Purpose | Trust Level |
|---------|---------|-------------|
| Management | Infrastructure control plane | High |
| Trusted | High-trust user devices | High |
| Storage | Dedicated storage traffic | High |
| Tenant | Per-tenant workload isolation | Medium |
| IoT | Untrusted/embedded devices | Low |
| Guest | Transient visitor access | Untrusted |

### Management Segment

The management segment carries infrastructure control traffic.

**Typical inhabitants:**
- Bootstrap node (`provisioner-ph01`)
- Hypervisor management interfaces (`hv01-mgmt`, `hv02-mgmt`)
- Router management interfaces (`core-rt01-mgmt`)
- Switch management interfaces (`sw01-mgmt`)
- IPMI/BMC interfaces (`hv01-ipmi`)

**Properties:**
- Full access to all infrastructure
- Source of Ansible automation
- Never exposed to untrusted networks

### Trusted Segment

The trusted segment contains high-trust user devices that require broad network access but are not part of the infrastructure control plane.

**Typical inhabitants:**
- Personal workstations (`ws01`, `ws02`)
- Laptops and primary user devices
- Multi-homed desktops with access to multiple segments

**Properties:**
- High trust level, similar to management
- Can initiate connections to most segments (except guest)
- May access management services for administration
- Users are authenticated and devices are known/managed
- Subject to endpoint security requirements

### Storage Segment

The storage segment isolates storage protocol traffic from other network activity.

**Typical inhabitants:**
- NAS storage interfaces (`nas-ph01-stor`)
- Hypervisor storage interfaces (`hv01-stor`, `hv02-stor`)
- Backup target interfaces (`backup-vm01-stor`)

**Properties:**
- High-bandwidth, low-latency requirements
- May use jumbo frames
- No internet access required
- Optional in minimal substrates where storage traffic is negligible

### Tenant Segments

Tenant segments provide network isolation between workload namespaces. Each tenant gets its own segment.

**Typical inhabitants:**
- Tenant VMs (e.g., `app-vm01` hosting `api.grooveiq.dvntm.deevnet.net`)
- Tenant containers
- Tenant application endpoints

**Properties:**
- One segment per tenant namespace
- Cannot see other tenants' traffic
- Access to shared services via explicit firewall rules
- Each tenant segment has its own DHCP scope

See [Tenant Networking](/docs/architecture/tenant/networking/) for tenant-specific network architecture.

### IoT Segment

The IoT segment isolates embedded and less-trusted devices that may have limited security capabilities.

**Typical inhabitants:**
- Raspberry Pis (`pi01`, `pi02`, `pi03`)
- Embedded devices (`em01`, `em02`)
- SDR receivers (e.g., `sdr.dvntm.deevnet.net` → `pi01`)
- Sensors and IoT gateways
- Smart home devices

**Properties:**
- Devices may have vulnerabilities or limited patching
- Outbound internet access (controlled)
- Limited or no access to management segment
- May need access to specific tenant services

### Guest Segment

The guest segment provides network access for transient devices without substrate access.

**Typical inhabitants:**
- Visitor laptops and phones
- Demo equipment
- Temporary test devices

**Properties:**
- Internet access only
- Complete isolation from all other segments
- Dynamic DHCP only (no static mappings)
- May have bandwidth or time limits

---

## Segment Relationships

Segments form a trust hierarchy with controlled routing between them:

```
┌─────────────────────┐   ┌─────────────────────┐
│     Management      │   │       Trusted       │  ← High-trust segments
│    (High Trust)     │   │    (High Trust)     │
└──────────┬──────────┘   └──────────┬──────────┘
           │ manages                 │ user access
           └────────────┬────────────┘
                        │
     ┌──────────────────┼──────────────────┐
     ▼                  ▼                  ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│      Storage      │ │  Tenant Segments  │ │        IoT        │
│   (High Trust)    │ │  (Medium Trust)   │ │   (Low Trust)     │
└───────────────────┘ └───────────────────┘ └───────────────────┘
                               │
                          no access
                               │
                    ┌──────────▼──────────┐
                    │        Guest        │  ← Internet only
                    │    (Untrusted)      │
                    └─────────────────────┘
```

### Default Routing Policy

- **Default deny** — Traffic between segments is blocked unless explicitly allowed
- **Management can reach all** — Management segment initiates connections to all others
- **Trusted has broad access** — Trusted segment can reach most segments except guest; similar to management but for user devices
- **Storage is isolated** — Only management, trusted, and designated compute hosts access storage
- **Tenants are isolated** — Tenants cannot see each other; access shared services via firewall rules
- **IoT is outbound-only** — IoT devices can reach internet; inbound requires explicit rules
- **Guest has no substrate access** — Guest segment routes only to internet gateway

---

## Integration with Substrate Model

Network segmentation is substrate-scoped:

- Each substrate (dvnt, dvntm) implements segmentation independently
- No cross-substrate segment dependencies
- The same segment model applies to all substrates
- Implementation details (VLAN IDs, IP ranges) vary per substrate

This aligns with the substrate independence principle — each substrate can be built, operated, and torn down without affecting the other.

---

## Core Router Integration

The core router serves as the segment router and firewall for each substrate:

| Function | Role |
|----------|------|
| VLAN interfaces | One interface per segment |
| Inter-segment routing | Controlled routing between segments |
| Firewall zones | Segment-based policy enforcement |
| DHCP scopes | Per-segment address pools |
| DNS | Authoritative for substrate zone |

### Firewall Zone Model

Each segment maps to a firewall zone with distinct rulesets:

- **MGMT zone** — Permissive outbound, restricted inbound
- **STOR zone** — Highly restricted, only designated hosts
- **TENANT zones** — Per-tenant rules, shared service access
- **IOT zone** — Outbound allowed, inbound restricted
- **GUEST zone** — Internet gateway only

---

## Authority Modes and Segmentation

Segmentation behavior differs between authority modes:

| Mode | Segmentation |
|------|--------------|
| Bootstrap-authoritative | Flat network (single segment) for initial provisioning |
| Router-authoritative | Full segmentation with VLAN isolation |

During bootstrap, the provisioner operates on a flat network to PXE boot and configure hosts. Once the core router is configured with VLAN interfaces and the switch is configured for trunking, the substrate transitions to full segmentation.

The transition is explicit — segment configuration is part of the authority handoff from bootstrap node to core router.

---

## Summary

1. Substrates use six segment types: Management, Trusted, Storage, Tenant, IoT, Guest
2. Segments form a trust hierarchy with default-deny routing between them
3. Each substrate implements segmentation independently
4. Core router provides VLAN routing, firewall zones, and per-segment DHCP
5. Bootstrap mode uses flat networking; production mode uses full segmentation
