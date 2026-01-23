---
title: "Online Preparation"
weight: 1
---

# Online Preparation

The builder node (with internet access) stages artifacts to the artifact server before any recovery is needed.

---

## What Gets Staged

| Artifact | Source | Role/Task |
|----------|--------|-----------|
| Fedora install tree | rsync from Fedora mirrors | `artifacts` role |
| Fedora Server ISO | download.fedoraproject.org | `artifacts` role |
| Proxmox VE ISO | enterprise.proxmox.com | `artifacts` role |
| SSH public keys | Generated locally | `artifacts` role |
| Container images | docker.io, etc. | `artifacts` role |

---

## Commands

From builder node with internet:

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit artifact_servers
```

---

## Verification

After staging, verify artifacts are accessible from the internal network:

```bash
curl -I http://artifacts.dvntm.deevnet.net/fedora/43/mirror/
curl -I http://artifacts.dvntm.deevnet.net/isos/proxmox/proxmox-ve_8.4-1.iso
```

---

## Scheduling

Artifact staging should run:

- **Weekly** - Keep OS mirrors current
- **After major releases** - New Fedora/Proxmox versions
- **Before planned maintenance** - Ensure fresh artifacts for any rebuild
