---
title: "ADR-0036: A Service Proxy on Each Service VM"
weight: -36
---

# ADR-0036: Tenant-Facing Services Answer on 443, Through a Proxy on Each Service VM

|  |  |
|--|--|
| **Status** | Accepted (2026-10-10): built and deployed by [CHG-0046](/docs/changes/2026/0046-service-proxy/) |
| **Date** | 2026-10-10 |
| **Scope** | Where a tenant-facing HTTPS service listens, what name and port a tenant dials, and which process holds the certificate. Not who may call a service, which each service still decides ([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §5), and not the broker, which is not HTTP. |
| **Extends** | [ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/): a service VM gains one more container, and a new service on it no longer opens a port to its segment. |
| **Amends** | [ADR-0024](/docs/architecture/decisions/platform-services/0024-dashboards/) As built §1 ("port 3000"), [ADR-0022](/docs/architecture/decisions/platform-services/0022-central-logging/) §3 ("vmauth is the only listener tenants can reach") and [ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/) §5 ("the store serves TLS"): each service is on loopback, and the proxy is the listener. What each decided about authentication stands. |
| **Related** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) (the Substrate CA issues the proxy's certificate), [ADR-0008](/docs/architecture/decisions/naming-and-dns/0008-host-naming-site-codes/) (service names are aliases of a host), [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) and [ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/) (the services that arrive next) |

---

## Context

**Every tenant-facing service has its own port.** Grafana is on 3000, the tenant downloads on 8443
and the log store on 8427, all on the observability store VM. The Deevnet API is on 8080 and the
state store on 9000, both on the provisioning VM. A tenant has to know five port numbers, and each
is written into tenant code, scripts and bookmarks.

**The port numbers are a symptom of sharing an address.** A service VM holds a domain, not a
service ([ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/)), so several services
share one address, and only one process can listen on 443 there. The unprivileged user a container
runs as is a smaller obstacle than it looks: the tenant DNS server already binds port 53 as one,
with a single capability.

**More services are coming to the same hosts.** The metrics store, the notification service and the
directory are decided and unbuilt. Each would otherwise bring another port, another firewall rule
on the tenant dev segment and another certificate.

**Three things already in place shape the answer.**

- Service names are aliases of the host a service runs on, declared in the inventory, and a host's
  certificate names are derived from the same data
  ([Certificates](/docs/standards/certificates/) 3.1).
- Tenant traffic reaches Platform already translated to one source address, so nothing on Platform
  can tell tenants apart by where a request came from. Each service authenticates its callers.
- A zone rule admits a segment to every listening socket on a host's segment. Every port a service
  opens is reachable from every zone that reaches Platform, whoever it was meant for.

## Decision

### 1. One proxy on each service VM that serves tenants

**Each service VM runs its own proxy, and it fronts only the services on that host.** It is one
more container in the domain. The provisioning VM's proxy serves the API and the state store; the
observability store's serves Grafana, the log store and the tenant downloads.

A host's services keep failing together and with no other host's, as they do today.

### 2. The proxy listens on 443 and routes by name

**A tenant dials a service name and no port.** The proxy terminates TLS, reads the name the client
asked for, and forwards to that service. A name the host does not serve gets no TLS handshake.

The list of names a proxy serves is therefore the complete statement of what that host offers on
443. It is declared in the inventory, beside the aliases.

### 3. Services listen on loopback

**A service behind the proxy is not reachable from its segment at all.** It listens on the host's
loopback address, on its own port number. The proxy listens on the host's segment address, so the
two never contend for a port.

Anything the service exposes that tenants were never meant to reach, such as an administration
console, stops being reachable from other hosts as a consequence.

### 4. The proxy holds the host's server certificate

**One certificate per service VM names the host, every alias and every address.** The Substrate CA
issues it, from the inventory's names, as it issues every substrate certificate. A new alias reaches
the certificate with no change to any role.

A service on loopback serves plain HTTP and holds no certificate or key. The exception is a service
whose certificate directory also carries what it needs for its own outbound calls: it keeps its
certificate, and the proxy verifies it against the Deevnet Root CA under the service's name.

### 5. The proxy routes and decides nothing else

**Authentication stays in each service.** The proxy passes the `Authorization` header through
untouched, adds no identity of its own and holds no list of tenants. It records the address a
request came from in place of whatever the caller claimed.

The name and port the client dialed reach the service unchanged, because the state store verifies a
signature over them and Grafana compares them with the page's origin.

### 6. A new tenant-facing service does not open a port

**A new HTTP service on a service VM is a loopback listener, an alias and a line in the proxy's
list.** It needs no firewall rule on the core router where its host's 443 is already admitted, and
no certificate of its own.

### 7. Old ports are kept, then retired

**The proxy also answers on the port each service used to listen on.** Addresses tenants already
hold, in state, in scripts and on the take-home Pi, keep working. On such a port the proxy answers
whatever name or address was dialed, as the service did.

Retiring those ports is a later change, once nothing a tenant holds names one.

## Consequences

**A tenant remembers names, not ports.** `grafana`, `logs`, `downloads`, `api` and `tfstate` in the
site's zone, each on 443.

**What the tenant dev segment may reach is decided in two places.** The core router admits a host
and port 443. Which services answer there is the proxy's list. The
[segmentation standard](/docs/standards/network-segmentation/) requires the zone policy to say where
the rest of the enforcement lives, and it does.

**Platform services stop being reachable on every port from every admitting zone.** Only the
proxy's ports are open on a host that runs one.

**The proxy is one more thing that can stop a host's services.** If it is down, every tenant-facing
service on that host is unreachable, though each is still running. It holds no state, so recovery is
a restart or a rebuild of the host like any other.

**The key that identifies a service moves.** It was readable by the service's own container user;
it is now readable by the proxy alone. The services hold nothing an attacker could use to
impersonate the host.

**Traffic between the proxy and a service on the same host is not encrypted.** It never leaves the
host's loopback interface.

**Two services keep host-based addresses until their clients move.** The log store was dialed by
host name and port before it had a service name; the proxy's legacy listener answers there.

## Alternatives considered

**One shared proxy VM for the site.** Rejected. Every service name would have to become an alias of
the proxy's host, which breaks the rule that a name follows the host its service runs on. The
provisioning and observability hosts would fail together for HTTPS. The services would stay on
routable addresses, each needing its own host firewall rule to keep callers from going around the
proxy. It is also another VM on a 32 GB hypervisor and another hop.

**One proxy, or one name, per tenant.** Rejected, for the reasons
[CHG-0045](/docs/changes/2026/0045-grafana-service-name/) found when a tenant published its own name
for Grafana: the certificate would need a name per tenant from a list the inventory deliberately
does not hold, and one certificate naming every tenant shows each tenant the others. A per-tenant
proxy would also be created at admission, which is a recurring tenant action the substrate would
have to carry. Tenants are already separated inside each service.

**Give one service the capability to bind 443.** Rejected as the general answer. It works for
exactly one service per host and leaves the rest on their ports.

**An address per service.** Rejected. Every service could then bind 443 itself, but a service name
would stop being an alias of its host, each address is an inventory entry and a certificate, and
nothing would be on loopback.

**Redirect ports at the host firewall.** Rejected. A port redirect cannot choose a service by name,
so it is the same limit as a capability.

**Encrypt between the proxy and every service.** Not chosen as the default. It keeps a certificate
and a key in every service for a connection that never leaves the host. Where a service keeps its
certificate for another reason, the proxy does verify it (§4).

## Open questions

1. **Whether operator-only pages belong behind the same proxy.** A service's metrics or
   administration page is not tenant-facing. Serving it by name on 443 would make it reachable from
   the tenant dev segment unless the proxy restricts it by source, which is a decision the proxy
   does not make today (§5).
2. **Whether the take-home Pi follows.** Its image uses the site's old port numbers so that an
   application moves by changing a host name alone. It can keep them, or run the same proxy.
3. **Whether hosts with no tenant-facing service get one.** The identity VM's services are reached
   by the operator and by other substrate services, on their own ports.
4. **Plain HTTP on port 80.** The proxy does not listen there, so a tenant who types a name without
   `https://` gets a refused connection and not a redirect.

## Current state

Built by [CHG-0046](/docs/changes/2026/0046-service-proxy/). The observability store's proxy
serves `grafana`, `logs` and `downloads`; the provisioning VM's serves `api` and `tfstate`. Each
also answers on its services' old ports. Grafana, the log store's vmauth, the downloads server and
the state store serve plain HTTP on loopback. The Deevnet API keeps its certificate (§4), and its
proxy verifies it.
