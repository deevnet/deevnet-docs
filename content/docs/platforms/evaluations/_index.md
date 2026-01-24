---
title: "Evaluations"
weight: 4
---

# Platform Evaluations

Platform evaluation documents capture decision rationale for technologies considered but not yet adopted, or being actively evaluated.

---

## VyOS Evaluation

OPNsense has served well for production routing but has a critical limitation: **no automated installation support**. This creates a gap in the otherwise automated substrate provisioning workflow.

### Why VyOS?

| Requirement | OPNsense | VyOS |
|-------------|----------|------|
| Automated install | No PXE, manual USB only | cloud-init + staged ISO |
| Air-gap recovery | Manual reinstall | Staged ISO, automated |
| Config-as-code | API-based | Native CLI + Ansible |
| Day-2 automation | Good (Ansible) | Excellent (vyos.vyos) |
| WebUI | Yes | No (CLI-centric) |

### Automation Capability

**OPNsense (Current)**:
- API-based configuration via `deevnet.net` collection
- **No PXE boot support** — requires manual USB installation
- Day-2 automation is good; initial provisioning is manual

**VyOS (Target)**:
- cloud-init support for automated initial configuration
- Official `vyos.vyos` Ansible collection
- CLI-centric, designed for automation
- ISO can be staged on artifact server for air-gap deployment

### Tradeoffs Accepted

- **No WebUI**: All management via CLI or Ansible. Aligns with config-as-code principles.
- **Rolling release**: LTS requires subscription. Rolling is free and acceptable for homelab.

### Migration Status

| Phase | Status |
|-------|--------|
| Platform evaluation | Complete |
| Manual testing (Proxmox VM) | Pending |
| cloud-init automation | Pending |
| Ansible roles | Pending |
| Production cutover | Pending |

### VyOS Ansible Modules

When migration proceeds, configuration will use the `vyos.vyos` Ansible collection:

| Component | Module |
|-----------|--------|
| Interfaces | `vyos_interfaces` |
| Firewall rules | `vyos_firewall_rules` |
| System settings | `vyos_system`, `vyos_hostname` |
| Static routes | `vyos_static_routes` |
