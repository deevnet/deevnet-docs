---
title: "Network Segmentation"
weight: 5
---

# Network Segmentation

Defines the network segmentation model for Deevnet sites.

---

## Purpose

Network segmentation divides each substrate into isolated broadcast domains with controlled routing between them. This provides:

- **Security boundaries** — Limit blast radius when devices are compromised
- **Traffic isolation** — Separate management, storage, and workload traffic
- **Operational clarity** — Each segment has a defined purpose and trust level

---

## Segment Model

Each substrate implements ten segment types:

| Segment | Purpose | Trust Level |
|---------|---------|-------------|
| Management | Infrastructure management plane | High |
| Trusted | High-trust user devices | High |
| Storage | Dedicated storage traffic | High |
| Platform | Shared infrastructure services | High |
| Tenant transit | The fabric's perimeter handoff; per-tenant isolation lives in the fabric, not here | Medium |
| IoT Vendor | Vendor-managed/untrusted IoT containment | Very Low |
| IoT | Custom-developed embedded devices with controlled firmware | Medium |
| IoT Backend | IoT application backends | Medium |
| Tenant Dev | Tenant developers' laptops: the tenant-facing services and nothing else | Low |
| Guest | Transient visitor access | Untrusted |

### Management Segment

The management segment carries infrastructure control traffic.

**Typical inhabitants:**
- Builder (`dv00bld001p01`)
- Hypervisor management interfaces (`dv02hyp001p01-mgmt`, `dv02hyp002p02-mgmt`)
- Router management interfaces (`dv02cor002p01-mgmt`)
- Switch management interfaces (`dv02acc001p01-mgmt`)
- IPMI/BMC interfaces (`dv02hyp001p01-oob`)

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
- NAS storage interfaces
- Hypervisor storage interfaces (`dv02hyp001p01-stor`, `dv02hyp002p02-stor`)
- Backup target interfaces

**Properties:**
- High-bandwidth, low-latency requirements
- May use jumbo frames
- No internet access required
- Optional in minimal sites where storage traffic is negligible

### Tenant Fabric Transport

**A tenant is not a VLAN.** Since
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/), a tenant's network is an
EVPN/VXLAN overlay owned by the tenant hypervisor's own fabric, with its own anycast gateway and
its own VRF. The core router never sees a tenant subnet, and **creating a tenant adds no segment
here** — which is the whole point of the model.

What the substrate carries instead is two segments for the fabric itself, and they do not grow with
the number of tenants:

| Segment | Carries | Router address |
|---------|---------|----------------|
| **Tenant transit** | Aggregate tenant egress, from the fabric to the core router's perimeter | Yes — the perimeter handoff |
| **Tenant underlay** | VTEP-to-VTEP transport between fabric members | **None** — the core router neither routes it nor holds an address on it |

**Typical inhabitants:** the tenant hypervisor's transit and underlay interfaces. No tenant
workload sits on either — workloads live in the overlay, at `10.20.128.0/18`.

**Properties:**
- Isolation between tenants is enforced **inside the fabric**, one VRF per tenant — not by a
  firewall rule here
- Tenant traffic arrives at the perimeter already SNATed, so the core router cannot tell one tenant
  from another even if it wanted to
- The core router holds **one** aggregate route into the overlay, so that operators on management
  and trusted can reach tenant workloads
  ([ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/)). Devices, other
  tenants and the outside world still have no path in.

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

The IoT segment contains controlled devices with a known owner. Their firmware is built and released by that owner, from that owner's repository; the substrate attaches them to the network and issues their credentials, but does not build their software. Unlike the IoT Vendor segment, where the vendor controls the firmware, an IoT device's owner is accountable for what it runs.

**Typical inhabitants:**
- Raspberry Pis (`dv02rpi001p01`, `dv02rpi002p01`, `dv02rpi003p01`)
- Embedded devices (`dv02bgw001e01`)
- SDR receivers (e.g., `sdr.mobile.deevnet.net` → `dv02rpi001p01`)
- Sensors and IoT gateways

**Properties:**
- Medium trust — firmware is controlled by a known owner
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

### Tenant Dev Segment

The tenant dev segment is where a tenant's developer works from. It reaches the services a tenant
consumes from its own laptop, and nothing else inside the site.

**Typical inhabitants:**
- A tenant developer's laptop, running the tenant's infrastructure-as-code and test clients

**Properties:**
- May reach the tenant-facing services only: the onboarding API, the tenant state store, the
  message broker, the tenant log store, tenant dashboards and the read-only tenant downloads, each
  by host and port
- No access to management, trusted, storage, IoT or any tenant's workloads
- Internet access
- Dynamic DHCP only (no static mappings)
- A shared key, not per-tenant keys: the segment identifies no tenant. The API's credentials do that

Without it, a tenant must work from a trusted seat, which reaches far more than the tenant needs.

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
    Mgmt -->|manages| Tenant[Tenant Transit<br>Medium Trust]
    Mgmt -->|manages| IoTBackend[IoT Backend<br>Medium Trust]
    Mgmt -->|manages| IoT[IoT<br>Medium Trust]
    Mgmt -->|manages| IoTVendor[IoT Vendor<br>Very Low Trust]
    Trusted -->|user access| Storage
    Trusted -->|user access| Platform
    Trusted -->|user access| Tenant
    Trusted -->|user access| IoTBackend
    Trusted -->|user access| IoT

    IoT -->|sensor data| IoTBackend
    TenantDev[Tenant Dev<br>Low Trust] -->|API, state store| Platform
    TenantDev -->|broker| IoTBackend
    Mgmt -->|manages| TenantDev
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
- **Tenant Dev reaches tenant-facing services only** — Named hosts and ports on platform and IoT backend; nothing else internal
- **Guest has no substrate access** — Guest segment routes only to internet gateway

---

## Integration with Substrate Model

Network segmentation is substrate-scoped:

- Each site (home, mobile) implements segmentation independently
- No cross-site segment dependencies
- The same segment model applies to all sites
- Implementation details (VLAN IDs, IP ranges) vary per site

This aligns with the site independence principle — each site can be built, operated, and torn down without affecting the other.

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

1. Sites use ten segment types: Management, Trusted, Storage, Platform, Tenant transit, IoT Vendor, IoT, IoT Backend, Tenant Dev, Guest — plus the underlay and blackhole segments, which carry no routed traffic
2. Segments form a trust hierarchy with default-deny routing between them
3. Each site implements segmentation independently
4. Core router provides VLAN routing, firewall zones, and per-segment DHCP
5. Bootstrap mode uses flat networking; production mode uses full segmentation
