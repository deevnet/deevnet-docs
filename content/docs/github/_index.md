---
title: "Code Repositories"
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
  <a class="section-card" href="https://github.com/deevnet/deevnet-docs">
    <h3>deevnet-docs</h3>
    <p>This documentation site.</p>
  </a>
</div>

---

## Repository Layout

```
dvnt/
├── ansible-collection-deevnet.builder/
├── ansible-collection-deevnet.mgmt/
├── ansible-collection-deevnet.net/
├── ansible-inventory-deevnet/
├── deevnet-image-factory/
└── deevnet-docs/
```

All repositories are designed to be cloned into a common parent directory (typically `~/dvnt/` or `/srv/dvnt/`).

---

## Getting Started

```bash
# Clone all repositories
mkdir -p ~/dvnt && cd ~/dvnt
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
