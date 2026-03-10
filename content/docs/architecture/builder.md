---
title: "Builder"
weight: 1
---

# Builder

## Purpose

The **builder** is responsible for provisioning and configuring all substrate infrastructure.

Every Deevnet Infrastructure Platform site needs a way to be created from scratch:

> *How do you provision infrastructure when no infrastructure exists yet?*

The builder answers this by providing:
- A self-contained provisioning role
- All artifacts needed for deployment
- Automation to configure every substrate component
- Authority transition from bootstrap to production

---

## Design Principles

**Self-Contained** — The builder carries everything needed to stand up a substrate: IaC/CaC definitions, OS images, network boot infrastructure, and Git repositories.

**Portable** — A single builder can provision any site. The same builder serves dvntm or dvnt — no site-specific hardware required.

**Air-Gapped Capable** — Once artifacts are staged, the builder can provision without upstream internet. No external dependencies during build.

**Disposable Authority** — The builder holds temporary DNS/DHCP/gateway authority during bootstrap, then hands off to the Core Router. It can become a regular admin host in production.

**Replaceable Provisioner** — The provisioner is a role, not a pet. Any suitable host can assume it via code — rebuilding or replacing the provisioner is expected. Switching provisioners requires only DNS changes, not consumer changes.

---

## How It Works

The builder hosts all Infrastructure as Code and Configuration as Code used to set up the substrate. The build process follows a deliberate sequence:

1. **Network boot** — Bare-metal and virtual hosts PXE boot from the builder, pulling OS images and kickstart configurations from its local artifact server
2. **OS installation** — Hosts install from builder-hosted images and register against builder-hosted DHCP reservations, receiving deterministic IPs and hostnames
3. **Configuration** — The builder runs automation (from its local Git mirrors) against the newly installed hosts, applying CaC to configure networking, services, and security policy
4. **Validation** — Each host is verified against its expected state before proceeding to the next

The builder drives this entire sequence from its own local resources — no external dependencies are required once artifacts are staged.

---

## Bootstrap Services

During initial build, the builder **is** the network — no other infrastructure exists yet. It runs its own DNS, DHCP, and gateway services so that newly provisioned hosts can resolve names, obtain addresses, and reach the builder's artifact server without depending on anything it hasn't built yet.

This means the builder must carry a complete, self-contained copy of every resource needed to stand up the substrate:

- **DNS zone data** — All substrate host records, service CNAMEs, and reverse entries for the target site, served authoritatively by the builder until the Core Router takes over
- **DHCP configuration** — Static reservations for every known host MAC, plus dynamic pools for initial PXE boot or OS image installation
- **Git repositories** — A local mirror of every repository in the `deevnet` GitHub organization (IaC, CaC, inventory, playbooks), so automation runs entirely against local clones
- **OS and package artifacts** — Installation images, kickstart configs, and package mirrors staged locally

### Authority Transition

Once the Core Router is provisioned and validated, DNS/DHCP authority transfers to it and the builder's bootstrap services are deactivated. The builder retains TFTP, artifact hosting, and automation controller duties in production.

The builder participates in explicit authority transitions:

| Phase | Builder Role | Core Router Role |
|-------|-------------|------------------|
| **Bootstrap** | DNS, DHCP, gateway, TFTP, artifacts | Does not exist |
| **Transition** | TFTP, artifacts | DNS, DHCP, gateway |
| **Production** | TFTP, artifacts, automation controller | DNS, DHCP, gateway, firewall |

The transition is explicit and deliberate—never automatic.

---

## Multi-Homing Without Identity Confusion

A builder node may be reachable from multiple sites.

Instead of ambiguous multi-A records, **interface-specific identities** may be published:

```
provisioner-01-dvnt.mgmt.deevnet.net
provisioner-01-dvntm.mgmt.deevnet.net
```

Each name maps to the IP address used by that site.

This preserves:
- truthful routing
- clear firewall policy
- explicit blast-radius boundaries
