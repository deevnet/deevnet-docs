---
title: "Home Site"
weight: 10
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 7
---

# Home Site

The Mobile Factory builds sites as well as tenants. The home site (`home.deevnet.net`, site code `01`)
is the next one: a site that hosts several tenants' Deevnet Pis. It is not built. Its site code,
zone and address space are reserved in the [Naming standard](/docs/standards/naming/).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

**Home is built at the factory and deployed at home.** The Builder comes home and runs Ansible
against the home inventory; nothing at home is changed any other way. Tenants at home have no
self-service: a change starts at the factory and arrives as a new image or a configuration change.

**In Scope**
- Home's own PKI, network, DNS and DHCP
- Hosting tenants' Deevnet Pis, which carry their own services ([ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/))

**Out of Scope**
- A hypervisor at home, and tenant workloads on it, until a tenant needs them
- A broker, a device registry or a Deevnet API at home: a Pi is its devices' broker and registry

---

## PKI ⏳

- ⏳ **Home Site CA.** Signed by the root in a ceremony (path 2), held offline ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) §1).
- ⏳ **Home Substrate CA.** Its key in home's vault, signed by the Home Site CA (path 3); home's
  infrastructure certificates issued from it by Ansible.

## Network ⏳

- ⏳ **Home inventory.** Hosts, VLANs and firewall policy, in the home inventory beside the mobile
  site's.
- ⏳ **DNS and DHCP on the core router**, OPNsense with Unbound, as on the mobile site.
- ⏳ **DNS for hosted Pis.** Each Pi's site-less names (`<service>.<tenant>.deevnet.net`) and the
  site names it carries, from the home inventory ([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/)).

## Later ⏳

- ⏳ **Kea for DHCP**, for the API support found wanting on the mobile site.
- ⏳ **A hypervisor at home**, when a tenant needs workloads there.
