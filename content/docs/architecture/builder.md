---
title: "Builder"
weight: 1
---

# Builder

### Purpose

The **builder** is the architectural function responsible for provisioning and configuring all substrate infrastructure.

Every site needs a way to be created from scratch:

> *How do you provision infrastructure when no infrastructure exists yet?*

The builder answers this by providing:
- A self-contained provisioning platform
- All artifacts needed for air-gapped deployment
- Automation to configure every substrate component
- Authority transition from bootstrap to production

---

## Key Properties

**Self-Contained** — Contains everything needed to stand up a substrate:
- Infrastructure as Code and Configuration as Code definitions
- Artifact server (OS images, packages, kickstarts)
- Network boot infrastructure (TFTP, GRUB configs)
- Git repositories for all IaC

**Portable** — A single builder can move between sites:
- Same builder serves dvntm or dvnt
- Provisions whichever environment it's connected to
- No site-specific hardware requirements

**Air-Gapped Capable** — Once artifacts are staged, the builder can provision without upstream internet:
- All required images stored locally
- No external dependencies during provisioning
- Critical for isolated or bandwidth-limited deployments

**Disposable Authority** — The builder has temporary authority during bootstrap:
- May serve as DNS/DHCP/gateway initially
- Hands off control to Core Router once configured
- Can become a regular admin host in production

---

## Bootstrap Services

During initial build, the builder **is** the network — no other infrastructure exists yet. It runs its own DNS, DHCP, and gateway services so that newly provisioned hosts can resolve names, obtain addresses, and reach the builder's artifact server without depending on anything it hasn't built yet.

This means the builder must carry a complete, self-contained copy of every resource needed to stand up the substrate:

- **DNS zone data** — All substrate host records, service CNAMEs, and reverse entries for the target site, served authoritatively by the builder until the Core Router takes over
- **DHCP configuration** — Static reservations for every known host MAC, plus dynamic pools for initial PXE boot or OS image installation
- **Git repositories** — A local mirror of every repository in the `deevnet` GitHub organization (IaC, CaC, inventory, playbooks), so automation runs entirely against local clones
- **OS and package artifacts** — Installation images, kickstart configs, and package mirrors staged locally

Once the Core Router is provisioned and validated, DNS/DHCP authority transfers to it and the builder's bootstrap services are deactivated. The builder retains TFTP, artifact hosting, and automation controller duties in production.

---

## Replaceable Provisioner Role

### Provisioner Is a Role, Not a Pet

The provisioner is a **role** that any suitable host can assume via code.

- no host is permanently "the provisioner"
- rebuilding or replacing the provisioner is expected
- authority is logical, not physical

Example:
```
artifacts.mgmt.deevnet.net -> provisioner-01.mgmt.deevnet.net
```

Switching provisioners requires only DNS changes, not consumer changes.

---

### Multi-Homing Without Identity Confusion

A management host may be reachable from multiple sites.

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

---

## Authority Transition

The builder participates in explicit authority transitions:

| Phase | Builder Role | Core Router Role |
|-------|-------------|------------------|
| **Bootstrap** | DNS, DHCP, gateway, TFTP, artifacts | Does not exist |
| **Transition** | TFTP, artifacts | DNS, DHCP, gateway |
| **Production** | TFTP, artifacts, automation controller | DNS, DHCP, gateway, firewall |

The transition is explicit and deliberate—never automatic.

---

## Design Principles

**Configuration as Code** — All substrate provisioning is code-driven: idempotent configuration, version-controlled definitions, traceable changes.

**Deterministic Identity** — All provisioned hosts receive: deterministic MAC addresses (for VMs), static DHCP reservations, predictable DNS records, inventory-defined identity.

**Explicit Authority** — Authority transitions are: documented in runbooks, triggered manually, validated before completion, never automatic.

---

## Out-of-Band and Adjacent Services

The management plane is the natural home for OOB and control infrastructure, including:

- serial console servers
- OOB management gateways
- bastion or jump hosts
- emergency recovery tooling

These services:
- live in `mgmt.deevnet.net`
- are independent of any substrate lifecycle
- remain reachable even when sites are impaired
