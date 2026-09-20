---
title: "Network Segmentation"
weight: 5
---

# Network Segmentation

Defines mandatory requirements for network segmentation in Deevnet sites.

---

## Purpose

This standard establishes rules for how sites implement network segmentation. It complements the [Substrate Networking](/docs/architecture/substrate/networking/) architecture document, which describes the segment model and design rationale.

---

## Definitions

| Term | Definition |
|------|------------|
| **Segment** | An isolated broadcast domain (VLAN) with controlled routing to other segments |
| **Trust boundary** | The point where traffic policy changes between segments |
| **Inter-segment traffic** | Network communication that crosses segment boundaries |
| **Segment authority** | The system responsible for segment routing and policy (core router in production) |

---

## Segment Requirements

### 1. Management Segment

The management segment contains infrastructure management plane systems.

- Management segment MUST exist in every site
- Management segment MUST contain the bootstrap/provisioner node
- Management segment SHOULD contain dedicated hypervisor management interfaces when hardware supports it
- Single-NIC hypervisors SHOULD use VLAN trunking or firewall rules to isolate management access
- Management segment MUST NOT contain end-user workloads or personal devices
- Management segment SHOULD contain IPMI/BMC interfaces
- Where a host's management interface is **not** its primary, that interface MUST be named with the `-mgmt` interface code ([ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) §3.6). Where it is the primary, it carries the host's root name and takes no suffix.

### 2. Trusted Segment

The trusted segment contains high-trust user devices that require broad network access.

- Trusted segment SHOULD exist when user workstations need elevated access beyond tenant segments
- Trusted segment MUST contain only known, managed devices
- Trusted segment MAY access management services for administration purposes
- Trusted segment MUST NOT contain infrastructure management plane systems (those belong in management)
- Trusted segment SHOULD have endpoint security requirements (e.g., disk encryption, managed updates)
- Trusted segment MAY access storage segment for user data access
- Devices in trusted segment SHOULD be authenticated users with known identities

### 3. Storage Segment

The storage segment isolates storage protocol traffic.

- Storage segment SHOULD exist when dedicated storage traffic is needed
- Storage segment MAY be omitted in minimal sites
- Storage segment MUST NOT carry non-storage traffic
- Hosts in storage segment MUST name that interface with the `-stor` interface code ([ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) §3.6)
- Storage segment MAY use jumbo frames when all participants support them

### 4. Tenant Networks

Tenant networks provide workload isolation per tenant. Since
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) they are **overlays owned by
the tenant compute domain**, not VLANs owned by the core router. The isolation requirements are
unchanged; where they are enforced is not.

- Each tenant MUST have its own isolated routing domain — one VRF per tenant in the tenant fabric
- Tenant networks MUST be isolated from each other by default
- Tenant networks MUST NOT have direct access to the management segment
- Tenant networks MAY access shared services via explicit policy at the perimeter
- Each tenant MUST have its own address allocation and DHCP scope, served by **fabric IPAM**
- Tenant identifiers and subnets MUST be allocated from the globally-unique scheme in
  [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/)
- A tenant MUST NOT require a VLAN, a switch change, or a core router change to create

The core router sees only the aggregate **tenant transit** network and acts as its perimeter. It
MUST NOT hold a VLAN interface or a DHCP scope per tenant.

### 5. Platform Segment

The platform segment contains shared infrastructure services.

- Platform segment MUST contain only shared services (DNS, NTP, artifact mirrors, reverse proxy)
- Platform segment MUST be reachable from management, trusted, tenant, and IoT backend segments
- Platform segment MUST NOT contain user workloads or tenant applications
- Platform segment MUST use static DHCP mappings only
- Platform segment SHOULD be treated as high-trust infrastructure

### 6. Guest Segment

The guest segment provides transient network access.

- Guest segment MUST provide internet access without substrate access
- Guest segment MUST NOT route to management, storage, or tenant segments
- Guest segment MUST use dynamic DHCP only (no static mappings)
- Guest segment MAY enforce bandwidth or time limits

### 7. IoT Vendor Segment

The IoT vendor segment is a strict containment zone for vendor-managed devices.

- IoT vendor segment MUST be fully isolated from all internal segments
- IoT vendor segment MUST allow outbound internet access only (for vendor cloud)
- IoT vendor segment MUST NOT have inbound access from any segment
- IoT vendor segment MUST NOT access management, storage, tenant, or platform segments
- IoT vendor segment is stricter than the IoT segment — devices are assumed compromised

### 8. IoT Segment

The IoT segment contains controlled devices with a known owner. Their firmware is built and released by that owner, from that owner's repository; the substrate attaches them to the network and issues their credentials, but does not build their software. Unlike the IoT Vendor segment, where the vendor controls the firmware, an IoT device's owner is accountable for what it runs.

- IoT segment MUST exist when custom-developed embedded devices are present
- IoT segment MUST be isolated from management segment
- IoT segment SHOULD allow controlled outbound internet access
- IoT segment MUST NOT have unrestricted inbound access
- IoT segment has medium trust — firmware is controlled by a known owner, but the devices have limited security capabilities

### 9. IoT Backend Segment

The IoT backend segment hosts application backends that process IoT data.

- IoT backend segment MUST accept inbound connections from IoT segment
- IoT backend segment MAY access platform segment for shared services
- IoT backend segment MUST NOT access management segment directly
- IoT backend segment MUST use static DHCP mappings only
- IoT backend segment SHOULD validate and sanitize all input from IoT devices

---

## Inter-Segment Communication

### Default Policy

- All inter-segment traffic MUST be denied by default
- Allowed traffic MUST be explicitly defined in firewall rules
- Firewall rules MUST be version-controlled as code

### Intra-Segment Traffic

Every requirement in this section governs traffic **between** segments. Traffic between two hosts
*within* one segment is switched at Layer 2 and never reaches the segment authority, so no zone
rule can observe or constrain it. This is a property of the topology, not a gap in the policy.

- Zone policy MUST NOT be relied on to separate hosts inside one segment
- A segment that carries mutually-distrusting hosts MUST NOT treat segment membership as trust
- Services on such a segment MUST authenticate their callers individually; a service that trusts a
  caller because it arrived from the expected segment has no boundary
- Intra-segment separation, where required, MUST come from a mechanism that sees the traffic —
  access-point client isolation for wireless hosts, or switch port isolation for wired ones
- Where such a mechanism is unavailable, the limitation MUST be recorded rather than assumed away

The IoT segment is the current instance: it carries devices belonging to different owners, and the
site's access point offers no client isolation that preserves the service reachability those
devices need. See [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)
open question 4 for the hardware position, and
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §5 for the
control that holds instead.

### Reachability and Permission

Zone policy governs **reachability between** segments. It does not govern which service on a
reachable host a caller may use: a zone rule admits a source segment to a destination segment, and
every listening socket in that segment sits behind the same rule. This is intentional. A zone is a
coarse unit by design, and making zone rules per-service would pull every service's topology into
the router's rule table and make adding a listener a firewall change.

- Network policy MUST control reachability between zones
- Host or service policy MAY further constrain access to individual services within a zone, where
  zone-level policy is intentionally coarser than the service requires
- A service whose exposure must be narrower than its zone MUST be constrained by a mechanism that
  can see what a zone rule cannot — a host firewall, or the service's own authentication
- Where a service's real exposure is narrower than the zone rule implies, the zone policy MUST say
  where the rest of the enforcement lives, so a reader of the rule table is not left believing the
  rule is the whole control
- Reachability MUST NOT be read as permission

The IoT Backend segment is the current instance. `iot -> iot_backend` is a zone-level pass, because
it is how a device reaches the broker at all; it is not a statement that a device may reach every
port on that segment. The broker's auth database sits there too, and its exposure is narrowed by a
host firewall rather than by the zone rule, which cannot distinguish one port from another. See
[CHG-0016](/docs/changes/2026/0016-broker-accounts/).

This is the same reasoning as [Intra-Segment Traffic](#intra-segment-traffic) applied one layer
out, and the service half of it is
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §5:
*"Network policy decides which segments may speak; only the service decides who is speaking."*

### Permitted Flows

The following inter-segment flows are permitted when explicitly configured:

| Source | Destination | Condition |
|--------|-------------|-----------|
| Management | Any | Always allowed (for administration) |
| Trusted | Most segments | Allowed except guest (for user administration) |
| Trusted | Storage | Required for user data access |
| Compute hosts | Storage | Required for storage access |
| Tenant | Shared services | Explicit per-service rules |
| Platform | Internet | Outbound for updates and external APIs |
| IoT Backend | Platform | Shared service access (DNS, NTP) |
| IoT | IoT Backend | Sensor data, MQTT publish |
| IoT | Internet | Outbound only |
| Guest | Internet gateway | Outbound only |

### Prohibited Flows

The following flows MUST NOT be permitted:

- Guest to any internal segment
- Tenant to tenant (cross-tenant)
- IoT to management (unless explicitly required for specific devices)
- IoT vendor to any internal segment (full containment)
- IoT backend to management (must go through platform)

---

## DHCP Requirements

- Each segment MUST have a dedicated DHCP scope
- DHCP scopes MUST NOT overlap
- Management, trusted, storage, platform, and IoT backend segments SHOULD use static DHCP mappings
- Tenant segments SHOULD use static mappings for known hosts
- IoT and guest segments MAY use dynamic pools
- IoT vendor segment MAY use dynamic pools

---

## Trunk Port Native VLAN

- Trunk ports MUST use a dedicated blackhole VLAN (VLAN 999) as the native VLAN
- The blackhole VLAN MUST NOT have a routed interface, subnet, or gateway
- The blackhole VLAN MUST NOT have DHCP enabled
- Management traffic on trunk ports MUST be tagged, not native
- The blackhole VLAN MUST exist in the switch VLAN database at every site

---

## Firewall Zone Principles

- Each segment MUST map to a firewall zone
- Zone rules MUST be explicit and auditable
- Zone rules MUST be defined as code (router config automation)
- Changes to zone rules MUST go through version control

---

## Site Independence

- Each site MUST implement segmentation independently
- Segment implementation (VLAN IDs, IP ranges) MAY differ between sites
- No implicit dependencies between site segments
- Cross-site communication MUST traverse external routing

---

## Correctness Invariants

Network segmentation is correct when:

1. **Segment membership is declarative** — Host segment assignment is defined in inventory, not discovered
2. **Traffic policies are auditable** — All inter-segment rules exist as code
3. **Trust boundaries are enforced** — Firewall rules implement the trust hierarchy
4. **Segments are site-scoped** — No cross-site segment dependencies
5. **Authority is explicit** — Segment routing is controlled by the core router in production mode
