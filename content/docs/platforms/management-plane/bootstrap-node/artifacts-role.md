---
title: "Artifacts Role"
weight: 2
---

# Artifacts Role

## Purpose

The artifacts server enables **air-gapped provisioning** for substrate hosts. Target machines fetch all installation artifacts from the local server—no internet connectivity required during provisioning.

Goals:
- **Air-gap capability** — Substrate hosts install without upstream dependencies
- **Single source of truth** — All provisioning artifacts in one location
- **Reproducibility** — Known artifacts yield known outcomes

---

## Current Capabilities

The artifacts server provides:

| Artifact Type | Description |
|---------------|-------------|
| **Kickstart files** | OS installation automation scripts |
| **PXE boot artifacts** | Kernel, initrd, boot configuration |
| **Custom scripts** | Post-install automation payloads |
| **OS images** | ISO images or extracted install trees |

Artifacts are served via HTTP at `artifacts.<site>.deevnet.net`.

---

## Air-Gap Model

### Scope: Substrate Layer Only

Air-gapping applies to **substrate hosts**—the infrastructure foundation:

- Proxmox / hypervisors
- Admin / build servers
- Routers, firewalls
- DNS, DHCP hosts
- Any host that defines the substrate

**Not in scope for air-gap:**

- Tenant workloads (may use upstream repos or container registries)
- Edge devices (Raspberry Pis, IoT) — different OS, different lifecycle
- Container images — separate concern, different tooling

### Rationale

Mirroring every possible OS (Debian for RPis, various container base images, tenant-specific distros) creates unsustainable maintenance burden. The substrate is the trusted foundation—focus air-gap effort there.

Tenants and edge devices can follow their own update patterns, potentially with network access to upstream repositories.

### Behavior

- **Install-time air-gap**: Substrate hosts fetch everything from local artifacts server
- **No upstream dependencies** during substrate provisioning workflow
- Artifacts are pre-staged and validated before use
- Tenants/workloads may have network access to upstream repos (policy decision per tenant)

---

## Package Mirrors

Not built. Substrate hosts install from the staged install tree, but there is no local mirror for post-install updates, so a fully air-gapped substrate cannot yet patch itself. The options are recorded as a candidate in [Evaluations → Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/).

---

## Integrity Verification

### GPG Signatures

DNF validates GPG signatures automatically when `gpgcheck=1`. Ensure GPG keys are pre-installed on target hosts (typically included in Kickstart).

---

## Service Identity

Per the [Naming Standard](/docs/standards/naming/):

- `artifacts.<site>.deevnet.net` — Site-scoped name (required)
- `artifacts.deevnet.net` — Global alias (optional, CNAME to active site)

The service name is the contract. The underlying host can change without affecting consumers.

---

## Relationship to Other Services

| Service | Relationship |
|---------|--------------|
| **PXE server** | Often co-located on same host (multihoming) |
| **DNS** | Must resolve before artifacts can be fetched |
| **DHCP** | Provides PXE boot options; artifact URLs come from Kickstart |

Per the [Correctness Standard](/docs/standards/correctness/#33-multihoming-service-co-location), co-located services share a failure domain. Document co-location in inventory.

---

## Summary

The artifacts server is the foundation of air-gapped substrate provisioning:

1. **Scope to site** — Don't try to air-gap everything
2. **Serve via DNS name** — `artifacts.<site>.deevnet.net`
3. **Verify integrity** — GPG signatures on everything installed
4. **Package mirrors are not built yet** — see [the candidate](/docs/platforms/evaluations/software/management-plane/package-mirror/)
5. **Document co-location** — If sharing a host with PXE/DNS, track the blast radius
