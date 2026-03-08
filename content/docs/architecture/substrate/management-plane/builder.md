---
title: "Builder"
weight: 1
---

# Builder (Bootstrap Node)

### Purpose

The **builder** is the architectural role responsible for provisioning and configuring all substrate infrastructure. This role is implemented by the bootstrap node.

Every substrate needs a way to be created from scratch:

> *How do you provision infrastructure when no infrastructure exists yet?*

The builder answers this by providing:
- A self-contained provisioning platform
- All artifacts needed for air-gapped deployment
- Automation to configure every substrate component
- Authority transition from bootstrap to production

For the DNS authority model and naming conventions that the builder participates in, see [Core Services](../core-services/).

---

## 1. Key Properties

**Self-Contained** — Contains everything needed to stand up a substrate:
- Automation code (Ansible collections, playbooks)
- Artifact server (OS images, packages, kickstarts)
- Network boot infrastructure (TFTP, GRUB configs)
- Git repositories for all IaC

**Portable** — A single builder can move between substrates:
- Same physical device serves dvntm or dvnt
- Provisions whichever environment it's connected to
- No substrate-specific hardware requirements

**Air-Gapped Capable** — Once artifacts are staged, the builder can provision without upstream internet:
- All required images stored locally
- No external dependencies during provisioning
- Critical for isolated or bandwidth-limited deployments

**Disposable Authority** — The builder has temporary authority during bootstrap:
- May serve as DNS/DHCP/gateway initially
- Hands off control to Core Router once configured
- Becomes a regular admin host in production

---

## 2. Replaceable Provisioner Role

### 2.1 Provisioner Is a Role, Not a Pet

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

### 2.2 Multi-Homing Without Identity Confusion

A management host may be reachable from multiple substrates.

Instead of ambiguous multi-A records, **interface-specific identities** may be published:

```
provisioner-01-dvnt.mgmt.deevnet.net
provisioner-01-dvntm.mgmt.deevnet.net
```

Each name maps to the IP address used by that substrate.

This preserves:
- truthful routing
- clear firewall policy
- explicit blast-radius boundaries

---

## 3. Authority Transition

The builder participates in explicit authority transitions:

| Phase | Builder Role | Core Router Role |
|-------|-------------|------------------|
| **Bootstrap** | DNS, DHCP, gateway, TFTP, artifacts | Does not exist |
| **Transition** | TFTP, artifacts | DNS, DHCP, gateway |
| **Production** | TFTP, artifacts, Ansible controller | DNS, DHCP, gateway, firewall |

The transition is explicit and deliberate—never automatic.

---

## 4. Relationship to Tenants

The builder provisions **substrate infrastructure only**:
- Core Router configuration
- Hypervisor setup
- Management plane VMs
- Network switch and AP configuration

Tenant workloads use a different provisioning model. See
[Tenant Building](/docs/architecture/tenant/building/) for tenant-specific
provisioning architecture.

---

## 5. Implementation

The builder role is implemented by the **bootstrap node**:

| Aspect | Implementation |
|--------|----------------|
| **Hardware** | Mini PC with dual NICs |
| **OS** | Fedora with `deevnet.builder` collection |
| **Artifacts** | nginx serving images and packages |
| **Network boot** | in.tftpd with GRUB configs |
| **Automation** | Ansible controller for all substrate hosts |

See [Bootstrap Node](/docs/platforms/management-plane/bootstrap-node/) for implementation details.

---

## 6. Design Principles

**Ansible-First** — All substrate provisioning uses Ansible: idempotent configuration, version-controlled playbooks, traceable changes, no Terraform for substrate infrastructure.

**Deterministic Identity** — All provisioned hosts receive: deterministic MAC addresses (for VMs), static DHCP reservations, predictable DNS records, inventory-defined identity.

**Explicit Authority** — Authority transitions are: documented in runbooks, triggered manually, validated before completion, never automatic.

---

## 7. Out-of-Band and Adjacent Services

The management plane is the natural home for OOB and control infrastructure, including:

- serial console servers
- OOB management gateways
- bastion or jump hosts
- emergency recovery tooling

These services:
- live in `mgmt.deevnet.net`
- are independent of any substrate lifecycle
- remain reachable even when substrates are impaired
