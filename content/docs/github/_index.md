---
title: "Code Repositories"
weight: 6
bookCollapseSection: true
---

# Code Repositories

All Deevnet projects are hosted on GitHub: [github.com/deevnet](https://github.com/deevnet)

---

## Repositories

| Repository | Description |
|------------|-------------|
| [ansible-collection-deevnet.builder](https://github.com/deevnet/ansible-collection-deevnet.builder) | Ansible collection for workstations, artifact servers, PXE boot |
| [ansible-collection-deevnet.net](https://github.com/deevnet/ansible-collection-deevnet.net) | Network-focused Ansible collection (OPNsense, Omada) |
| [ansible-inventory-deevnet](https://github.com/deevnet/ansible-inventory-deevnet) | Central inventory for platform infrastructure |
| [deevnet-image-factory](https://github.com/deevnet/deevnet-image-factory) | Packer builds for Raspberry Pi and Proxmox templates |
| [deevnet-docs](https://github.com/deevnet/deevnet-docs) | This documentation site |

---

## Repository Layout

```
dvnt/
├── ansible-collection-deevnet.builder/
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
git clone git@github.com:deevnet/ansible-collection-deevnet.net.git
git clone git@github.com:deevnet/ansible-inventory-deevnet.git
git clone git@github.com:deevnet/deevnet-image-factory.git
git clone git@github.com:deevnet/deevnet-docs.git
```

---

## Standards Authority

`deevnet-docs` is authoritative—if a project conflicts with standards defined here, standards win.

Other repos may include it as a git submodule at `docs/deevnet/`.
