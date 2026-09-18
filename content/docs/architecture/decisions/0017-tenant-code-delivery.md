---
title: "ADR-0017: How Tenant Code Reaches a Tenant Workload"
weight: 17
---

# ADR-0017: How Tenant Code Reaches a Tenant Workload

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-18 |
| **Scope** | How a tenant's own application code and configuration arrive on a tenant workload, and how they are kept current — not what the code is, and not how the workload itself is built |
| **Extends** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), which says tenants own their code but does not say how it is delivered; [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), which builds the empty workload this decision fills |
| **Related** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0011: Edge Devices Are Application-Owned](/docs/architecture/decisions/0011-edge-devices-application-owned/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) |

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

**So delivery must be a pull, initiated from inside the workload.** That much is forced. What is
open is how the workload learns what to pull.

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

A tenant workload can therefore pull and run containers from a public registry the moment it boots.
The missing piece is narrow: **how it is told what to run.**

### The substrate's only injection point is Proxmox cloud-init, and it is currently limited

The Deevnet API configures a workload through the PVE API, setting the native cloud-init fields:
`ciuser`, `sshkeys`, `nameserver` and `ipconfig0`. Proxmox supports arbitrary user-data only
through `cicustom`, which points at a **snippet file on a storage**.

Two facts constrain that:

1. **No storage on the tenant hypervisor has `snippets` content enabled.** `pvesm status -content
   snippets` returns nothing. So `cicustom` is unavailable today without a storage change.
2. **The API writes through the PVE API and never files on a hypervisor**, by deliberate rule. The
   PVE upload endpoint does not accept snippets, so honouring that rule while delivering user-data
   needs a decision, not just a flag.

There is a third fact that shapes what may go in user-data at all: **a cloud-init snippet is a file
on substrate storage**, readable by anyone with sufficient PVE privilege, and it is not covered by
[ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)'s sealing. Whatever
mechanism is chosen, user-data is not a place for a tenant's long-lived secrets.

### Statelessness is the intended shape

The operator's stated direction is that tenant workloads stay **as stateless as possible**, so that
replacing one is the ordinary repair rather than a loss. This is not yet a guarantee, and it
interacts with this decision: a delivery mechanism that reconstructs the workload from scratch on
every boot reinforces statelessness, while one that mutates a long-lived machine works against it.

It also has a sharp edge today. A tenant has **no way to restart a workload in place**; the only
lever the provider offers is replace, which destroys the disk
([CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/) follow-up). A mechanism that needs a
reboot to take effect therefore needs a rebuild, and that is only acceptable while workloads hold
nothing.

---

## Options considered

### Option A — Tenant-authored cloud-init user-data

The tenant supplies user-data on `deevnet_workload`; the API stores it as a snippet and sets
`cicustom`. On first boot cloud-init installs units, pulls images and starts them.

- **For:** the standard mechanism, familiar to anyone who has used a cloud; tenant-authored and
  Terraform-native; declarative; runs before anything else; reinforces statelessness because a
  replaced workload rebuilds itself identically.
- **Against:** needs snippets storage enabled on every tenant hypervisor **and** a way for the API
  to write the snippet without writing files on a hypervisor; user-data is readable on substrate
  storage, so it cannot carry tenant secrets; it runs **once**, so it delivers but does not keep
  current.

### Option B — Tenant-built images

The tenant builds a VM image containing its application; the substrate boots it instead of the
shared Fedora template.

- **For:** nothing to deliver at run time; the workload is correct the instant it boots; strongest
  possible statelessness.
- **Against:** puts tenant-built artifacts in substrate storage and makes the substrate host a
  tenant build pipeline; every code change becomes an image build plus a workload replace; the
  template is currently substrate-owned and substrate-scanned, and tenant images would need their
  own lifecycle, provenance and cleanup. Heavy for a one-line configuration change.

### Option C — A substrate bootstrap agent in the base image

The base image carries a small agent that, on boot, resolves a tenant-declared pointer and applies
whatever it names. The tenant publishes the pointer itself — for instance a TXT record in its own
zone, which it already owns over RFC 2136
([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).

- **For:** needs no snippets storage and no new API surface; the pointer is tenant-owned and
  changeable without touching the substrate; nothing tenant-specific is stored substrate-side; it
  can re-check on a timer, so it keeps current as well as delivers.
- **Against:** the substrate now ships and owns an agent that runs tenant-chosen code, which is a
  real ongoing responsibility and an obvious blast radius; a DNS TXT pointer is small, public within
  the site, and an odd control channel; it is a Deevnet-specific mechanism where Option A is an
  industry-standard one.

### Option D — The tenant runs its own deployer inside its own fabric

Workloads within a tenant's overlay can reach each other. The tenant runs one workload as its own
CI or deployment node and pushes to the rest.

- **For:** entirely tenant-owned; needs nothing from the substrate; scales naturally to a tenant
  with many workloads; the tenant may use whatever tooling it likes.
- **Against:** **it does not solve the problem, it relocates it.** The deployer workload is itself
  an empty VM that something must fill, and that something is one of the other options. Sensible as
  a later pattern for a large tenant; it cannot be the base case.

### Option E — Convention over configuration

The substrate passes only the tenant and workload name. The base image always starts a container
from a fixed, derived location — for example `<registry>/<tenant>/<workload>:latest`.

- **For:** the smallest possible mechanism; no user-data, no agent, no new API field.
- **Against:** rigid — one container per workload, no configuration, no environment, no choice of
  registry; a naming convention is a weak contract to hang a platform on; and it still requires a
  pull loop to keep current, so it buys less than it looks.

---

## Decision

**Proposed, and the part that is not in doubt:** delivery is a **pull initiated from inside the
workload**. No push mechanism may be introduced, and in particular the substrate's Ansible and
`podman_service` pattern must not be extended to tenant workloads. That follows from the no-inbound
architecture and from tenant code ownership, and it is independent of which option below is taken.

**The recommendation is Option A, with three qualifications** — but this ADR is deliberately
brought forward before the options are closed, because the qualifications are real and one of them
may change the answer:

1. **User-data delivers; it does not maintain.** Cloud-init runs once. Keeping a workload current
   is a second mechanism — most cheaply `podman auto-update` on a systemd timer, which the base
   image can already run, installed *by* the user-data. Delivery and currency should be decided
   together, not one now and one later.
2. **User-data carries no secrets.** It lives as a readable file on substrate storage. It may carry
   public configuration and pointers only. How a workload authenticates to a private registry, or
   receives a tenant secret at all, is unresolved and is the sharpest open question below.
3. **The snippets obstacle must be resolved without breaking the "no files on a hypervisor" rule.**
   If it cannot be, Option C becomes the leading candidate, because it needs no substrate-side
   per-tenant storage at all.

Option B is rejected as the base case: making the substrate host tenant build artifacts reverses
ADR-0010's direction, though a tenant remains free to bake its own container images — which is
different, and expected. Option D is rejected as a base case for circularity, and recorded as a
later pattern. Option E is rejected as too rigid to build on.

---

## Consequences

- **The `deevnet_workload` resource grows** a user-data attribute, and the API grows the storage
  path behind it. That is new tenant-facing surface and needs its own contract.
- **A tenant's workload becomes reproducible from its repository alone.** Given the tenant's
  Terraform and its images, a destroyed workload returns complete. That is the statelessness goal
  made real rather than aspirational.
- **The substrate takes on a storage responsibility it does not have today** — snippets, per
  hypervisor, with a lifecycle of their own. A workload's user-data must be removed when the
  workload is.
- **Restart-in-place becomes more pressing.** Under Option A a user-data change needs a boot, and
  today the only boot a tenant can cause is a replace. Either the restart action lands, or every
  configuration change destroys the machine.
- **Nothing here gives a tenant a way in.** Delivery is solved; interactive access to a running
  tenant workload remains unavailable to the tenant, and is deliberately out of scope.

---

## Open questions

1. **How does a workload get a secret?** The sharpest one. User-data is readable substrate-side, so
   it cannot hold a registry credential, a broker password or a tenant API token. Candidates: only
   public images at first; a short-lived token minted by the API and exchanged on boot; or a
   workload identity derived from something the substrate already asserts. This blocks the EdS
   broker work, where `lightd` needs a broker credential.
2. **Can the API write a snippet without writing files on a hypervisor?** If the PVE API genuinely
   cannot accept one, the rule and the option are in conflict, and one of them gives.
3. **Delivery and currency: one mechanism or two?** `podman auto-update` on a timer is the cheap
   answer, but it re-pulls a moving tag, which is in tension with reproducibility.
4. **Does user-data belong to the workload or the tenant?** Per-workload is more flexible;
   per-tenant defaults would spare repetition for a tenant with many similar workloads.
5. **What is the blast radius of arbitrary tenant user-data?** It runs as root in the tenant's own
   guest, which is the tenant's business — but it is written by the substrate, and that path should
   be reviewed rather than assumed safe.

---

## To confirm when building

- Whether a storage with `snippets` content can be enabled on the tenant hypervisor without
  disturbing `local-lvm`, and whether the PVE API can place a snippet on it.
- That `cicustom` user-data actually applies to a cloned template on this Proxmox version, tested on
  a throwaway workload.
- That `podman auto-update` works from a tenant workload against the chosen registry, over the
  egress path confirmed above.
- Whether removing a workload removes its snippet, and what happens to an orphaned one — the same
  class of question as the tenant state that survives deletion
  ([CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/) follow-up).
- Whether a tenant workload can reach a private registry at all, or only public ones.

---

## Current state

Nothing is built. Tenant workloads are empty Fedora VMs with podman, cloud-init, working DNS and
working egress, and no mechanism to tell them what to run. EdS has a running, empty `eds-services`
workload and an application waiting for this decision.
