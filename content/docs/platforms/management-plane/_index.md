---
title: "Management Plane"
weight: 3
bookCollapseSection: true
---

# Management Plane

The products behind the site's own services: the builder that stands the site up, the hypervisor
its substrate service VMs run on, and the services on those VMs that have implementation notes of their own.
What the management plane is, and what belongs to it, is in
[Architecture → Management Plane](/docs/architecture/substrate/management-plane/) and
[Control Plane](/docs/architecture/substrate/control-plane/); the builder is its own role,
[Builder](/docs/architecture/builder/).

| Role | Filled by | Page |
|------|-----------|------|
| Builder | AOOSTAR N1 PRO, Fedora | [Builder Node](builder-node/) |
| Management hypervisor | Dell OptiPlex 7050 Micro, Proxmox VE | [Management Hypervisor](management-hypervisor/) |
| Management and control plane services | One VM per domain | [Substrate Service VMs](substrate-service-vms/) |
| Tenant DNS | PowerDNS Authoritative | [Tenant DNS](tenant-dns/) |

The other domain services are listed, with versions, in the
[Software Catalog](/docs/platforms/software-catalog/#substrate-service-vms).
