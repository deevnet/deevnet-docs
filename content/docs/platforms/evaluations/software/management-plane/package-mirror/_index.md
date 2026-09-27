---
title: "Substrate package mirror"
weight: 1
---

# Substrate package mirror

| | |
|---|---|
| **Role** | Local package repositories on the artifact server, for post-install updates on an air-gapped substrate |
| **Current** | {{< status-badge "planned" "Not yet evaluated" >}} Nothing built; options recorded below |

The commands on this page are design sketches. None of them is run anywhere today.

## Context

Beyond Kickstart and PXE artifacts, a fully air-gapped substrate requires local package repositories for post-install updates and additional package installation.

## Option A: dnf reposync + nginx

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
baseurl=http://artifacts.mobile.deevnet.net/repos/fedora/41/fedora
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-41-primary

[local-updates]
name=Local Fedora Updates Mirror
baseurl=http://artifacts.mobile.deevnet.net/repos/fedora/41/updates
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-41-primary
```

**Sync scheduling:**
- Manual sync before major provisioning runs
- Or: scheduled sync (weekly/monthly) via cron/systemd timer
- Storage: ~100-200GB per Fedora release

## Option B: Pulp / Katello

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

## Adjacent ideas, not built

These would sit alongside a package mirror, and were recorded with it.

### OpenSCAP compliance

For hardened substrate hosts, use OpenSCAP to validate against security profiles:

```bash
oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_cis \
  /usr/share/xml/scap/ssg/content/ssg-fedora-ds.xml
```

Can be integrated into post-install automation.

### SBOM generation

For audit trails, consider generating Software Bill of Materials:

```bash
rpm -qa --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' > /root/sbom.txt
```
