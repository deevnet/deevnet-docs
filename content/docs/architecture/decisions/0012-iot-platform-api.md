---
title: "ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider"
weight: 12
---

# ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider

|  |  |
|--|--|
| **Status** | Accepted |
| **Accepted** | 2026-09-18, at the close of [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) — when the Wi-Fi half had been built, deployed and proven on the AP, not when it was written. The broker half (§8) and the device registry (§3) are decided but not built. |
| **Date** | 2026-09-14 |
| **Reviewed** | 2026-09-14. Four of the original open questions were decided in review: the broker (§8), secrets after a rebuild (§4, §5), provider distribution (§7) and credential delivery (§9). The sources are quoted in each section. Revised the same day: the API is provisioning-only, and the broker authenticates from its own auth database (§8). Open questions 2, 5 and 6 were then answered: where the API, its database, the broker's auth database and the Omada controller run (§7, [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)). Revised 2026-09-16: tenant workloads get broker accounts too (§3), and topic confinement is decided (§10, Open question 4). Revised 2026-09-18 by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/), which built the Wi-Fi half: a key is per tenant per trust class rather than per device (§3), v1 ships on `DVNTM-IOT` only (§3), the drift report names profiles rather than counting keys (§6), and `DVNTM-IOT` turned out to be a creation rather than a migration (Consequences). |
| **Scope** | How a tenant reaches an IoT platform service whose own interface can't confine it to its scope, and what the substrate builds so it can |
| **Extends** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §1 and §3, which require a scoped service but don't say how one is built when the backing software can't scope itself |
| **Answers, in part** | [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) open questions 1 (scoped registration) and 3 (Wi-Fi keys — answered per tenant per trust class, not per device; §3) |
| **Related** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/), [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/), [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/) (§4 and §5 depend on it) |

---

## Context

### The rule has no mechanism for IoT

ADR-0010 set the test for a platform service: *does this recurring tenant action need a substrate
commit?* For IoT, two actions fail it today:
- registering a device with the MQTT broker
- granting it topics

ADR-0011 adds a third that it wants per device: a Wi-Fi key.

ADR-0010 §3 also says a service that can't confine a tenant *"is not offered as self-service."*
The validation on 2026-09-14
([ADR-0011 → Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14))
found that **neither backing service can confine a tenant:**

- **The broker.** Mosquitto's dynamic security plugin changes clients and permissions at runtime,
  but its administrative access is all-or-nothing
  ([mosquitto.org](https://mosquitto.org/documentation/dynamic-security/)).
- **The Wi-Fi controller.** Omada 6.3.0.45 documents per-device PPSK keys, each with its own VLAN.
  But every such write lists the permission *"Site Settings Manager Modify | Network Config Page
  Modify"*, the same one that creates SSIDs and ACLs.

Handing a tenant either credential hands it the whole service.

### How DNS solved the same problem

The substrate has already chosen the same shape three times:

| Record | What the substrate issues | What the tenant does after |
|---|---|---|
| [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) | A zone and a TSIG key, once | Writes its own records over RFC 2136 |
| [ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/) | A fabric attachment | Keeps its desired state in its own repository |
| [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/) | A state-store credential, declinable | Keeps its own Terraform state |

DNS had one advantage the IoT services lack: **a protocol with scoping built in.** The tenant
module records why it didn't use the PowerDNS HTTP API:

> PowerDNS's HTTP API has a single global key, so publishing through it would let any tenant write
> any zone. A per-zone TSIG key is scoped by the server
> — `deevnet-tenant-factory/modules/tenant/versions.tf`

That is the same situation the broker and the controller are in now. There is no MQTT or Omada
equivalent of a per-zone TSIG key, so if the scoping is to exist, Deevnet has to supply it.

### How tenants receive what the substrate issues

Tenant credentials are generated on the substrate side (`openssl rand`), kept in the substrate vault
(`vault_tenant_tsig_keys`, `vault_tenant_state_keys`), and imported by the `powerdns` and `minio`
roles. **A tenant receives them by reading the substrate vault itself:** the tenant Makefile runs
`ansible-vault view` against substrate inventory. So every tenant operator needs substrate vault
access. §9 changes that for every tenant credential, not only the new one.

### What the application owner actually wants

The goal is IoT platform services in the manner of a public IoT platform. The platform supplies
the facilities for connecting, identifying and serving devices. The owner writes the firmware,
owns the devices and their keys, and declares what it wants in its own Terraform.

### How devices, tenants and platform services connect at runtime

At runtime, devices, tenants and platform services meet on the site network, and they reach it by
**different paths**. The tenant is never reached *through* an IoT VLAN. The Deevnet API isn't part
of this picture: it only provisions (§1).

{{< graphviz >}}
digraph runtime {
    graph [
        rankdir=TB,
        splines=polyline,
        nodesep=0.4,
        ranksep=0.5,
        fontname="Helvetica",
        fontsize=12,
        bgcolor="#e0e0e0",
        pad=0.2,
        newrank=true,
        size="6.5,14",
        labelloc=b,
        label="Devices and tenants never connect to each other: both dial out and meet at the broker.\nIoT Vendor (VLAN 31): outbound internet only, nothing internal.\nThe Deevnet API is not in this path. It only provisions (section 1)."
    ]
    node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica", fontsize=11, margin="0.15,0.06"]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=10]

    // Clients at the top: application-owned devices (amber) and a hardwired
    // substrate Pi (blue), all on the IoT segment.
    subgraph cluster_devices {
        label="IoT, VLAN 30\nshared Layer 2"
        labelloc=t
        style=filled
        fillcolor="#f7f7f7"

        DeviceA [label="wireless device\n(tenant A)", fillcolor="#fff3cd"]
        DeviceB [label="wireless device\n(tenant B)", fillcolor="#fff3cd"]
        Pi [label="wired Pi\n(substrate)", fillcolor="#e0f0ff"]
    }

    AP [label="Wi-Fi AP dv02wap001p01\nSSID DVNTM-IOT -> VLAN 30", fillcolor="#e0f0ff"]
    Switch [label="access switch dv02acc001p01\nAP port: trunk 10, 30, 31, 40, 99\nPi port: access, VLAN 30", fillcolor="#e0f0ff"]

    subgraph cluster_router {
        label="Core router\nroutes between VLANs"
        labelloc=t
        style=filled
        fillcolor="#e0f0ff"

        Rules [label="zone policy (CHG-0007)\niot -> iot_backend\ntenant_transit -> iot_backend", fontname="Courier", fontsize=10]
    }

    // The backend, side by side: shared services and the tenant fabric.
    // Labels sit at the bottom, because links arrive from the switch above.
    subgraph cluster_hv01 {
        label="messaging VM dv02msg001v01\nIoT Backend, VLAN 35, on dv02hyp001p01"
        labelloc=b
        style=filled
        fillcolor="#e0f0ff"

        Broker [label="broker container\n(VerneMQ)"]
        AuthDB [label="broker auth database\ncontainer beside the broker\nread at connect (dashed)"]
    }

    subgraph cluster_hv02 {
        label="tenant hypervisor dv02hyp002p02\ntenant fabric, one VRF per tenant"
        labelloc=b
        style=filled
        fillcolor="#fff3cd"

        Exit [label="exit node (SNAT)\ntenant transit, VLAN 50"]
        TenantA [label="tenant A VRF"]
        TenantB [label="tenant B VRF"]
    }

    { rank=same; DeviceA; DeviceB; Pi }
    { rank=same; Switch; Rules }
    { rank=same; Broker; AuthDB; Exit }
    { rank=same; TenantA; TenantB }
    DeviceA -> DeviceB [style=invis]
    DeviceB -> Pi [style=invis]
    AuthDB -> Exit [style=invis]
    TenantA -> TenantB [style=invis]

    // Access: devices into the AP and switch.
    DeviceA -> AP
    DeviceB -> AP
    AP -> Switch
    Pi -> Switch

    // The switch's uplink to the router, and its links to the backend hosts.
    Switch -> Rules [dir=none]
    Switch -> Broker [dir=none]
    Switch -> Exit [dir=none]

    // Tenant workloads leave their VRF through the exit node.
    Exit -> TenantA [dir=back]
    Exit -> TenantB [dir=back]

    // The broker's only runtime dependency sits in the same VM.
    Broker -> AuthDB [style=dashed, constraint=false]
}
{{< /graphviz >}}

**The paths.** The switch port assignments are in `mobile/host_vars/dv02acc001p01.yml`.
- **Devices** reach the network in one of two ways:
  - through the Wi-Fi AP `dv02wap001p01`, whose switch port trunks VLANs 10, 30, 31, 40 and 99
  - through an access port in VLAN 30, for hardwired hosts such as the Pis

  They attach to the access VLAN of their trust class
  ([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) §3), not their
  tenant's, and reach the broker over `iot -> iot_backend`.
- **Tenant workloads** run on the tenant hypervisor `dv02hyp002p02` (trunk 50, 51, 99). They leave
  their VRF through the fabric's exit node, SNATed onto the **tenant transit** VLAN (50), and reach
  Platform and IoT Backend over `tenant_transit -> platform` and `tenant_transit -> iot_backend`
  ([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) Seam 1,
  [ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)).
- **The shared services sit beside the tenant fabric in the backend**, on the management hypervisor
  `dv02hyp001p01`.
  - The broker runs as a container in the messaging VM (`msg`, on IoT Backend, VLAN 35). Its auth database runs
    in a container beside it, and the broker reads it at connect (§7, §8).
  - The Deevnet API runs in the provisioning VM (`prv`, on Platform, VLAN 25), but nothing at runtime calls it
    (§1).
- **There is no *network* path between a tenant and a device.** Tenants have no inbound path
  (ADR-0003), so neither side can dial the other directly. They meet at a platform service on IoT
  Backend that **both** dial out to. The broker is that service for publish/subscribe, and it is
  the one this record builds.
  > **Amended 2026-09-19.** This read *"The broker is where they meet, and both sides dial out to
  > it"* — which, stated without qualification in an accepted record, made MQTT the only way an
  > application-owned device could ever reach its application. That was never the intent:
  > [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) §1 says
  > *"rendezvous services on IoT Backend, **such as** the broker."* The rendezvous **shape** is what
  > has no alternative — the absence of a network path is a fact about ADR-0003, not a preference
  > for a protocol. Which service fills that shape is open, and
  > [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) fills it
  > for request/response and stream protocols. It also answers what this sentence called
  > *"ADR-0011 open question 5"* — a number that did not exist until ADR-0011 was repaired the same
  > day. Nothing else in this record changes.

**What follows from the paths.**
- **Tenants can't see each other.** Isolation is enforced inside the fabric, one VRF per tenant:
  *"Tenant networks MUST be isolated from each other by default"*
  ([Network Segmentation](/docs/standards/network-segmentation/) §4).
- **The router can't tell tenants apart.** Their traffic arrives SNATed on one transit network, and
  the site's firewall policy says so: *"the core router sees only SNATed transit traffic, so it
  could not distinguish one tenant from another even if it wanted to"*
  (`mobile/group_vars/all/firewall.yml`).
- **A tenant can reach whole segments, but uses only what its credentials allow.** The zone rules
  open Platform and IoT Backend to every tenant. What a tenant can actually *do* there is set by
  what it holds: its TSIG key, its state key, its IoT API token. That is why this record scopes
  tenants by credential, in the API (§2).
- **Tenants' devices are not isolated from each other.** They share VLAN 30's Layer 2. Isolation
  there is best effort, with credentials first (ADR-0011 open question 4).
- **IoT Vendor devices use no internal service.** *"IoT vendor segment MUST be fully isolated from
  all internal segments"* (standard §7), so they get a Wi-Fi key and nothing else (§3).
- **The Deevnet API is not in the runtime path.** Devices, the AP and the broker never call it. An
  API outage stops provisioning, not devices (§1, §8).
- **None of this is enforced yet.** The core router passes all traffic between segments until
  [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) applies the zone policy.

---

## Options considered

### A — Hand tenants the backing credentials

Give each tenant an Omada Open API client and dynsec admin rights.

- **Pros:** nothing to build.
- **Cons:** neither credential can be narrowed to one tenant, so each tenant could rewrite the
  site's wireless and every other tenant's broker permissions. It fails ADR-0010 §3 outright.
- **Verdict:** Rejected.

### B — The substrate acts per device

Today's model. Device accounts, ACLs, and eventually keys are declared in substrate inventory and
applied by substrate automation.

- **Pros:** it works, it's reviewable in git, and it's the pattern the substrate uses everywhere.
- **Cons:** every device is a substrate commit, which fails the ADR-0010 test.
- **Verdict:** Rejected. It stays as the recorded debt ADR-0010 lists until this record is built.

### C — Tenants run their own broker and Wi-Fi

- **Cons:** already rejected by ADR-0010 Option C. There is one physical access network, and tenants
  have no inbound path for devices to reach.
- **Verdict:** Rejected.

### D — A Deevnet API, consumed through a Terraform provider

The substrate runs an API that holds the backing credentials, confines every request to the
calling tenant, and drives the backing services. Deevnet publishes a Terraform provider for it,
and tenants declare devices in their own Terraform.

- **Pros:**
  - It meets ADR-0010 §3 for services that can't scope themselves.
  - Tenant desired state stays in the tenant's repository (ADR-0006) and state (ADR-0007).
  - **The backing implementation can change without the tenant noticing:** a different broker, a
    different controller, a different Wi-Fi vendor.
  - It gives the platform one place to record what changed, which ADR-0010 noted no service yet has.
- **Cons:**
  - It is a new service to build, run, secure and version.
  - It holds privileged credentials, so its compromise is a site-wide compromise of those services.
  - A provider brings schema-versioning discipline and a distribution problem (§7).
- **Verdict: Chosen.**

**An API without a provider** was also considered. It is viable for imperative work, but desired
state would then live in scripts or in the API's own database rather than in tenant Terraform. That
breaks ADR-0010 §4's re-derivability. The provider is the primary interface; the API stays callable
directly for work that isn't declarative.

---

## Decision

**Option D.**

### 1. The API provisions; it is never in a device's path

{{< graphviz >}}
digraph provisioning {
    graph [
        rankdir=TB,
        splines=ortho,
        nodesep=0.45,
        ranksep=0.55,
        fontname="Helvetica",
        fontsize=12,
        bgcolor="#e0e0e0",
        pad=0.2,
        newrank=true,
        size="6.5,14",
        labelloc=b,
        label="Solid: written at provisioning time.  Dashed: secrets returned to the tenant.\nDotted: what the broker reads at runtime, shown for context. The API is never in a device's path."
    ]
    node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica", fontsize=11, margin="0.15,0.06"]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=10]

    subgraph cluster_tenant {
        label="Tenant repository"
        labelloc=t
        style=filled
        fillcolor="#fff3cd"

        Creds [label="credentials file (age)\nissued at onboarding (section 9)"]
        TF [label="tenant Terraform\nBuilder, laptop or CI"]
        Provider [label="provider\ndeevnet/deevnet"]
        State [label="tenant state\nauthoritative device secrets"]
    }

    subgraph cluster_control {
        label="provisioning VM dv02prv001v01 (Platform, VLAN 25)\nDeevnet API containers: provisioning only"
        labelloc=b
        style=filled
        fillcolor="#e0f0ff"

        API [label="Deevnet API\nv1: device registry, Wi-Fi key,\nbroker account"]
        APIDB [label="API database\nregistry, hosted tenant state"]
        Later [label="later layers, each its own record\nidentity/PKI, policy, firmware hosting,\nOTA/jobs, observability", style="rounded,dashed,filled"]
    }

    Controller [label="Omada controller container\nnetwork management VM dv02nms001v01\nwrites: PPSK key on the trust-class VLAN\nvia platform -> management, one port", fillcolor="#e0f0ff"]
    AuthDB [label="broker auth database container\nmessaging VM dv02msg001v01 (VLAN 35)\nwrites: account + ACL (bcrypt)\nvia platform -> iot_backend, one port", fillcolor="#e0f0ff"]
    AP [label="Wi-Fi AP\ndv02wap001p01", fillcolor="#e0f0ff"]
    Broker [label="broker container (VerneMQ)\nsame VM", fillcolor="#e0f0ff"]

    { rank=same; TF; Creds }
    { rank=same; Provider; State }
    { rank=same; API; APIDB; Later }
    { rank=same; Controller; AuthDB }
    { rank=same; AP; Broker }
    TF -> Creds [style=invis]
    Provider -> State [style=invis]
    API -> APIDB [style=invis]
    APIDB -> Later [style=invis]
    Controller -> AuthDB [style=invis]
    AP -> Broker [style=invis]

    // Provisioning: the tenant declares, the provider calls the API.
    TF -> Provider
    Provider -> API
    API -> APIDB [constraint=false]

    // The API writes into the backing services.
    API -> Controller
    API -> AuthDB
    Controller -> AP

    // Secrets come back into the tenant's own state.
    API -> State [style=dashed, constraint=false]

    // Runtime, for context only: the broker reads its auth database.
    Broker -> AuthDB [style=dotted, dir=back]
}
{{< /graphviz >}}

- **The API is the only tenant-facing control surface for IoT services.** The Omada controller and
  the broker's auth database are implementations behind it. No tenant holds their credentials.
- **It provisions, and nothing else.** A tenant's `terraform apply` is the only thing that calls it.
  It writes:
  - a Wi-Fi key to the Omada controller, which pushes it to the AP
  - a broker account, for a device or a tenant workload, and its ACL to the broker's auth database

  After that, the AP authenticates the device itself, and the broker reads its own database (§8).
  No device, AP or broker calls the API at runtime.
- **Secrets come back to the tenant.** The keys and passwords the API generates return to the
  tenant's state, which holds the authoritative copy (§4, §5).
- **Devices never call the control plane.** They connect to Wi-Fi and the broker as they do today.

### 2. Scope is enforced by the API, and issued once

- **One credential at onboarding.** At onboarding the substrate issues each tenant one API
  credential. It is the same act, and the same shape, as the TSIG key (`vault_tenant_tsig_keys`)
  and the state key (`vault_tenant_state_keys`). It is delivered as §9 describes.
- **Every object belongs to exactly one tenant.** The API refuses any read or write outside the
  calling tenant's objects.
- **The backing credentials are the API's alone**, held by the substrate: the Omada Open API client,
  and write access to the broker's auth database (§8).

This is how ADR-0010 §3 is met for a service whose own interface can't meet it. The confinement is
a control enforced by the API, not a convention, because the tenant never holds a credential that
could go around it.

### 3. Version 1 is a registry and two bindings

v1 covers exactly the actions that fail ADR-0010's test. Resource names below are working names.

| Resource | What it is | Confined by the API to |
|---|---|---|
| `deevnet_iot_device` | A registry entry: name, trust class (`iot` or `iot_vendor`), optional MAC | The calling tenant |
| `deevnet_iot_wifi_key` | A PPSK key for one tenant on one trust class's SSID | **That trust class's VLAN.** The tenant can't choose a VLAN, so no tenant network ever reaches the air (ADR-0011 Option B stays rejected). |
| `deevnet_iot_broker_account` | An MQTT account, with its topic permissions, for a device or for a tenant workload | Topics under the tenant's prefix, `<tenant>/…`, which the API writes itself (§10). The existing ACLs already follow this: `eds/lightstand/…`. **A device account needs trust class `iot`.** A workload account has no device. |

**A key is per tenant per trust class, not per device.** *Amended 2026-09-18.* The original wording
was one key per device.

- **A MAC binding buys no enforcement.** Omada can bind a key to a MAC, but a MAC is trivially
  spoofed, so the binding stops nobody who is trying. What it does cost is real: the tenant has to
  enumerate its hardware to the substrate before it can flash anything, and a replaced device
  becomes a substrate act — which is exactly the test [ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §2 sets.
- **The thing that is enforced comes from the key either way.** The VLAN is bound to the key, so a
  device joining with a tenant's key lands on that trust class's VLAN whether or not the substrate
  has heard of the device.
- **So revocation is the only thing granularity buys**, and per tenant per class is the boundary the
  substrate can actually police: one tenant's key dies without touching another tenant's devices.
  Finer than that is the tenant's business, and a tenant that wants a key per device can declare
  several — the resource does not stop it.
- **The device registry is unaffected.** `deevnet_iot_device` still exists, for broker accounts.
  A Wi-Fi key does not reference it: one key serves every device the tenant flashes with it.
- **What it costs, stated plainly.** A key lives in a device's NVS, written over USB, so revoking
  one means a visit to every device of that tenant in that class. The per-device alternative would
  have made that one visit — at the price of a substrate registration before every first flash.

**The keys sit in a shared profile, and the controller can read them back.**
`getPPSKProfileDetail` returns every key in a profile with its password in plaintext, to any caller
holding the site-write permission every PPSK write needs. That is what makes the API's
read-before-write possible, and it is also the reason no tenant may ever hold that credential
(§2, and ADR-0010's Consequences). The substrate automation deliberately never reads a profile's
keys, so they do not reach Ansible output.

**IoT Vendor devices get no broker account.**
- **The standard forbids the path.** It says *"IoT vendor segment MUST be fully isolated from all
  internal segments"* and *"MUST NOT access management, storage, tenant, or platform segments"*
  ([Network Segmentation](/docs/standards/network-segmentation/) §7). The zone policy declares no
  `iot_vendor -> iot_backend` rule.
- **So the account would be useless.** A broker account for a vendor device could never be used,
  and issuing one would imply a path the segment is defined not to have.
- **What the API does instead:** it refuses `deevnet_iot_broker_account` for a device whose trust
  class is `iot_vendor`. Such a device gets a `deevnet_iot_wifi_key` on VLAN 31, and outbound
  internet only.

**v1 ships on `DVNTM-IOT` only.** *Added 2026-09-18.* `DVNTM-IOTV` keeps its shared key until its
own change record: it already exists and already has devices, whereas `DVNTM-IOT` never existed, so
one is a migration and the other is a creation. See the Consequences.

**Tenant workloads get broker accounts too.** *Added 2026-09-16.*
- **Why.** A tenant's own services reach its devices through the broker. lightd, in eds, publishes
  scenes to the LP stand and reads its status, under the ACLs in
  `mobile/group_vars/mqtt_brokers.yml`. lightd is a workload in the tenant fabric, not a device, so
  an account that has to belong to a registry entry can't describe it.
- **How.** `deevnet_iot_broker_account` takes an **optional** device.
  - With a device, the device's trust class must be `iot`, as above.
  - Without one, the account belongs to a tenant workload.
- **Its path is already declared.** A workload connects from the tenant fabric over
  `tenant_transit -> iot_backend` (Context), so the device trust-class rule doesn't apply to it.
- **Confinement doesn't change.** Every account's topics are confined to the tenant's prefix
  (§10), with or without a device.
- **Not chosen: a separate workload-account resource.** It would repeat the same schema and the
  same confinement, and differ only in one reference.

The `deevnet_` prefix is not just a naming choice. *"Terraform uses a resource type's name to
determine which provider to use. By convention, resource type names start with their provider's
preferred local name"*
([HashiCorp](https://developer.hashicorp.com/terraform/language/resources/configure)). So these
resources belong to a provider whose type is `deevnet` (§7).

Everything else in the layer model is a later layer:
- identity and PKI
- policy
- firmware release hosting
- OTA and jobs
- observability

Each needs its own record. OTA and jobs in particular are imperative and are unlikely to be
Terraform resources at all.

### 4. The API generates device secrets; the tenant's state holds the authoritative copy

*Decided in review, 2026-09-14.*

- **Generated on first create.** The API generates the Wi-Fi key and the broker password. The
  provider returns them as sensitive attributes, and they land in the tenant's own state (ADR-0007:
  its prefix in the offered store, or its own backend). The owner provisions them onto the device.
- **The tenant's state is the authoritative copy.** The API's copies are working copies, restorable
  from the tenant's state (§5).
  - For the broker, only what authentication needs is kept: a bcrypt hash, in the broker's auth
    database (§8).
  - A PPSK key is stored by the controller in usable form because the AP needs it. That is a
    property of the protocol, not a copy kept for the substrate's use.
- **Secrets are sensitive values in state, not write-only.** Terraform 1.11's write-only arguments
  keep a value out of state entirely: they are *"not persisted to the Terraform plan or state"*
  ([HashiCorp](https://developer.hashicorp.com/terraform/plugin/framework/resources/write-only-arguments)).
  That would leave nothing to restore from, so they were considered and **not chosen**.
- **Rotation is a replacement.** Replace the resource and re-provision the device.
- **Device identity is not firmware signing.** If identity PKI is added later, it is device
  identity only. Firmware signing keys never reach the substrate (ADR-0011 §4).

**Also considered in review:** having the tenant generate secrets in its own Terraform (for example
`random_password`, whose result is stored in state) and pass them in. That is restorable by
construction, but it reverses "the API generates" and wasn't chosen.

### 5. A substrate rebuild never costs a device visit

*Decided in review, 2026-09-14.*

- **The API's database is hosted tenant state, not the source of truth** (ADR-0010 §4).
- **Requirement:** a substrate rebuild that loses the API's database costs each tenant one
  `terraform apply`, and **never** a device visit. This matters most for devices provisioned over USB
  into NVS, such as the Ma Bell gateway (ADR-0011).
- **How the provider meets it: restore, not recreate.**
  - When the API reports an object missing, the provider sends the object back **with the secret
    already in state**. Terraform doesn't get to plan a fresh create with a new secret.
  - The device reconnects with the key and password it already holds.
  - Both backing services accept a supplied secret. Omada's add-key operation takes
    `ppskList[].psk` (*"Password, should contain 8 to 63 visible ASCII characters."*). For the
    broker, the API writes the restored password's bcrypt hash back into its auth database (§8).
- **This departs from the framework's documented pattern, on purpose.** The Terraform Plugin
  Framework tells a provider whose remote object is gone to *"call the response state
  `RemoveResource()` method, and return early"*, after which *"the next Terraform plan will
  recreate the resource"*
  ([HashiCorp](https://developer.hashicorp.com/terraform/plugin/framework/resources/read)). Followed
  as written, that re-creates the object with a new secret. The provider's restore path is a
  deliberate exception, confined to the secret-bearing resources, and has to be documented in the
  provider.
- **The one case that still costs a re-flash:** losing the API's database **and** the tenant's state
  together.

### 6. One object class is carved out of ADR-0009

- **ADR-0009 still holds for site structure.** Inventory remains the only declaration of site
  structure: networks, SSIDs, AP settings, and **one PPSK profile per trust class**. The controller
  applies that inventory, as ADR-0009 decided.
- **Each trust class keeps its own SSID, carrying one VLAN.**
  - `DVNTM-IOT` carries VLAN 30 only, and `DVNTM-IOTV` carries VLAN 31 only. Each SSID has its own
    PPSK profile.
  - The API binds every key in a profile to that SSID's single VLAN.
  - One SSID spanning several trust-class VLANs is avoided on purpose. The controller's spec warns
    that *"If a device does not support multiple VLANs, the smallest VLAN you configured will be
    applied to the SSID"*
    ([ADR-0011 → Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#wireless-per-key-vlans-ppsk)).
    On such an AP, a key meant for IoT Vendor would silently land on IoT.
- **The carve-out: keys inside those profiles are tenant content**, written by this API, not by
  inventory.
- **The existing guard already fits.** ADR-0009's automation never deletes objects inventory
  doesn't declare (§7), so it leaves the keys in place already. What changes is its report: it has
  to recognize API-owned keys as expected rather than list them as drift. *Built 2026-09-18:* it
  **names the profiles whose contents it is not inspecting** rather than counting their keys,
  because counting would mean calling `getPPSKProfileDetail`, which returns every tenant's password
  in plaintext. Live tenant credentials have no business in Ansible memory or output.
- **Inventory creates the profile empty.** A profile has to exist before the SSID that binds it,
  and it holds no key of inventory's own. Whether the controller accepts a create with an empty key
  list is undocumented — the schema permits it — so the play tries empty and, if refused, creates
  with one random seed key and deletes that key in the same run.
- **This extends ADR-0009 for one object class; it does not supersede it.**

### 7. Placement, and how the provider reaches tenants

*Distribution decided in review, 2026-09-14.*

**Placement.**
*Placement decided 2026-09-14 (Open questions 2, 5 and 6), following the domain VMs of [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/).*

- **The API and its database run as containers in the provisioning VM (`prv`)**, on the management
  hypervisor `dv02hyp001p01`, on Platform (VLAN 25).
  - **Not on management.** Tenants must reach the API, and the segmentation standard says
    *"Tenant networks MUST NOT have direct access to the management segment"*
    ([Network Segmentation](/docs/standards/network-segmentation/) §4).
  - **Not in the same VM as the controller.** They serve different domains on different segments. ADR-0013 groups services by domain and keeps every VM on one segment, so no VM bridges two zones.
  - **hv01's switch port gains VLAN 25.** It carries 35 and 99 today, and adding 25 is the same
    one-time change that added 35 for the broker (`mobile/host_vars/dv02acc001p01.yml`).
- **Tenants reach it** over `tenant_transit -> platform`, which the declared zone policy already
  allows. Operators reach it from management.
- **Nothing on the IoT segments needs a path to it.** Devices never call it, and neither does the
  broker.
- **The broker's auth database runs beside the broker, in the messaging VM (`msg`).**
  - It fate-shares with the broker, so patching or losing the provisioning VM never affects
    devices.
  - It is a separate database from the API's own.
  - The API writes it over a narrow `platform -> iot_backend` rule: from the provisioning VM
    to the database port, and nothing else.
  - **Amended 2026-09-20.** "And nothing else" is not something a zone rule can deliver, and this
    sentence would be believed by someone who has not tried. Zone rules grant a whole zone, and the
    site declares `iot -> iot_backend` as a zone-level pass because that is how a device reaches
    the broker. So a database port published on that segment is reachable from every device on the
    IoT segment, whatever the `platform -> iot_backend` rule says — not because a rule permits it,
    but because the rule that admits devices to the broker cannot tell one port from another.
    The zone rule states the intent; a **host firewall** on the messaging VM enforces the part the
    zone rule cannot express. This was written before
    [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) made zone policy real, which is
    why it assumed otherwise. See
    [Network Segmentation → Reachability and Permission](/docs/standards/network-segmentation/#reachability-and-permission)
    and [CHG-0016](/docs/changes/2026/0016-broker-accounts/).
- **The Omada controller runs as a container in the network management VM (`nms`)**, on management
  ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)). The API
  reaches it over a narrow `platform -> management` rule: from the provisioning VM to the
  controller's Open API port, and nothing else.
- **Both narrow rules are declared when the API is built.** Neither exists today.

**The requirements set in review:**
- **Private now, public later.** Going public must be a switch, not a rewrite.
- **Tenant `terraform init` works with no internet access.** This goes beyond the standard, which
  says *"Air-gap scope is **substrate only**. Tenants and edge devices may follow different
  policies."* ([Correctness §5.4](/docs/standards/correctness/)). The offline requirement is
  therefore tenant policy set by this record, and it covers every provider a tenant uses:
  `bpg/proxmox` and `hashicorp/dns` too, which today come straight from the public registry.
- **Tenant Terraform runs from the Builder, from operator laptops, and eventually from CI** on site
  (§9).

**Decision: a filesystem mirror now, served over HTTPS later.**
- **Building the mirror.** The artifacts role builds a provider mirror in Terraform's packed
  layout, *"`HOSTNAME/NAMESPACE/TYPE/terraform-provider-TYPE_VERSION_TARGET.zip`"*. Public providers
  come from `terraform providers mirror`. Deevnet's own release archives are placed into the same
  layout, because that command only documents downloading from registries.
- **Reaching it.** The Builder uses the mirror locally, and laptops and CI copy it from the
  artifact server. *Amended by [CHG-0025](/docs/changes/2026/0025-tenant-downloads/):* the artifact
  server is on management, which a tenant laptop on `DVNTM-TD` must not reach, so tenants get the
  prebuilt provider (and the `grafana` provider) from the read-only **tenant downloads** on
  Platform, or from the provider's GitHub release, installed into the implicit local mirror by
  `install-provider.sh`.
- **Integrity comes from the tenant's committed lock file, not from the transport.** Terraform
  *"will also verify that each package it installs matches at least one of the checksums it
  previously recorded in the lock file"*
  ([HashiCorp](https://developer.hashicorp.com/terraform/language/files/dependency-lock)). The `h1:`
  scheme is *"computed from the contents of the provider distribution package"*, while `zh:` *"is not
  suitable for verifying packages that come from other provider installation methods"*. The docs
  don't state outright that every installation method is checked alike, so a tamper test confirms
  it before this is relied on (see [To confirm when building](#to-confirm-when-building)).
- **Why not an HTTPS mirror now.** A network mirror *"must use the scheme `https:`"* and is subject
  to TLS certificate checks
  ([HashiCorp](https://developer.hashicorp.com/terraform/internals/provider-network-mirror-protocol)).
  The artifact server serves plain HTTP. The internal CA is still an unstarted roadmap project
  ([SSL Cert Automation](/docs/roadmap/infrastructure/ssl-cert-automation/), 0 of 16 tasks).
- **Later.** Once that CA exists, the same tree is served as a network mirror, and only client
  configuration changes.
- **Rejected: `dev_overrides`.** It *"disables the version and checksum verifications for this
  provider"*, and HashiCorp recommends it *"only temporarily during provider development work"*.

**Decision: the source address is `deevnet/deevnet` from day one.**
- It is the public-registry form, served from the mirror while private, so going public later
  needs no change to any tenant's `required_providers`.
- The type `deevnet` is the one §3's resource names require.
- **The assumption this rests on:** publishing gives the namespace `deevnet`. The registry's
  publishing flow selects *"the organization and repository"*, and the repositories live in the
  `deevnet` GitHub organization. The docs imply this but don't state it.
- **Publishing requirements to meet from the start:** the repository must be public and *"match
  the pattern `terraform-provider-{NAME}`"*, and *"all provider releases are required to be signed"*
  ([HashiCorp](https://developer.hashicorp.com/terraform/registry/providers/publishing)). So the
  repository is named `terraform-provider-deevnet`, and releases carry a manifest, `SHA256SUMS` and a
  GPG signature from the first tag, even while private.
- **The alternative, rejected:** a Deevnet hostname address such as
  `terraform.deevnet.net/deevnet/deevnet`. Going public would then mean changing the source in every
  tenant and running `terraform state replace-provider`, which *"will update all resources using the
  'from' provider"*
  ([HashiCorp](https://developer.hashicorp.com/terraform/cli/commands/state/replace-provider)).

**The provider is versioned like the tenant module.** Tenants pin it and commit the lock file, as
they already do for `bpg/proxmox` and `hashicorp/dns`.

### 8. The broker is VerneMQ, built from source, and it reads its own auth database

*Decided in review, 2026-09-14; revised the same day to make the API provisioning-only.*

**The requirements set in review:**
- **Devices authenticate with a username and password**, over TLS. That is how the LP stand works
  today, and it keeps identity and PKI a later layer.
- **The API is provisioning-only.** When a tenant provisions, the API writes each device's account
  and ACL into the broker's own auth database. The broker authenticates from that database at
  connect, and never calls the API.
- **This was revised the same day.**
  - **What was chosen first:** the pull model, in which the broker asks the API on every connect,
    subscribe and publish, with a brief API outage accepted.
  - **Why it changed:** drawing runtime and provisioning as separate flows showed that the pull
    model put the API in every device's path.
  - **The result:** an API outage now stops provisioning, never devices.
- **Design for growth.** v1 is one node, but the broker must be able to cluster later.

**Why VerneMQ.**
- **Its source is Apache-2.0**, and the project describes itself as *"a distributed MQTT message
  broker"*. It states *"The VerneMQ mission is active & the project maintained"*
  ([GitHub](https://github.com/vernemq/vernemq)). The current release is 2.2.0, published
  2026-08-09, following 2.1.1 on 2025-07-14 (GitHub releases API).
- **It authenticates from a database, natively**
  ([VerneMQ database auth](https://docs.vernemq.com/configuring-vernemq/db-auth)):
  - *"The database drivers are handled using the `vmq_diversity` plugin"*
  - supported databases: PostgreSQL, MySQL, MongoDB, Redis and CockroachDB
  - passwords are bcrypt for PostgreSQL, MongoDB and Redis
  - ACLs are JSON pattern objects with optional `modifiers`. Modifiers turned out not to be a way to
    enforce the tenant prefix (§10).
- **Lookups happen once per connection.** *"The database integrations will cache the ACLs when the
  client connects avoiding expensive database lookups for each publish or subscribe message. The
  cache entries are evicted when the client disconnects."*
- **The database is now the broker's runtime dependency, in place of the API.** It runs beside the
  broker in the messaging VM, separate from the API's own database (§7).
- **Built from source, not from the official images.** *"To use the provided docker images the
  VerneMQ EULA must be accepted"*
  ([VerneMQ Docker](https://docs.vernemq.com/installing-vernemq/docker)). The 2.2.0 release notes put
  the binary packages and images under that EULA too. Building from the Apache-2.0 source avoids the
  question, and the Builder already builds and stages images.

**Rejected in review.**

| Broker | Why not |
|---|---|
| **EMQX** | A strong fit technically: HTTP authentication with per-client ACLs, and HTTP authorization. But from 5.9 it is under the Business Source License. EMQ's FAQ: *"You may run single-node (any size) instances of EMQX in production for free, as long as you do not offer EMQX itself 'as‑a‑service'"*, and *"You cannot connect multiple nodes into a cluster (clustering requires a commercial license)"* ([EMQX licensing FAQ](https://www.emqx.com/en/content/license-faq)). That fails the growth requirement. Its last Apache-licensed line, 5.8, reached end of life on *"February 28, 2026"*, after which EMQ *"will no longer provide … bug fixes, security patches"* ([EMQ notice](https://www.emqx.com/en/news/a-notice-on-the-emqx-5-8-open-source-version)). |
| **Mosquitto** (today's broker) | Its dynamic security plugin changes clients and permissions at runtime, so it could hold accounts the API writes, and provisioning-only doesn't rule it out. Growth does: clustering and high availability are sold by Cedalo as Pro Mosquitto features, not open-source ones. Under the earlier pull model it was also rejected because the third-party `mosquitto-go-auth` plugin was archived in June 2025, per its package page; that reason no longer applies. |

**The existing `mosquitto` role and `dv02mqt001v01` are superseded once this is built.** The broker
doesn't answer today anyway (ADR-0011 → Validation).

### 9. Tenant credentials are issued age-encrypted into the tenant's repository

*Decided in review, 2026-09-14.*

**The requirements set in review:**
- **A tenant operator never needs substrate vault access.**
- **One delivery path for every tenant credential:** the TSIG key (ADR-0004), the state-store key
  (ADR-0007) and the IoT API token (§2).
- **A static token now, short-lived tokens later.** v1 issues one long-lived, rotatable API token
  per tenant. The API stores only its hash, and its authentication layer is written so a token
  exchange can be added without changing how the provider is configured.
- **Tenant CI will be self-hosted on site**, and must reach the API and the provider mirror.

**Generation doesn't change; delivery does.** Generating credentials at onboarding stays a
substrate act (ADR-0004 §5): the substrate creates them, keeps them in its vault, and its roles
import them into the services. What changes is how the tenant receives them.

**Decision.**
1. **The tenant registers public keys at onboarding.** It gives the substrate one **age public
   key per consumer**: the Builder operator, each laptop, and the CI runner. They are recorded in
   the tenant's row in `deevnet_tenants`. A public key is not a secret, so it belongs in inventory.
2. **The substrate issues an encrypted credentials file into the tenant's repository**, with a
   target beside the existing one. `make tenant-attachment` already issues the fabric attachment
   *"to a tenant repository. This is an onboarding act, done once per tenant"*. A
   `make tenant-credentials TENANT=<path>` target reads the substrate vault **on the substrate
   side**, and writes the tenant's credentials encrypted to all of its recipients.
3. **The tenant decrypts with its own key** and exports the values as it exports them today. The
   encrypted file is safe to commit.
4. **Provenance is the commit.** The substrate operator commits the file into the tenant repository,
   or opens a pull request, and git review and history establish where it came from.

**Why age, and why this is enough.**
- **age is packaged in Fedora** (1.3.1, in `updates`).
- **Its payload is authenticated.** The age specification encrypts it with ChaCha20-Poly1305 and
  protects the header with a MAC *"computed with HMAC-SHA-256"*
  ([C2SP age](https://github.com/C2SP/C2SP/blob/main/age.md)). One file can carry many recipients.
- **age doesn't authenticate the sender.** The specification describes no sender authentication:
  anyone holding a tenant's public keys could encrypt a substitute file. That is why provenance comes
  from the commit, and why an unexplained change to the file in the tenant's history is a signal.
  Signing each file was considered and not chosen for v1.

**Revoking a consumer.** Remove its public key and re-issue, **and rotate the credentials it could
decrypt.** Earlier versions of the file stay in git history, readable by the removed key, so
re-issuing alone revokes nothing already exposed.

**Rejected in review.**

| Option | Why not |
|---|---|
| **SOPS with age** | The same key model, with values encrypted per key and an Ansible collection (`community.sops`) to write them. But `sops` isn't in the site's configured package repositories, so it would be one more binary to stage. |
| **The Deevnet API issues the credentials** | This prepares for short-lived tokens. But the API would have to serve TSIG and state keys owned by other roles, and the one-time enrollment secret still has to be delivered somehow. |
| **One age key per tenant** | Simpler, but a leak anywhere means rotating everywhere. |

### 10. The API confines topics by writing the tenant's prefix itself

*Decided 2026-09-16 (Open question 4).*

**Decision.**
- **A tenant declares topic patterns relative to its prefix.** eds declares
  `lightstand/+/scene`, and the API stores `eds/lightstand/+/scene`.
- **The API validates each pattern before prefixing it.** It refuses a pattern that:
  - is empty, or starts with `/` or `$`
  - uses `#` anywhere except as the whole last level, or `+` anywhere except as a whole level
  - contains `%`, which starts a VerneMQ template variable. v1 doesn't need them: the API chooses
    usernames, so `%u` has nothing to offer a tenant.
- **The API never writes `modifiers`**, and no provider attribute can set them.

**Why the prefix holds.**
- **The first level is always literal.** Every stored pattern starts with the tenant's name as a
  literal level, and MQTT wildcards can't reach past a level:
  - *"The plus sign (‘+’ U+002B) is a wildcard character that matches only one topic level."*
    Where it is used, *"it MUST occupy an entire level of the filter [MQTT-4.7.1-3]"*.
  - The multi-level wildcard *"MUST be the last character specified in the Topic Filter
    [MQTT-4.7.1-2]"*.
  - Source: [MQTT 3.1.1 §4.7](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).
  - So `eds/#` matches topics under `eds`, and never under another tenant's name.
- **The prefix does the confining.** Refusing a leading `/`, a leading `$` or a malformed wildcard
  is hygiene. Once prefixed, each of those would still sit under the tenant's name, but none means
  what the tenant intended.

**Why not modifiers.** Open question 4 listed modifiers as a way to rewrite topics into the prefix.
They can't do that:
- **They replace values; they don't prefix them.** VerneMQ documents a publish ACL modifier as
  `"modifiers": {"topic": "new/topic", "payload": "new payload", "qos": 2, "retain": true,
  "mountpoint": "other-mountpoint"}`
  ([VerneMQ database auth](https://docs.vernemq.com/configuring-vernemq/db-auth)).
- **A fixed topic can't map a wildcard pattern into a prefix.**
- **A modifier can move a message out of the prefix.** It can set any topic or another mountpoint.
  That makes it a way around confinement, which is why the API never writes one.

**Why the API prefixes rather than only refusing.** Refusal alone would also confine: the tenant
writes `eds/…` and the API rejects anything else. Prefixing does the same job and leaves the tenant nothing to get
wrong.

**What the API writes for each account.** One row in the plugin's `vmq_auth_acl` table:
- **Mountpoint:** the default, `''`, as in the plugin's own example.
- **Username:** derived by the API from the tenant and the account name, so no two tenants collide.
- **Password:** the bcrypt hash (§8).
- **ACLs:** the prefixed publish and subscribe patterns.
- **Client ID:** `*`.
  - The plugin looks a client up with
    `WHERE mountpoint=$1 AND (client_id=$2 OR client_id='*') AND username=$3`
    (`apps/vmq_diversity/priv/auth/postgres_cockroach_commons.lua`, unchanged at tag 2.2.0).
  - So an account isn't tied to a client ID, and a tenant doesn't declare one.
  - The password still has to match.

---

## Consequences

**ADR-0010's failing rows become conformant once this is built.** Registering a device, and
granting it topics and a Wi-Fi key, become `terraform apply` in the tenant's repository. Until then
they stay recorded debt.

**The substrate gains a privileged service.** The API holds credentials that can rewrite the
site's wireless configuration, and write access to every broker account. Its authentication and
audit log are platform responsibilities. A compromised API is a site-wide compromise of those
services.

**The broker's auth database is in the connection path; the API is not** (§8).
- **An API outage** stops provisioning, never devices.
- **The auth database carries that weight instead.** While it's down, devices already connected are
  expected to keep their cached ACLs, but new connections can't authenticate until it's back. See
  [To confirm when building](#to-confirm-when-building).
- **It fate-shares with the broker.** It runs in the messaging VM with the broker, so
  maintenance on the provisioning VM never takes it down (§7).

**The platform gets a record of what changed.** ADR-0010 noted that a service tenants change
without commits needs its own record, and that none had one. The API's audit log is that record
for IoT.

**A substrate rebuild costs tenants an apply, not devices a visit** (§5). Only losing the API's
database and a tenant's state together forces re-provisioning. That puts more weight on
ADR-0007's state custody.

**The provider carries a documented exception to its framework** (§5). Restore-instead-of-recreate
is deliberate, limited to secret-bearing resources, and tested.

**Deevnet owns a public schema.** A breaking provider change needs versioning discipline like
`tenant-module-vX.Y.Z` (ADR-0006), and a deprecation path. The repository and releases meet public
registry requirements from the first tag (§7).

**Tenant operators stop reading the substrate vault** (§9). This changes delivery for ADR-0004's
TSIG key and ADR-0007's state key, not what they are or who issues them. The tenant provisioning
runbook and the tenant Makefiles change on acceptance.

**Tenants get an offline policy the standard doesn't require** (§7). Correctness §5.4 limits
air-gap to the substrate. This record sets offline `terraform init` for tenants.

**Deevnet builds and patches its own broker** (§8). A from-source VerneMQ build is ours to keep
current, in a smaller project with a slower release cadence than EMQX.

**It is the first service placed where the declared policy expects.** Today's tenant-facing
services, tenant DNS and state, sit on the management segment. Tenants reach them only because the
core router currently passes everything (ADR-0011 → Validation). This record doesn't move them, but
it shouldn't repeat that.

**`DVNTM-IOT` was a creation, not a migration.** *Corrected 2026-09-18.* This entry used to say
that moving the IoT SSIDs off a shared key needed a change record that solved a coexistence problem.
For VLAN 30 that premise was wrong: CHG-0005 held the `iot` segment out of `omada-wireless.yml`
while its security model was undecided, so **`DVNTM-IOT` never existed on the controller and no
device was ever on its shared key**. There was nothing to convert, no coexistence window and nothing
to re-flash. [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) created it as PPSK from the
start, and `deevnet_wifi_psk.iot` was deleted rather than migrated away from.

**`DVNTM-IOTV` still has the problem, and still needs its own change record.**
- **Today:** it is WPA-Personal on one shared key from `deevnet_wifi_psk`, and it has devices.
- **What won't do it:** `omada-wireless.yml` doesn't rewrite existing objects. Its header says
  *"existing objects that differ are reported, not rewritten."* Converting it means deleting and
  recreating the SSID.
- **What's at stake:** devices on the shared key keep working only while that key is accepted. The
  Ma Bell gateway's key is in NVS, written over USB.
- **Two ways through:** re-provision every device onto a tenant key once, or run the shared-key SSID
  beside a PPSK one until each device has moved.
- **The drift check will now say so.** Since CHG-0013 the play compares an SSID's `security` as well
  as its VLAN, so declaring `iot_vendor` as ppsk without converting it reports the mismatch instead
  of passing silently.

**Two narrow zone rules are added when the API is built** (§7):
- `platform -> management`: the provisioning VM to the Omada controller's Open API port.
  **Declared by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/).** It is declared rather
  than applied, because the core router still passes everything
  ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) has never run). Declaring it now
  matters precisely because nothing enforces it: when the zone policy is finally applied, an
  undeclared path would break key issuance as a *timeout inside a tenant's `terraform apply`*,
  which is among the worst signals to debug.
- `platform -> iot_backend`: the provisioning VM to the broker's auth database port. Still pending
  — there is no broker.

They are the only paths the API needs beyond the declared policy, and each is limited to one host
and one port.

**It depends on data-plane work, some of which is now done.** As of 2026-09-18:
- PPSK is **proven on the AP** ([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) phase 6)
  and `DVNTM-IOT` is created and served
  ([CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/))
- the broker still doesn't answer, so broker accounts remain unbuilt
- the IoT segments still aren't enforced, pending [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)

An API over a data plane that doesn't enforce anything confines nothing that matters. That remains
true of the segment boundary: a tenant's key decides which VLAN its devices land on, but nothing yet
stops that VLAN reaching another.

**Building it is real work:**
- the provisioning and network management VMs on `dv02hyp001p01`, and VLAN 25 on that hypervisor's
  switch port ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/))
- the API service
- a provider on the Terraform Plugin Framework in Go (the Builder already provides Go)
- a VerneMQ build
- a mirror in the artifacts role
- the credentials issuance target

---

## Open questions

1. **Can a custom Omada role narrow the API's own controller credential?** This is defense in depth
   for §2, not tenant scoping. It wasn't checked.
2. **Where does the API's database live, and how is it backed up?** *Answered 2026-09-14:* with the
   API, as a container in the provisioning VM on the management hypervisor (§7). How it's backed up is deferred.
   Since §5, a backup is a convenience that avoids a round of tenant applies, not what keeps
   devices online.
3. **How does a registry entry relate to ADR-0011 open question 2?** **Answered 2026-09-15.**
   ADR-0011 question 2 was decided: an application-owned device takes no substrate host record. It
   leases from the IoT pool and is named in its owner's own zone, so a registry entry is the
   device's identity and the provider composes with the existing `hashicorp/dns` path rather than
   wrapping DNS.
4. **Where is topic confinement enforced?** **Answered 2026-09-16** (§10):
   - The API enforces it. A tenant declares patterns relative to its prefix, and the API validates
     each one and writes the prefix itself.
   - Modifiers were ruled out. They set fixed values, so they can't add a prefix, and they could
     move a message out of one.
5. **Is the broker's auth database the API's own database, or a separate one?** *Answered
   2026-09-14:* a separate one, beside the broker in the messaging VM, so it
   fate-shares with the broker rather than with the API (§7). Only the API writes it, and the broker's credential is
   read-only.
6. **How does the API reach the Omada controller?** *Answered 2026-09-14:* the controller's official
   home becomes a container in the network management VM on the management hypervisor
   ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)), and the API
   reaches it over a narrow `platform -> management` rule, from the provisioning VM to the
   controller's Open API port only (§7).

## To confirm when building

These aren't open decisions. They are claims this record relies on that only an implementation can
prove.

- **A tampered provider package is refused** when installed from the filesystem mirror against a
  committed lock file (§7).
- **The restore path works end to end** (§5). Delete an object at the API, apply, and confirm the
  device reconnects with its existing secret.
- **VerneMQ builds from source on the Builder** into a stageable image that includes
  `vmq_diversity` and the chosen database driver (§8).
- **Devices that are already connected keep working through an auth-database outage**, on their
  cached ACLs, and new connections are refused rather than let in (§8, Consequences).
- **The public registry namespace comes out as `deevnet`** before the provider is first published
  (§7).
- **A self-hosted CI runner decrypts the credentials file with its own key**, and reaches the API
  and the mirror (§9).
- **A tenant account asking for more than its prefix is refused** (§10).
  - VerneMQ compares a subscription's filter with the account's ACL patterns. The documentation
    doesn't say what happens when the filter is wider than every pattern, so test it.
  - Test cases: a subscription to `#` or `+/…`, and a publish to another tenant's topic.

---

## Current state

- **Accepted 2026-09-18**, at the close of
  [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) — when the Wi-Fi half had been built,
  deployed and proven on the AP rather than when it was written.
- **Built and live: the Wi-Fi half.** `DVNTM-IOT` exists as a PPSK SSID on VLAN 30, bound to a
  profile inventory creates empty. The API issues, restores and revokes one key per tenant per trust
  class; the `eds` tenant holds `eds-devices` from its own `terraform apply`, and no tenant reads a
  Wi-Fi key from the substrate vault any more. `deevnet_wifi_psk.iot` was deleted rather than
  migrated away from.
- **Built and live: the device registry.** `deevnet_iot_device` is in the API and the provider
  ([CHG-0014](/docs/changes/2026/0014-tenant-device-registry/)), ordered first by
  [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/). *Updated
  2026-09-23: this line read "Written, not yet deployed … the route still answers `501`", which was
  true when written and wrong from 2026-09-20, when CHG-0014 deployed v0.4.0. The registry answers;
  `mabell` holds `ma-bell-gw-01` in it.*
- **Built and live: broker accounts.** The API issues a tenant's MQTT account against the broker's
  own auth database ([CHG-0016](/docs/changes/2026/0016-broker-accounts/)), and no broker account or
  topic permission remains in substrate inventory — [CHG-0017](/docs/changes/2026/0017-retire-mosquitto/)
  deleted the last of them. Four accounts exist on the broker today: eds's two, mabell's gateway, and
  the log bridge's, which is the only one the substrate writes rather than the API
  ([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/) §4). *Updated 2026-09-23: this
  line read "Not built … because there is no broker", which stopped being true on 2026-09-20 when
  CHG-0015 built VerneMQ and CHG-0016 deployed the account writer.*
- **The segment boundary is enforced.** *Updated 2026-09-20.*
  [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) completed 2026-09-19: the core router
  applies default-deny between zones, and the `platform -> management` rule the API needs is live
  rather than merely declared. A tenant's key still decides only which VLAN its devices land on —
  two tenants' devices share VLAN 30 and reach each other at Layer 2, which no zone rule can fix
  (ADR-0020, *Peer devices on a shared segment*).
- **Both rules §7 promised are live.** `platform -> management` and
  `platform -> iot_backend: deevnet-api -> broker account writer` (port 22) are both in the router's
  managed rules, confirmed against the live router on 2026-09-23. *Updated 2026-09-23: this line read
  "One rule §7 promised is still missing", which was the finding that
  [CHG-0016](/docs/changes/2026/0016-broker-accounts/) then fixed on 2026-09-20 — an undeclared path
  fails as a timeout inside a tenant's own `terraform apply`, which is why it was worth recording
  and is worth recording that it is closed.*
- **Still open: open question 1** — whether a custom Omada role can narrow the API's own controller
  credential. It is defense in depth for §2, not tenant scoping, and it has never been checked.
  *Corrected 2026-09-19: this line previously read "open question 1 (device-to-tenant ingress)",
  which mislabeled it — ingress is ADR-0011's open question 5, now answered by
  [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/). The real
  open question 1 was consequently tracked nowhere.* The same unchecked item is also recorded at
  ADR-0010 and ADR-0011 open question 3.
- [ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/) is still
  Proposed — accepting this record ahead of the one it extends is deliberate: ADR-0010 states a
  principle, and this is the first service that actually satisfies it.
- Reviewed on 2026-09-14 (four of eight open questions decided: §4, §5, §7, §8, §9), revised the
  same day to make the API provisioning-only, then questions 2, 5 and 6 answered (§7, ADR-0013),
  question 3 on 2026-09-15 and amended 2026-09-18, and question 4 on 2026-09-16 (§10).
