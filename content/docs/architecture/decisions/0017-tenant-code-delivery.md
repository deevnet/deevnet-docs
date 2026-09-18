---
title: "ADR-0017: How Tenant Code Reaches a Tenant Workload"
weight: 17
---

# ADR-0017: How Tenant Code Reaches a Tenant Workload

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-18 |
| **Revised** | 2026-09-18, before review. First written as a single choice between delivery mechanisms, with tenant-authored cloud-init user-data recommended. Rewritten to separate the **tenant-facing contract** from the **substrate-side mechanism**: the contract is Deevnet-shaped and settled (§1), the mechanism is a separate and still-open question (§2). The first draft argued the wrong layer. |
| **Scope** | How a tenant's own application code and configuration arrive on a tenant workload, and how they are kept current — not what the code is, and not how the workload itself is built |
| **Extends** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), which says tenants own their code but does not say how it is delivered; [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), which builds the empty workload this decision fills |
| **Related** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0011: Edge Devices Are Application-Owned](/docs/architecture/decisions/0011-edge-devices-application-owned/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/) |

---

## Context

### The substrate can build a workload but cannot fill one

[ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) made tenant building
complete: a tenant declares `deevnet_workload` and gets a running Fedora VM with an address, a
name, DNS and egress. What arrives is an **empty machine**. Nothing in the substrate puts an
application on it, and nothing says how a tenant should.

This is the first question the EdS tenant hits. Its repository holds real code — a Python palette
service, a Go `lightd`, ESP-IDF firmware — and a built, running, empty VM to put none of it on.

### A tenant has no inbound path, so nothing can push

This is the constraint that removes most of the obvious answers.

[Shared Tenant Services](/docs/architecture/tenant/shared-services/) states it plainly: a tenant
has no inbound path. It was confirmed directly — the Builder cannot reach a tenant workload at all.
Tenant traffic leaves through the fabric's exit node, SNATed
([ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)); nothing
returns unbidden.

The substrate's own deployment pattern is Ansible plus the `podman_service` role, pushed from the
control node. **That pattern cannot reach a tenant workload**, and it should not: it is
substrate-side, and [ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/)
and [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) are explicit that
tenants own their code the way an AWS customer owns theirs.

The one exception proves the rule. The hypervisor hosting the fabric *can* reach into a tenant's
VRF — `ip vrf exec vrf_eds ping 10.20.130.10` succeeds from the exit node. But that is the
substrate reaching into a tenant, available only to whoever holds root on a hypervisor. It is not a
path a tenant can use, and building on it would rebuild exactly the coupling ADR-0015 removed.

**So delivery must be a pull, initiated from inside the workload.** That much is forced.

### What a workload can do today

Three things are newly true, and they matter:

- **Name resolution works.** Until [CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/),
  every tenant workload was given an authoritative-only DNS server and could resolve nothing but
  its own tenant's names. It now resolves public names, substrate names and tenant names alike.
- **Outbound HTTPS works.** Verified along the tenant VRF's own default route and SNAT:
  `quay.io` 200, `registry.fedoraproject.org` 302, `github.com` 200. The declared zone policy keeps
  this — `tenant_transit` is in `firewall_internet_zones` — so
  [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) does not take it away.
- **The base image already carries podman and cloud-init**, with the cloud-init units enabled
  (image factory, `fedora.pkr.hcl`).

A tenant workload can therefore pull and run containers, and call the Deevnet API, the moment it
boots. The missing piece is narrow: **how it is told what to run.**

### What the substrate can inject, verified

The Deevnet API configures a workload through the PVE API, and by deliberate rule it
**writes through that API and never files on a hypervisor**. What that permits was checked rather
than assumed, on the tenant hypervisor:

| Channel | Available through the PVE API? |
|---|---|
| Native cloud-init fields (`ciuser`, `sshkeys`, `nameserver`, `ipconfig0`) | Yes — used today |
| `cicustom` user-data | **No.** It points at a snippet file on a storage. `pvesm status -content snippets` returns nothing, and no storage endpoint writes one: upload accepts only `import`, `iso`, `vztmpl`, and content POST allocates disk images. |
| `smbios1` — `serial`, `product`, `sku`, `family`, `version` | **Yes.** Settable on the config endpoint, base64, no file writes. Readable in-guest from `/sys/class/dmi/id/`. |

So arbitrary user-data is not merely unconfigured, it has **no API-only path at all** on this
Proxmox version. Any mechanism that depends on it must first resolve that, by enabling snippets
storage the API can write to some other way, or by relaxing the rule.

Both `cicustom` and `smbios1` share a property worth stating plainly: whatever they carry is
**readable by anyone with sufficient PVE privilege**, and neither is covered by
[ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)'s sealing. Neither is a
place for a tenant's long-lived secrets.

### Statelessness is the intended shape

The operator's stated direction is that tenant workloads stay **as stateless as possible**, so that
replacing one is the ordinary repair rather than a loss. A delivery mechanism that reconstructs the
workload from scratch on every boot reinforces that; one that mutates a long-lived machine works
against it.

It also has a sharp edge today. A tenant has **no way to restart a workload in place**; the only
lever the provider offers is replace, which destroys the disk
([CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/) follow-up). A mechanism that needs a
reboot to take effect therefore needs a rebuild, and that is only acceptable while workloads hold
nothing.

---

## Options considered

The first draft of this record treated delivery as one choice. It is two, and conflating them is
what made a Proxmox implementation detail look like a tenant-facing decision.

### Part 1 — What does a tenant declare?

**1a. Proxmox-shaped.** The tenant supplies raw cloud-init user-data, passed through to `cicustom`.

- **For:** no schema to design; anything cloud-init supports works on day one; portable knowledge.
- **Against:** it puts Proxmox in the tenant contract. A tenant would be writing to the hypervisor's
  format, so the substrate could never change mechanism without breaking every tenant — the exact
  coupling ADR-0015 removed for networks, workloads and names. It also means the tenant-facing
  contract inherits `cicustom`'s problems, including that it is a readable file.

**1b. Deevnet-shaped.** The tenant declares configuration to the Deevnet API in a Deevnet-owned
schema. The API decides how to realise it.

- **For:** the tenant never learns that Proxmox exists, consistent with everything else it
  declares; the substrate may change mechanism freely; the API can validate, constrain and reject —
  size limits, and refusing secrets in a field that cannot hold them safely; it can also supply what
  the substrate requires rather than trusting a tenant to.
- **Against:** a schema to design and maintain; expressiveness has to be chosen deliberately rather
  than inherited; a tenant wanting something the schema omits has to ask for it.

**1c. Nothing declared.** Convention only: the workload always runs a container derived from its
tenant and workload name.

- **For:** the smallest possible contract.
- **Against:** rigid — one container, no configuration, no environment, no registry choice. A
  naming convention is a weak contract to hang a platform on.

### Part 2 — How does the substrate realise it?

**2a. cloud-init user-data via `cicustom`.** The API renders the declaration into user-data and
places it as a snippet.

- **For:** the industry-standard mechanism; declarative; runs before anything else; a replaced
  workload rebuilds itself identically.
- **Against:** **no API-only path exists** (see above), so it needs snippets storage the API can
  reach some other way, which is new substrate machinery with its own lifecycle; the snippet is
  readable, so it cannot carry secrets; and it runs **once**, so it delivers but does not maintain.

**2b. Bootstrap pointer in `smbios1`, configuration fetched from the API.** The API writes a
pointer and a single-use bootstrap token into an SMBIOS field. An agent in the base image reads it
at boot and fetches the real configuration from the Deevnet API over TLS.

- **For:** needs no snippets storage and no files on a hypervisor — it is a config-endpoint field,
  available today; **secrets never touch substrate storage**, because they arrive over an
  authenticated channel, which is the strongest argument for it; the agent can re-check on a timer,
  so it maintains as well as delivers; the API sees each workload check in, which is observability
  the other options do not give.
- **Against:** the substrate now ships and owns an agent in the base image that runs
  tenant-supplied configuration — a real ongoing responsibility and an obvious blast radius; it is a
  Deevnet-specific mechanism where 2a is a standard one; SMBIOS fields are small and readable, so
  the token must be genuinely single-use; and it adds a boot-time dependency on the API being up,
  which ADR-0012's provisioning-only stance has so far avoided.

**2c. Tenant-built images.** The tenant builds a VM image containing its application.

- **For:** nothing to deliver at run time; correct the instant it boots; strongest statelessness.
- **Against:** puts tenant-built artifacts in substrate storage and makes the substrate host a
  tenant build pipeline, reversing ADR-0010's direction; every change becomes an image build plus a
  workload replace. A tenant baking its own **container** images is different, and expected.

**2d. A tenant-run deployer inside its own fabric.** One workload deploys the others.

- **For:** entirely tenant-owned; scales to a tenant with many workloads.
- **Against:** it relocates the problem rather than solving it — the deployer is itself an empty VM
  that one of the above must fill. A sensible later pattern; it cannot be the base case.

---

## Decision

### §1 — The contract is Deevnet-shaped, and this part is settled

A tenant declares its workload configuration **to the Deevnet API, in a Deevnet-owned schema**
(option 1b). It does not supply Proxmox user-data, and nothing in the tenant-facing contract names
a hypervisor mechanism.

This follows directly from ADR-0015. A tenant already declares a network without knowing about SDN
zones and a workload without knowing about templates or VMIDs; configuration is the same kind of
thing. Putting `cicustom` in the contract would make a Proxmox implementation detail permanent and
tenant-visible, and would prevent exactly the mechanism change that §2 leaves open.

### §2 — Delivery is a pull; the mechanism is open, and 2b leads

**Forced, not chosen:** delivery is a **pull initiated from inside the workload**. No push
mechanism may be introduced, and the substrate's Ansible and `podman_service` pattern must not be
extended to tenant workloads.

**The mechanism is genuinely undecided.** The leading candidate is **2b**, the SMBIOS bootstrap
pointer with configuration fetched from the API, for three reasons that emerged from checking
rather than reasoning:

1. It is the only option with an **API-only path that exists today**. 2a has none.
2. It is the only option where **secrets never sit on substrate storage**, which is what blocks the
   EdS broker work, where `lightd` needs a broker credential.
3. It **maintains as well as delivers**, because the agent can re-check.

Against that, it makes the substrate own an agent, and it puts the API in the workload's boot path.
Those are real costs and they are why this is `Proposed` rather than decided. **2a remains viable**
if snippets storage is worth building, and it has the considerable merit of being the mechanism
everyone already knows.

2c is rejected as the base case; 2d is recorded as a later pattern for a large tenant; 1c is
rejected as too rigid to build on.

---

## Consequences

- **The `deevnet_workload` resource grows a configuration attribute**, in a Deevnet schema. That
  schema is a new tenant-facing contract and needs its own versioning discipline.
- **The substrate owes the tenant a documented vocabulary** — what can be declared, what cannot,
  and what the API supplies itself. Under 1b a tenant cannot simply reach for a cloud-init feature.
- **Under 2b the base image gains an agent**, which makes the image a participant in tenant
  delivery rather than a neutral starting point, and puts it on the upgrade treadmill.
- **Under 2b the API enters the boot path.** ADR-0012 made the API provisioning-only on purpose, so
  that nothing at runtime depends on it. A workload that fetches configuration at every boot
  weakens that, and the failure mode — a workload that reboots while the API is down — must be
  decided rather than discovered.
- **A tenant's workload becomes reproducible from its declaration alone**, which makes the
  statelessness goal real rather than aspirational.
- **Restart-in-place becomes more pressing.** A configuration change takes effect on a boot, and
  today the only boot a tenant can cause is a replace.
- **Nothing here gives a tenant a way in.** Interactive access to a running tenant workload remains
  unavailable to the tenant, and is deliberately out of scope.

---

## Open questions

1. **What is in the schema?** The whole of §1 rests on it. Containers and their images, environment,
   ports, files, units, a plain escape hatch? Too small and tenants are blocked; too large and it is
   cloud-init with extra steps.
2. **Does the workload authenticate to the API, and how?** Under 2b the bootstrap token is in a
   readable SMBIOS field, so it must be single-use and short-lived, and something must define what
   happens when it has already been spent — a legitimate reboot looks exactly like a replay.
3. **What happens when the API is down at boot?** Serve the last-known configuration from disk, or
   fail to start? The first weakens statelessness, the second makes the API a runtime dependency.
4. **Delivery and currency: one mechanism or two?** If the agent re-checks, it is one. If the
   mechanism is 2a, currency needs a second answer such as `podman auto-update`, which re-pulls a
   moving tag and is in tension with reproducibility.
5. **Per-workload or per-tenant configuration?** Per-workload is more flexible; per-tenant defaults
   would spare repetition for a tenant with many similar workloads.
6. **What is the blast radius of tenant-supplied configuration?** It runs as root in the tenant's
   own guest, which is the tenant's business — but it is realised by the substrate, and that path
   should be reviewed rather than assumed safe.

---

## To confirm when building

- That an `smbios1` field set through the PVE config API is readable in-guest from
  `/sys/class/dmi/id/`, and how many bytes it will actually carry, tested on a throwaway workload.
- Whether a workload can reach the Deevnet API from inside a tenant overlay — the API is on
  Platform and `tenant_transit -> platform` is declared, but this has not been exercised from a
  workload.
- Whether a storage with `snippets` content can be enabled on the tenant hypervisor without
  disturbing `local-lvm`, and by what route the API would write to it, if 2a is pursued.
- That `cicustom` user-data actually applies to a cloned template on this Proxmox version, before
  any of 2a is built on the assumption that it does.
- That `podman auto-update` works from a tenant workload against the chosen registry, over the
  egress path confirmed above.
- Whether a workload's configuration is removed when the workload is — the same class of question
  as the tenant state that survives deletion
  ([CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/) follow-up).
- Whether a tenant workload can reach a private registry at all, or only public ones.

---

## Current state

Nothing is built. Tenant workloads are empty Fedora VMs with podman, cloud-init, working DNS and
working egress, and no mechanism to tell them what to run. EdS has a running, empty `eds-services`
workload and an application waiting for this decision.
