---
title: "Artifacts Server"
weight: 1
---

# Artifacts Server

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

Artifacts are served via HTTP at `artifacts.<substrate>.deevnet.net`.

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

Beyond Kickstart and PXE artifacts, a fully air-gapped substrate requires local package repositories for post-install updates and additional package installation.

### Simple Approach: dnf reposync + nginx

For Fedora-based substrate hosts, mirror the essential repositories locally:

**Repositories to mirror:**
- `fedora` — Base OS packages
- `updates` — Security and bug fixes

**Basic sync:**
```bash
dnf reposync --repoid=fedora --repoid=updates \
  --download-metadata \
  --destdir=/var/www/html/repos/fedora/41
```

**Directory structure:**
```
/var/www/html/repos/
└── fedora/
    └── 41/
        ├── fedora/
        │   └── Packages/
        │   └── repodata/
        └── updates/
            └── Packages/
            └── repodata/
```

**Target machine repo configuration** (`/etc/yum.repos.d/local.repo`):
```ini
[local-fedora]
name=Local Fedora Mirror
baseurl=http://artifacts.dvnt.deevnet.net/repos/fedora/41/fedora
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-41-primary

[local-updates]
name=Local Fedora Updates Mirror
baseurl=http://artifacts.dvnt.deevnet.net/repos/fedora/41/updates
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-41-primary
```

**Sync scheduling:**
- Manual sync before major provisioning runs
- Or: scheduled sync (weekly/monthly) via cron/systemd timer
- Storage: ~100-200GB per Fedora release

### Enterprise Approach: Pulp / Katello

For larger environments or stricter compliance requirements:

| Feature | Benefit |
|---------|---------|
| **Content views** | Snapshot package sets for reproducibility |
| **Promotion workflow** | dev → QA → prod with identical packages |
| **GPG verification** | Built-in signature validation |
| **Vulnerability data** | OVAL integration for security scanning |
| **Lifecycle management** | Track which hosts use which content view |

Consider Pulp/Katello when:
- Multiple environments need identical, versioned package sets
- Compliance requires audit trails for package changes
- Scale exceeds what manual sync can manage

---

## Integrity Verification

### GPG Signatures

DNF validates GPG signatures automatically when `gpgcheck=1`. Ensure GPG keys are pre-installed on target hosts (typically included in Kickstart).

### OpenSCAP Compliance

For hardened substrate hosts, use OpenSCAP to validate against security profiles:

```bash
oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  /usr/share/xml/scap/ssg/content/ssg-fedora-ds.xml
```

Can be integrated into post-install automation.

### SBOM Generation

For audit trails, consider generating Software Bill of Materials:

```bash
rpm -qa --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' > /root/sbom.txt
```

---

## Service Identity

Per the [Naming Standard](/docs/standards/naming/):

- `artifacts.<substrate>.deevnet.net` — Substrate-scoped name (required)
- `artifacts.deevnet.net` — Global alias (optional, CNAME to active substrate)

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

1. **Scope to substrate** — Don't try to air-gap everything
2. **Serve via DNS name** — `artifacts.<substrate>.deevnet.net`
3. **Include package mirrors** — dnf reposync for Fedora hosts
4. **Verify integrity** — GPG signatures, OpenSCAP for compliance
5. **Document co-location** — If sharing a host with PXE/DNS, track the blast radius
