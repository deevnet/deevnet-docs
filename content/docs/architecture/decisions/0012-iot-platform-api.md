---
title: "ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider"
weight: 12
---

# ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-14 |
| **Reviewed** | 2026-09-14. Four of the original open questions were decided in review: the broker (§8), secrets after a rebuild (§4, §5), provider distribution (§7) and credential delivery (§9). The sources are quoted in each section. |
| **Scope** | How a tenant reaches an IoT platform service whose own interface can't confine it to its scope, and what the substrate builds so it can |
| **Extends** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §1 and §3, which require a scoped service but don't say how one is built when the backing software can't scope itself |
| **Answers, in part** | [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/) open questions 1 (scoped registration) and 3 (per-device Wi-Fi keys) |
| **Related** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/), [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/) |

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

### How a tenant, its devices and platform services connect

A tenant and its devices reach the platform by **different paths**. The tenant is never reached
*through* an IoT VLAN:

```
  TENANT FABRIC                 CORE ROUTER             SHARED SERVICES
  one VRF per tenant            zone policy (CHG-0007)

  tenant A ─┐  exit node   tenant      ┌────────────►  Platform (25): Deevnet API
            ├─► (SNAT) ──► transit ────┤                 ▲  broker's auth hooks call the API
  tenant B ─┘              VLAN 50     └────────────►  IoT Backend (35): broker
                                                         ▲
  ACCESS NETWORK                                         │
  device, tenant A ─┐                                    │
                    ├─► IoT, VLAN 30 ────────────────────┘
  device, tenant B ─┘   (shared Layer 2)

  IoT Vendor, VLAN 31: outbound internet only, nothing internal
  tenant ↔ device: no path either way; both dial out to the broker
```

**The three paths.**
- **Tenant workloads** leave their VRF through the fabric's exit node, SNATed onto the **tenant
  transit** VLAN (50), and reach Platform and IoT Backend over `tenant_transit -> platform` and
  `tenant_transit -> iot_backend`
  ([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) Seam 1,
  [ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)).
- **Devices** attach to the access VLAN of their trust class
  ([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) §3), not their
  tenant's, and reach the broker over `iot -> iot_backend`.
- **There is no path between a tenant and a device.** Tenants have no inbound path (ADR-0003), and
  device-to-tenant ingress is a future record (ADR-0011 open question 5). The broker is where they
  meet, and both sides dial out to it.

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

### 1. Two planes; the tenant sees only the control plane

```
                      DEEVNET IoT PLATFORM SERVICES
 ┌───────────────────────────────────────────────────────────────┐
 │ CONTROL PLANE        Deevnet API  ·  Terraform provider       │
 │                                                               │
 │  v1:     device registry · Wi-Fi key binding ·                │
 │          broker account binding                               │
 │  later:  identity/PKI · policy · firmware release hosting ·   │
 │          OTA/jobs · observability      (each its own record)  │
 └───────────────────────────────┬───────────────────────────────┘
                                 │ holds the backing credentials;
                                 │ confines every call to one tenant;
                                 │ answers the broker's auth hooks (§8)
 ┌───────────────────────────────┴───────────────────────────────┐
 │ DATA PLANE           substrate implementations, never         │
 │                      tenant-facing                            │
 │                                                               │
 │  Wi-Fi controller + IoT VLANs · MQTT broker (VerneMQ) ·       │
 │  DNS/DHCP · artifacts                                         │
 └───────────────────────────────┬───────────────────────────────┘
                                 │ devices use data-plane services
                                 │ only
                    application-owned edge devices
                                 │
 ┌───────────────────────────────┴───────────────────────────────┐
 │ TENANT / APPLICATION                                          │
 │                                                               │
 │  firmware · signing keys · backend services ·                 │
 │  Terraform (desired state and device secrets)                 │
 └───────────────────────────────────────────────────────────────┘
```

- **The API is the only tenant-facing control surface for IoT services.** The Omada controller and
  the broker's administrative interface are implementations behind it. No tenant holds their
  credentials.
- **Devices never call the control plane.** They connect to Wi-Fi and the broker as they do today.

### 2. Scope is enforced by the API, and issued once

- **One credential at onboarding.** At onboarding the substrate issues each tenant one API
  credential. It is the same act, and the same shape, as the TSIG key (`vault_tenant_tsig_keys`)
  and the state key (`vault_tenant_state_keys`). It is delivered as §9 describes.
- **Every object belongs to exactly one tenant.** The API refuses any read or write outside the
  calling tenant's objects.
- **The backing credentials are the API's alone**, held by the substrate: the Omada Open API client,
  and the broker's hooks answered by the API (§8).

This is how ADR-0010 §3 is met for a service whose own interface can't meet it. The confinement is
a control enforced by the API, not a convention, because the tenant never holds a credential that
could go around it.

### 3. Version 1 is a registry and two bindings

v1 covers exactly the actions that fail ADR-0010's test. Resource names below are working names.

| Resource | What it is | Confined by the API to |
|---|---|---|
| `deevnet_iot_device` | A registry entry: name, trust class (`iot` or `iot_vendor`), optional MAC | The calling tenant |
| `deevnet_iot_wifi_key` | A per-device PPSK key | **The VLAN of the device's trust class.** The tenant can't choose a VLAN, so no tenant network ever reaches the air (ADR-0011 Option B stays rejected). |
| `deevnet_iot_broker_account` | An MQTT account for the device, with its topic permissions | Topics under the tenant's prefix, `<tenant>/…`. The existing ACLs already follow this: `eds/lightstand/…`. **Devices of trust class `iot` only.** |

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
  - For the broker, the API keeps only what authentication needs: a password hash.
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
    `ppskList[].psk` (*"Password, should contain 8 to 63 visible ASCII characters."*), and the broker
    checks passwords through the API (§8), which re-hashes the restored one.
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
  to recognise API-owned keys as expected rather than list them as drift.
- **This extends ADR-0009 for one object class; it does not supersede it.**

### 7. Placement, and how the provider reaches tenants

*Distribution decided in review, 2026-09-14.*

**Placement.**
- The API runs as a substrate platform service on the platform segment.
- Tenants reach it over `tenant_transit -> platform`, which the declared zone policy already allows.
- Operators reach it from management.
- Nothing on the IoT segments needs a path to it. The broker's auth hooks call the API from
  IoT Backend, over `iot_backend -> platform`, which is also declared.

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
  artifact server.
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

### 8. The broker is VerneMQ, built from source, and it asks the API

*Decided in review, 2026-09-14.*

**The requirements set in review:**
- **Devices authenticate with a username and password**, over TLS. That is how the LP stand works
  today, and it keeps identity and PKI a later layer.
- **The broker asks the API (pull), rather than the API writing into the broker (push).** On
  connect, subscribe and publish, the broker calls the API. The broker then holds no tenant state,
  there is one source of truth, and a rebuild restores only the API.
- **A brief outage is acceptable.** While the API is down, reconnecting devices may fail. A single
  API instance is fine for v1.
- **Design for growth.** v1 is one node, but the broker must be able to cluster later.

**Why VerneMQ.**
- **Its source is Apache-2.0**, and the project describes itself as *"a distributed MQTT message
  broker"*. It states *"The VerneMQ mission is active & the project maintained"*
  ([GitHub](https://github.com/vernemq/vernemq)). The current release is 2.2.0, published
  2026-08-09, following 2.1.1 on 2025-07-14 (GitHub releases API).
- **Its webhooks are the pull model, natively**
  ([VerneMQ webhooks](https://docs.vernemq.com/plugin-development/webhookplugins)):
  - `auth_on_register`, `auth_on_subscribe` and `auth_on_publish`, with MQTT 5 variants
  - the register call carries `username` and `password`, so the API verifies the password itself
  - the endpoint allows with `{"result": "ok"}` and denies with `{"result": {"error": "not_allowed"}}`
  - subscribe and publish responses can rewrite topics, which is one way to enforce the tenant
    prefix (Open question 4)
  - HTTPS to the endpoint is supported (`vmq_webhooks.cafile`, `.certfile`, `.keyfile`,
    `.verify_peer`)
- **It covers the brief-outage tolerance.** Decisions are cached when the API returns
  *"`cache-control: max-age=AgeInSeconds`"*.
- **Caveat on the cache.** Entries *"are currently not actively disposed after expiry"*, so memory
  use under churn is something to watch.
- **Built from source, not from the official images.** *"To use the provided docker images the
  VerneMQ EULA must be accepted"*
  ([VerneMQ Docker](https://docs.vernemq.com/installing-vernemq/docker)). The 2.2.0 release notes put
  the binary packages and images under that EULA too. Building from the Apache-2.0 source avoids the
  question, and the Builder already builds and stages images.

**Rejected in review.**

| Broker | Why not |
|---|---|
| **EMQX** | A strong fit technically: HTTP authentication with per-client ACLs, and HTTP authorization. But from 5.9 it is under the Business Source License. EMQ's FAQ: *"You may run single-node (any size) instances of EMQX in production for free, as long as you do not offer EMQX itself 'as‑a‑service'"*, and *"You cannot connect multiple nodes into a cluster (clustering requires a commercial license)"* ([EMQX licensing FAQ](https://www.emqx.com/en/content/license-faq)). That fails the growth requirement. Its last Apache-licensed line, 5.8, reached end of life on *"February 28, 2026"*, after which EMQ *"will no longer provide … bug fixes, security patches"* ([EMQ notice](https://www.emqx.com/en/news/a-notice-on-the-emqx-5-8-open-source-version)). |
| **Mosquitto** (today's broker) | No maintained way to ask an external API: the third-party `mosquitto-go-auth` plugin was archived by its maintainer in June 2025, per its package page. The pull model would mean writing our own plugin on the hooks Mosquitto 2.1 added (2026-02-05). Clustering and high availability are sold by Cedalo as Pro Mosquitto features, not open-source ones. |

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

---

## Consequences

**ADR-0010's failing rows become conformant once this is built.** Registering a device, and
granting it topics and a Wi-Fi key, become `terraform apply` in the tenant's repository. Until then
they stay recorded debt.

**The substrate gains a privileged service.** The API holds credentials that can rewrite the
site's wireless configuration, and it decides every broker connection. Its authentication, audit
log and availability are platform responsibilities. A compromised API is a site-wide compromise of
those services.

**The API is in the broker's connection path.** Under the pull model (§8), an API outage stops
reconnecting devices once cached decisions expire. That was accepted for v1 in review. An HA API is
the remedy if it stops being acceptable.

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

**Moving the IoT SSIDs from a shared key to per-device keys needs its own change record.**
- **Today:** the IoT SSIDs are WPA-Personal on one shared key per segment (`deevnet_wifi_psk`).
- **What won't do it:** `omada-wireless.yml`, which creates them from inventory, doesn't rewrite
  existing objects. Its header says *"existing objects that differ are reported, not rewritten."*
- **What's at stake:** devices already on the shared key keep working only while that key is
  accepted. The Ma Bell gateway's key is in NVS, written over USB.
- **Two ways through:** re-provision every device onto its own key once, or run the shared-key SSID
  beside the PPSK SSID until each device has moved.
- **When:** that change record depends on the ADR-0011 device test, so it follows CHG-0005.

**It depends on data-plane work that isn't done.** As of 2026-09-14:
- the broker doesn't answer
- PPSK is untested on the AP, pending [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)
- the IoT segments aren't enforced, pending [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)

An API over a data plane that doesn't enforce anything confines nothing that matters.

**Building it is real work:**
- the API service
- a provider on the Terraform Plugin Framework in Go (the Builder already provides Go)
- a VerneMQ build
- a mirror in the artifacts role
- the credentials issuance target

---

## Open questions

1. **Can a custom Omada role narrow the API's own controller credential?** This is defence in depth
   for §2, not tenant scoping. It wasn't checked.
2. **Where does the API's database live, and how is it backed up?** Since §5, a backup is a
   convenience that avoids a round of tenant applies, not what keeps devices online.
3. **How does a registry entry relate to ADR-0011 open question 2?** A device could still have a
   substrate host record, or lease from the IoT pool and be named in its owner's zone. The provider
   could compose with the existing `hashicorp/dns` path rather than wrap DNS.
4. **Where is topic confinement enforced?** The API can deny out-of-prefix topics in its hook
   responses, or rewrite them into the tenant's prefix (VerneMQ's modifiers allow either), or both.

## To confirm when building

These aren't open decisions. They are claims this record relies on that only an implementation can
prove.

- **A tampered provider package is refused** when installed from the filesystem mirror against a
  committed lock file (§7).
- **The restore path works end to end** (§5). Delete an object at the API, apply, and confirm the
  device reconnects with its existing secret.
- **VerneMQ builds from source on the Builder** into a stageable image, and its webhook cache stays
  bounded under reconnect churn (§8).
- **The public registry namespace comes out as `deevnet`** before the provider is first published
  (§7).
- **A self-hosted CI runner decrypts the credentials file with its own key**, and reaches the API
  and the mirror (§9).

---

## Current state

- **Proposed.** Nothing is built.
- The broker accounts and topic permissions remain in substrate inventory as ADR-0010 debt. No
  Wi-Fi keys are per device, and tenants still read their keys from the substrate vault.
- Reviewed on 2026-09-14. Four of the original eight open questions were decided (§4, §5, §7, §8,
  §9), and four remain.
- **Acceptance waits on:**
  - ADR-0010 and ADR-0011
  - Open question 3, which ties to ADR-0011 open question 2
  - the data-plane changes above: CHG-0005 and CHG-0007
