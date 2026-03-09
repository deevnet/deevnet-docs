---
title: "Networking"
weight: 1
---

# Substrate Networking

Defines the network segmentation model for Deevnet sites.

---

## Purpose

Network segmentation divides each substrate into isolated broadcast domains with controlled routing between them. This provides:

- **Security boundaries** — Limit blast radius when devices are compromised
- **Traffic isolation** — Separate management, storage, and workload traffic
- **Operational clarity** — Each segment has a defined purpose and trust level

---

## Segment Model

Each substrate implements nine segment types:

| Segment | Purpose | Trust Level |
|---------|---------|-------------|
| Management | Infrastructure management plane | High |
| Trusted | High-trust user devices | High |
| Storage | Dedicated storage traffic | High |
| Platform | Shared infrastructure services | High |
| Tenant | Per-tenant workload isolation | Medium |
| IoT Vendor | Vendor-managed/untrusted IoT containment | Very Low |
| IoT | Custom-developed embedded devices with controlled firmware | Medium |
| IoT Backend | IoT application backends | Medium |
| Guest | Transient visitor access | Untrusted |

### Management Segment

The management segment carries infrastructure control traffic.

**Typical inhabitants:**
- Builder (`provisioner-ph01`)
- Hypervisor management interfaces (`hv01-mgmt`, `hv02-mgmt`)
- Router management interfaces (`core-rt01-mgmt`)
- Switch management interfaces (`sw01-mgmt`)
- IPMI/BMC interfaces (`hv01-ipmi`)

**Properties:**
- Full access to all infrastructure
- Source of Ansible automation
- Never exposed to untrusted networks

### Trusted Segment

The trusted segment contains high-trust user devices that require broad network access but are not part of the infrastructure management plane.

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
- Optional in minimal sites where storage traffic is negligible

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

### Platform Segment

The platform segment contains shared infrastructure services that multiple segments need to access.

**Typical inhabitants:**
- DNS resolvers (`dns01`, `dns02`)
- NTP servers
- Artifact mirrors and package caches
- Reverse proxy / load balancer
- Certificate authority

**Properties:**
- Reachable from management, trusted, tenant, and IoT backend segments
- High trust — hosts are fully managed infrastructure
- Static DHCP only
- No direct user workloads
- Services are shared, not tenant-specific

### IoT Vendor Segment

The IoT vendor segment is a strict containment zone for vendor-managed devices that phone home to cloud services and cannot be fully audited.

**Typical inhabitants:**
- Smart home hubs with vendor cloud dependencies
- IP cameras with vendor firmware
- Consumer IoT devices (smart plugs, thermostats)
- Any device where firmware updates are vendor-controlled

**Properties:**
- Outbound internet access only (for vendor cloud connectivity)
- Complete isolation from all internal segments — stricter than IoT
- No inbound access from any segment
- Devices are assumed compromised by default
- Cannot reach management, storage, tenant, or platform segments

### IoT Segment

The IoT segment contains custom-developed embedded devices with controlled firmware. Unlike the IoT Vendor segment, these devices run firmware that is built, managed, and updated through the Deevnet automation pipeline.

**Typical inhabitants:**
- Raspberry Pis (`pi01`, `pi02`, `pi03`)
- Embedded devices (`em01`, `em02`)
- SDR receivers (e.g., `sdr.dvntm.deevnet.net` → `pi01`)
- Sensors and IoT gateways

**Properties:**
- Medium trust — firmware is custom-developed and controlled
- Outbound internet access (controlled)
- Limited or no access to management segment
- May need access to specific tenant services

### IoT Backend Segment

The IoT backend segment hosts application backends that process IoT data — MQTT brokers, home automation controllers, and data pipelines.

**Typical inhabitants:**
- MQTT brokers (`mqtt01`)
- Home Assistant instances
- IoT data ingestion and processing services
- Time-series databases for sensor data

**Properties:**
- Accepts inbound connections from IoT segment (sensor data, MQTT publish)
- May access platform segment (DNS, NTP, artifact mirrors)
- Must not access management segment directly
- Medium trust — hosts are managed but handle untrusted input
- Static DHCP only

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

{{< mermaid >}}
graph TB
    subgraph high["High-trust segments"]
        Mgmt[Management<br>High Trust]
        Trusted[Trusted<br>High Trust]
    end

    Mgmt -->|manages| Storage[Storage<br>High Trust]
    Mgmt -->|manages| Platform[Platform<br>High Trust]
    Mgmt -->|manages| Tenant[Tenant Segments<br>Medium Trust]
    Mgmt -->|manages| IoTBackend[IoT Backend<br>Medium Trust]
    Mgmt -->|manages| IoT[IoT<br>Medium Trust]
    Mgmt -->|manages| IoTVendor[IoT Vendor<br>Very Low Trust]
    Trusted -->|user access| Storage
    Trusted -->|user access| Platform
    Trusted -->|user access| Tenant
    Trusted -->|user access| IoTBackend
    Trusted -->|user access| IoT

    IoT -->|sensor data| IoTBackend
    IoTBackend -->|shared services| Platform

    Tenant -.->|no access| Guest[Guest<br>Untrusted<br>Internet only]
    IoTVendor -.->|internet only| Guest
{{< /mermaid >}}

### Default Routing Policy

- **Default deny** — Traffic between segments is blocked unless explicitly allowed
- **Management can reach all** — Management segment initiates connections to all others
- **Trusted has broad access** — Trusted segment can reach most segments except guest; similar to management but for user devices
- **Storage is isolated** — Only management, trusted, and designated compute hosts access storage
- **Tenants are isolated** — Tenants cannot see each other; access shared services via firewall rules
- **IoT is outbound-only** — IoT devices can reach internet; inbound requires explicit rules
- **Platform is broadly reachable** — Management, trusted, tenant, and IoT backend segments can reach platform services
- **IoT Vendor is fully contained** — Outbound internet only; no access to any internal segment
- **IoT Backend accepts IoT traffic** — Inbound from IoT, outbound to platform; no direct management access
- **Guest has no substrate access** — Guest segment routes only to internet gateway

---

## Integration with Substrate Model

Network segmentation is substrate-scoped:

- Each site (dvnt, dvntm) implements segmentation independently
- No cross-site segment dependencies
- The same segment model applies to all sites
- Implementation details (VLAN IDs, IP ranges) vary per site

This aligns with the site independence principle — each site can be built, operated, and torn down without affecting the other.

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

The transition is explicit — segment configuration is part of the authority handoff from builder to core router.

---

## Summary

1. Sites use nine segment types: Management, Trusted, Storage, Platform, Tenant, IoT Vendor, IoT, IoT Backend, Guest
2. Segments form a trust hierarchy with default-deny routing between them
3. Each site implements segmentation independently
4. Core router provides VLAN routing, firewall zones, and per-segment DHCP
5. Bootstrap mode uses flat networking; production mode uses full segmentation
