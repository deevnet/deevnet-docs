---
title: "Workstation Role"
weight: 1
---

# Workstation Role

## Purpose

The `workstation` role configures a host as a **developer/admin workstation** with users, development tools, and infrastructure automation tooling.

---

## Capabilities

### User Management

- Creates dev users with configurable primary/extra groups
- Fetches SSH public keys from GitHub
- Sets up home directories and shell preferences

### Development Tools

| Category | Packages |
|----------|----------|
| **Core** | git, vim, tmux, golang |
| **ISO/Image** | Tools for working with disk images |
| **X11** | Display support for GUI tools |

### HashiCorp Tools

Configures the HashiCorp RPM repository and installs:
- **Terraform** — Infrastructure as code
- **Packer** — Image building

### AI Tools

- **Node.js** — Runtime for AI tooling
- **Claude Code** and other AI assistants

### Virtualization

- Libvirt/KVM support for local VM testing
- Podman for container workflows

---

## Configuration

Define users in inventory (`group_vars` or `host_vars`):

```yaml
dev_users:
  - name: cdeever
    primary_group: cdeever
    extra_groups:
      - wheel
    home: /home/cdeever
    github_keys_url: "https://github.com/cdeever.keys"
```

---

## Use Cases

- **Bootstrap node** — Admin environment for running Ansible playbooks
- **Dev workstation** — Full development environment for infrastructure work
- **Build host** — Image factory with Packer/Terraform installed

---

## Relationship to Other Roles

| Role | Relationship |
|------|--------------|
| **base** | Workstation depends on base for system packages |
| **artifacts** | May be co-located to serve build outputs |
