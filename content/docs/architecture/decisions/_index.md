---
title: "Decisions"
weight: 8
bookCollapseSection: true
---

# Architecture Decision Records

This section records **significant architectural decisions** — the design forks where more
than one option was viable, the reasoning that selected one, and the consequences accepted
in doing so. Each record is a durable answer to "why is it built this way, and what did we
turn down?"

Decision records are **point-in-time**. They capture what was decided and why *at the time
the decision was made*. When a later decision supersedes an earlier one, the earlier record
is marked `Superseded` and linked forward — records are never rewritten to hide the history.
The descriptive architecture, platform, and roadmap pages are kept current; the decision log
is kept honest.

Not every follow-on decision is a reversal. A record is often found to be **correct but
incomplete** — it settled the question it asked and left an adjacent one unanswered, usually
because building the thing is what exposed the gap. That case gets its own record, which
**extends** the earlier one: the earlier record keeps its `Accepted` status, because nothing
it decided has stopped being true, and gains a forward link. Superseding it instead would
retire a sound decision and force a near-duplicate rewrite, and appending the new reasoning
into the old record would date-stamp a decision to a day it was not made.

The test is whether the earlier record is still safe to act on. If yes, extend it. If acting
on it would now be a mistake, supersede it.

---

## Format

Each record follows a lightweight ADR structure:

| Field | Purpose |
|-------|---------|
| **Status** | `Proposed`, `Accepted`, `Superseded`, or `Deprecated` |
| **Extends** / **Extended by** | Set when one record answers a question another left open, without invalidating it. Both records stay `Accepted`. |
| **Context** | The situation and the goals that forced a choice |
| **Options considered** | The viable alternatives, each with its trade-offs |
| **Decision** | What was chosen |
| **Consequences** | What the decision commits us to — good and bad |

Records are numbered in the order they are **opened** (`0001`, `0002`, …) and never renumbered.
A record may sit at `Proposed` for a while before it is accepted; the number is claimed when the
question is written down, not when it is answered.

---

## Records

- [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) — tenant networking is an
  overlay fabric owned by the tenant compute domain, self-contained per hypervisor, built as
  a single-member fabric that expands to a cluster without redefinition.
- [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/) — every tenant
  identifier (VNI, VRF, subnet) derives from a single tenant index, allocated inside the existing
  site `/16` rather than a second aggregate.
- [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/) —
  tenant egress needs transit forwarding and a default route inside each tenant VRF; Proxmox's own
  exit-node behaviour routes around the perimeter rather than through it.
- [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/) —
  each tenant publishes into its own zone, delegated from the substrate zone and served by a
  substrate-run PowerDNS, written by the tenant over RFC 2136 with a TSIG key scoped to that zone.
- [ADR-0005: Tenant Zone Apex Ownership](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/) —
  a delegated zone's SOA and apex NS are substrate-owned and set at onboarding; extends ADR-0004,
  and records that this particular boundary is a convention rather than a server-enforced control.
- [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/) —
  each tenant lives in its own repository, consuming the tenant module by tag and a fabric
  attachment the substrate issues at onboarding; extends ADR-0004's onboarding-versus-recurring
  line into where the code itself lives.
- [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/) —
  the substrate offers an S3-compatible state store that tenants may use or decline; locking and
  per-tenant isolation are server-enforced, and the opt-out is what makes the dependency acceptable.
- [ADR-0008: Host Naming and Site Codes](/docs/architecture/decisions/0008-host-naming-site-codes/) —
  A fixed-width site code in every hostname, so the short name is unambiguous wherever
  it appears rather than only inside the inventory that loaded it; site zones renamed to say what
  the site is, and code `00` for the builder appliance that belongs to no site.
- [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/) —
  inventory is the only declaration of switch and AP configuration, and the Omada controller
  applies it through its documented Open API; undocumented calls are a marked, version-pinned
  fallback, and the CLI role becomes break-glass for adopted switches.
- [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) —
  *Accepted.* A tenant may depend on the substrate, but the substrate must not come to contain the
  tenant: platform services are bound to a tenant once at onboarding, and nothing that recurs needs a
  substrate commit; extends ADR-0004 §5 from DNS to every platform service.
- [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) —
  A physical device belongs to the application that gives it purpose, joins the access
  network of its trust class rather than its tenant's fabric, and reaches the tenant through scoped
  platform services; device secrets and signing keys never enter the substrate vault.
- [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) —
  *Accepted.* Where a backing service can't confine a tenant, as with the broker and the Wi-Fi
  controller, the substrate runs an API that holds its credentials and scopes every call to one
  tenant, and tenants use it through a Deevnet Terraform provider; v1 is a device registry, a
  Wi-Fi key binding and a broker account binding; extends ADR-0010 §3. Reviewed 2026-09-14:
  the API only provisions and the broker reads its own auth database, device secrets are restored
  from tenant state, providers come from an offline mirror, and tenant credentials are issued
  age-encrypted per consumer. Revised 2026-09-16: tenant workloads get broker accounts too, and
  the API confines topics by writing the tenant's prefix itself. Accepted 2026-09-18 at the close
  of CHG-0013, which built the Wi-Fi half and amended it: a key is per tenant per trust class, not
  per device. The device registry and broker accounts are decided but unbuilt — there is no broker.
- [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/) —
  Services on the management hypervisor run as containers on VMs grouped by domain —
  network management, substrate and tenant observability, provisioning, identity, and device
  messaging — each on exactly one network segment, so no VM bridges two zones; the Omada controller
  moves off the roaming Builder into the network management VM, and tenant DNS and state fold into
  the identity and provisioning VMs; extends ADR-0009.
- [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/) —
  *Proposed.* Once device secrets live in tenant state, that state is data that can't be
  re-derived. The store's data moves to a data disk and is copied on every write to separate on-site
  hardware, and the API's database is backed up on a schedule. It closes ADR-0012 §5's re-flash
  exception, which ADR-0013 had made a single-VM event. Extends ADR-0007 and ADR-0013.
- [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) —
  *Accepted.* The Deevnet API creates and builds tenants: its database is the only registry, an
  index is allocated against that registry and the live fabric, and the API builds each tenant's DNS,
  state credential, network, workloads and workload names. Tenants are admitted with a single-use
  enrollment token and hold no substrate credential; tenant repositories use one provider and carry no
  index, so tdemo returns as the reference tenant, and the factory keeps only the fabric. Extends
  ADR-0012; supersedes the registry in ADR-0002 and ADR-0006 §1–§3.
- [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/) —
  *Accepted.* The substrate's runtime credentials, the encryption of tenant secrets at rest, the
  internal certificate authority and single-use enrollment tokens live in OpenBao, in the identity VM,
  unsealed by a static key from ansible-vault. Chosen over Vault Community Edition for its native
  static seal and free namespaces. Extends ADR-0015.
- [ADR-0017: How Tenant Code Reaches a Tenant Workload](/docs/architecture/decisions/0017-tenant-code-delivery/) —
  *Proposed.* Separates the tenant-facing contract from the substrate-side mechanism. **The contract
  is settled:** a tenant declares its workload configuration to the Deevnet API in a Deevnet-owned
  schema, never Proxmox user-data, so a hypervisor detail stays out of the tenant contract and the
  mechanism can change. **Delivery is forced to be a pull** from inside the workload, because a
  tenant has no inbound path. **The mechanism is open:** an SMBIOS bootstrap pointer with
  configuration fetched from the API leads, because it is the only channel with an API-only path
  today and the only one where secrets never touch substrate storage; both halves were tested, and
  the channel's measured 512-character cap enforces a pointer rather than a payload. The workload
  fetches only when it has no cached configuration, not on every boot, which is what keeps ADR-0012
  provisioning-only rather than softening it. Extends ADR-0010, which said tenants own their code
  without saying how it arrives, and ADR-0015, which builds the empty workload this fills.
- [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/0018-operator-access-to-tenants/) —
  *Accepted.* The core router carries one aggregate route to the tenant overlay so the substrate's
  management and trusted networks can reach tenant workloads, because the operator owns every tenant
  here and building, checking and debugging one otherwise means the hypervisor console. Supersedes,
  in part, ADR-0001 and ADR-0002 where they say the core router never learns tenant address space.
  Devices, other tenants and the outside world still have no path in, and this is explicitly not a
  delivery mechanism for tenant code — ADR-0017 holds, now as a rule rather than a physical fact.
- [ADR-0019: Tenant Layer 2 at the Access Edge](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/) —
  *Accepted.* Re-opens ADR-0011 Option B for a variation it never considered: a VLAN range reserved
  once, so tenant creation needs no switch change. The variation is real and defeats two of Option
  B's objections, but the answer holds — Proxmox generates a VNet bridge whose only port is its
  VXLAN interface, EVPN zones have no DHCP option, and Proxmox SDN has no EVPN multihoming, so the
  boundary would be unreproducible node-local state that cannot be made redundant. Attachment stays
  by trust class, not by owner. Its one open question — whether a hand-added bridge port survives an
  SDN apply — is closed by reasoning rather than experiment: the port modifies an object the
  generator owns and rewrites, which is an ownership conflict whatever the reconciliation does.
  The reconsideration trigger is corrected: Art-Net and sACN are routable and were the wrong
  examples; only link-local discovery is genuinely L2-bound, and a reflector answers that.
- [ADR-0020: Direct Device Access to Tenant Services](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) —
  *Accepted.* Answers ADR-0011's open question 5, which an editing error had left orphaned and
  unnumbered: how a device reaches a service its application exposes directly, when publish/subscribe
  does not fit. It is the rendezvous shape ADR-0011 already named — a platform service on IoT
  Backend, over the `iot -> iot_backend` flow the standard already permits — so it needs no segment,
  no SSID and no new rule. What is accepted is the contract, not the mechanism: authorization is
  cryptographic and never rests on MAC or IP, direct access grants no tenant network membership,
  tenant workloads are never multi-homed onto device segments, and no zone-level path from devices
  into tenant space may be added. Records the invariant the shared segment depends on — every
  device-facing service authenticates its callers per device, because zone policy grants a whole
  zone — and accepts that peer devices on one VLAN are not separable with the current access point.
