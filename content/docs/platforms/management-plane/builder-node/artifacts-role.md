---
title: "Artifacts Role"
weight: 2
aliases:
  - /docs/platforms/management-plane/bootstrap-node/artifacts-role/
---

# Artifacts Role

Serves the builder's artifacts: everything a substrate host installs from. What is in scope for the
air gap, and why, is in [Builder → Air-Gap Scope](/docs/architecture/builder/#air-gap-scope).

---

## Current Capabilities

The artifacts server provides:

| Artifact Type | Description |
|---------------|-------------|
| **Kickstart files** | OS installation automation scripts |
| **PXE boot artifacts** | Kernel, initrd, boot configuration |
| **Custom scripts** | Post-install automation payloads |
| **OS images** | ISO images or extracted install trees |
| **Container images** | Service image tarballs, loaded by the roles that run them |

Artifacts are served via HTTP at `artifacts.<site>.deevnet.net`.

---

## Package Mirrors

The artifact server holds a full rsync of each Fedora release's `os` repository — the packages as
released, with their `repodata` — at `fedora/<release>/mirror`, and hosts install from it. It does not
carry Fedora's `updates` repository, and installed hosts are not pointed at the local mirror, so
post-install updates still come from the internet and an air-gapped site cannot patch itself.
Mirroring `updates` is the
[Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/)
candidate.

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

1. **Scope to the substrate** — Don't try to air-gap everything
2. **Serve via DNS name** — `artifacts.<site>.deevnet.net`
3. **Verify integrity** — GPG signatures on everything installed
4. **The release is mirrored; updates are not** — see [the candidate](/docs/platforms/evaluations/software/management-plane/package-mirror/)
5. **Document co-location** — If sharing a host with PXE/DNS, track the blast radius
