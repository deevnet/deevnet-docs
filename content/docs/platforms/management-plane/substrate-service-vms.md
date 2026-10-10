---
title: "Substrate Service VMs"
aliases:
  - /docs/platforms/management-plane/domain-vms/
weight: 3
---

# Substrate Service VMs

The VMs on the [management hypervisor](/docs/platforms/management-plane/management-hypervisor/)
that run the substrate's own services, for both the
[management plane](/docs/architecture/substrate/management-plane/) and the
[control plane](/docs/architecture/substrate/control-plane/). The architecture places each service on
a segment by audience. This page groups those services into **domains** by what they are for, and
gives each domain one VM
([ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/)).

---

## The map

From inventory: each host's group memberships, and the `deevnet.mgmt` roles `site.yml` applies to them.

| Domain | Plane | Host | Segment | Services |
|---|---|---|---|---|
| Network management | Management | `dv02nms001v01`, 10.20.99.40 | Management | Omada controller |
| Substrate observability | Management | `dv02col001v01`, 10.20.99.41 | Management | None yet: built empty, for the collector [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) will place there |
| Provisioning | Control | `dv02prv001v01`, 10.20.25.20 | Platform | [Deevnet API](/docs/platforms/deevnet-software/deevnet-api/) and its database; MinIO, the tenant state store; the service proxy |
| Identity | Control | `dv02idn001v01`, 10.20.25.21 | Platform | OpenBao; PowerDNS, the [tenant DNS](/docs/platforms/management-plane/tenant-dns/) |
| Tenant observability | Control | `dv02obs001v01`, 10.20.25.22 | Platform | VictoriaLogs behind vmauth; Grafana; tenant downloads; the service proxy |
| Device messaging | Control | `dv02msg001v01`, 10.20.35.20 | IoT Backend | VerneMQ and its account writer; the [log bridge](/docs/platforms/deevnet-software/log-bridge/) |

Every service VM runs Fedora from the site template, with its services as Podman containers under
systemd ([Software Catalog → Substrate Service VMs](/docs/platforms/software-catalog/#substrate-service-vms)).

In inventory, the group `management_plane` means *a VM on the management hypervisor with an
allocated identity*, whichever plane it serves. It is what the VM identity allocator scans, not a
statement about audience.

---

## Packaging rules

- **Each domain is one host, on exactly one segment.** Anything that crosses segments goes through
  the core router and its zone policy, so no host quietly bridges two zones.
- **A domain that needs two segments becomes two domains.**
- **Each service stays separable.** It runs in its own container, with its own data and its own
  inventory group, so moving a service to another host is an inventory change, not a redesign.
- **A new service joins the domain it belongs to**, or becomes a new domain if none fits.
- **Services in one domain share the host's fate.** Rebooting a host takes all of its services with
  it, which is accepted at this scale.
- **Services with different audiences never share a host.** The substrate's own services change
  often, and a restart among them must not take down something tenants or devices depend on.

## The service proxy

**Each service VM that serves tenants runs one proxy, which is the only listener for its HTTPS
services.** It is nginx, in a container like the services beside it
([ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/)).

| Host | Names it serves on 443 | Old ports it still answers on |
|---|---|---|
| `dv02prv001v01` | `api`, `tfstate` | 8080, 9000 |
| `dv02obs001v01` | `grafana`, `logs`, `downloads` | 3000, 8427, 8443 |

- **It routes by name.** It terminates TLS, reads the name the client asked for, and forwards to
  that service on the host's loopback address. A name the host does not serve gets no handshake.
- **It holds the host's server certificate**, issued for the host, each alias and each address from
  the inventory. Grafana, the log store, the downloads and the state store hold none. The API keeps
  its own, which the proxy verifies.
- **It decides nothing about who is calling.** Each service authenticates its own callers, as before.
- **The list of names is inventory**, `service_proxy_vhosts` in the host's variables. A new service
  is a loopback listener, an alias and one entry there.

The broker is not behind a proxy: it is not HTTP, and it is on another segment.

How a service VM is built is [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/).
What each loses when its host is rebuilt is in
[Rebuild a Hypervisor](/docs/runbook/substrate/recovery/rebuild-hypervisor/#management-hypervisor-dv02hyp001p01).
