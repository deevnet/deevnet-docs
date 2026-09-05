---
title: "💻 Code Repositories"
weight: 6
bookCollapseSection: true
---

# Code Repositories

All Deevnet projects are hosted on GitHub: [github.com/deevnet](https://github.com/deevnet)

<div class="section-cards">
  <a class="section-card" href="https://github.com/deevnet/ansible-collection-deevnet.builder">
    <h3>deevnet.builder</h3>
    <p>Ansible collection for workstations, artifact servers, PXE boot.</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/ansible-collection-deevnet.mgmt">
    <h3>deevnet.mgmt</h3>
    <p>Management plane and centralized services.</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/ansible-collection-deevnet.net">
    <h3>deevnet.net</h3>
    <p>Network-focused Ansible collection (OPNsense, Omada).</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/ansible-inventory-deevnet">
    <h3>ansible-inventory</h3>
    <p>Central inventory for platform infrastructure.</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/deevnet-image-factory">
    <h3>image-factory</h3>
    <p>Packer builds for Raspberry Pi and Proxmox templates.</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/deevnet-tenant-factory">
    <h3>tenant-factory</h3>
    <p>The tenant fabric, the reusable tenant module, and the index registry. Substrate side — tenants themselves live elsewhere.</p>
  </a>
  <a class="section-card" href="https://github.com/deevnet/deevnet-docs">
    <h3>deevnet-docs</h3>
    <p>This documentation site.</p>
  </a>
</div>

---

## Repository Layout

```
home/
├── ansible-collection-deevnet.builder/
├── ansible-collection-deevnet.mgmt/
├── ansible-collection-deevnet.net/
├── ansible-inventory-deevnet/
├── deevnet-image-factory/
├── deevnet-tenant-factory/
├── deevnet-tenant-<name>/          one per tenant
└── deevnet-docs/
```

All repositories are designed to be cloned into a common parent directory (typically `~/home/` or `/srv/home/`).

### Tenants get their own repositories

A tenant is **not** a directory inside a substrate repo. Each one is
`deevnet-tenant-<name>`, and that repository is the tenant: its network, its workloads and its DNS
records are declared there and rebuilt from there
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)).

The split is what makes the tenant contract real rather than aspirational — a tenant's recurring
lifecycle touches no substrate repository at all. New tenants are created by copying
`examples/tenant/` **out of** the tenant factory, never by copying a live tenant.

---

## Getting Started

```bash
# Clone all repositories
mkdir -p ~/home && cd ~/home
git clone git@github.com:deevnet/ansible-collection-deevnet.builder.git
git clone git@github.com:deevnet/ansible-collection-deevnet.mgmt.git
git clone git@github.com:deevnet/ansible-collection-deevnet.net.git
git clone git@github.com:deevnet/ansible-inventory-deevnet.git
git clone git@github.com:deevnet/deevnet-image-factory.git
git clone git@github.com:deevnet/deevnet-docs.git
```

---

## Standards Authority

`deevnet-docs` is authoritative — if a project conflicts with standards defined here, standards win.

Other repos may include it as a git submodule at `docs/deevnet/`.
