---
title: "Network Segmentation"
weight: 5
---

# Network Segmentation

Defines mandatory requirements for network segmentation in Deevnet substrates.

---

## Purpose

This standard establishes rules for how substrates implement network segmentation. It complements the [Substrate Networking](/docs/architecture/substrate/networking/) architecture document, which describes the segment model and design rationale.

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

- Management segment MUST exist in every substrate
- Management segment MUST contain the bootstrap/provisioner node
- Management segment SHOULD contain dedicated hypervisor management interfaces when hardware supports it
- Single-NIC hypervisors SHOULD use VLAN trunking or firewall rules to isolate management access
- Management segment MUST NOT contain end-user workloads or personal devices
- Management segment SHOULD contain IPMI/BMC interfaces
- Hosts in management segment MUST use `-mgmt` suffix for interface DNS entries (e.g., `hv01-mgmt.dvntm.deevnet.net`)

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
- Storage segment MAY be omitted in minimal substrates
- Storage segment MUST NOT carry non-storage traffic
- Hosts in storage segment MUST use `-stor` suffix for interface DNS entries (e.g., `hv01-stor.dvntm.deevnet.net`)
- Storage segment MAY use jumbo frames when all participants support them

### 4. Tenant Segments

Tenant segments provide workload isolation per tenant namespace.

- Each tenant MUST have its own dedicated segment
- Tenant segments MUST be isolated from each other by default
- Tenant segments MUST NOT have direct access to management segment
- Tenant segments MAY access shared services via explicit firewall rules
- Each tenant segment MUST have its own DHCP scope

### 5. IoT Segment

The IoT segment isolates untrusted or embedded devices.

- IoT segment MUST exist when untrusted devices are present
- IoT segment MUST be isolated from management segment
- IoT segment SHOULD allow controlled outbound internet access
- IoT segment MUST NOT have unrestricted inbound access
- Devices in IoT segment SHOULD be treated as potentially compromised

### 6. Guest Segment

The guest segment provides transient network access.

- Guest segment MUST provide internet access without substrate access
- Guest segment MUST NOT route to management, storage, or tenant segments
- Guest segment MUST use dynamic DHCP only (no static mappings)
- Guest segment MAY enforce bandwidth or time limits

---

## Inter-Segment Communication

### Default Policy

- All inter-segment traffic MUST be denied by default
- Allowed traffic MUST be explicitly defined in firewall rules
- Firewall rules MUST be version-controlled as code

### Permitted Flows

The following inter-segment flows are permitted when explicitly configured:

| Source | Destination | Condition |
|--------|-------------|-----------|
| Management | Any | Always allowed (for administration) |
| Trusted | Most segments | Allowed except guest (for user administration) |
| Trusted | Storage | Required for user data access |
| Compute hosts | Storage | Required for storage access |
| Tenant | Shared services | Explicit per-service rules |
| IoT | Internet | Outbound only |
| Guest | Internet gateway | Outbound only |

### Prohibited Flows

The following flows MUST NOT be permitted:

- Guest to any internal segment
- Tenant to tenant (cross-tenant)
- IoT to management (unless explicitly required for specific devices)

---

## DHCP Requirements

- Each segment MUST have a dedicated DHCP scope
- DHCP scopes MUST NOT overlap
- Management, trusted, and storage segments SHOULD use static DHCP mappings
- Tenant segments SHOULD use static mappings for known hosts
- IoT and guest segments MAY use dynamic pools

---

## Firewall Zone Principles

- Each segment MUST map to a firewall zone
- Zone rules MUST be explicit and auditable
- Zone rules MUST be defined as code (router config automation)
- Changes to zone rules MUST go through version control

---

## Substrate Independence

- Each substrate MUST implement segmentation independently
- Segment implementation (VLAN IDs, IP ranges) MAY differ between substrates
- No implicit dependencies between substrate segments
- Cross-substrate communication MUST traverse external routing

---

## Correctness Invariants

Network segmentation is correct when:

1. **Segment membership is declarative** — Host segment assignment is defined in inventory, not discovered
2. **Traffic policies are auditable** — All inter-segment rules exist as code
3. **Trust boundaries are enforced** — Firewall rules implement the trust hierarchy
4. **Segments are substrate-scoped** — No cross-substrate segment dependencies
5. **Authority is explicit** — Segment routing is controlled by the core router in production mode
