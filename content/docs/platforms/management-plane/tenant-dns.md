---
title: "Tenant DNS"
weight: 4
---

# Tenant DNS Implementation

The authoritative service behind
[ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/). For the model — who owns
what, and why forwarding a zone is not delegating it — see
[Naming and Addressing](/docs/architecture/naming-and-addressing/). This page is the
implementation: what runs, and the specifics that are not guessable from the design.

---

## What runs where

| | |
|---|---|
| **Service** | PowerDNS Authoritative ([version](/docs/platforms/software-catalog/#substrate-service-vms)) |
| **Backend** | SQLite (`gsqlite3`) |
| **Runtime** | Podman container, `pdns-auth`, managed by a systemd unit |
| **Host** | `dv02idn001v01`, the identity service VM, on the management hypervisor (dv02hyp001p01) |
| **Address** | `10.20.25.21`, on the platform segment, DHCP reservation keyed on its declared MAC |
| **Operator alias** | `tdns.mobile.deevnet.net` |
| **Provisioned by** | `deevnet.mgmt`, role `powerdns` |

It runs on the **management** hypervisor, not the tenant one: a service every tenant depends on does
not belong inside the tenant compute domain. It shares the identity VM with OpenBao
([ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/)); the `tenant_dns`
inventory group keeps it movable to its own host.

### Host networking, not published ports

The container uses `--network host`. An authoritative server has to see the real client address to
enforce its per-zone `ALLOW-DNSUPDATE-FROM` check, and a port mapping would rewrite every source
address to the container gateway — silently turning that control into "anyone on the host network".

---

## Specifics that cost time to discover

Each of these was found by running the deployment, not by reading documentation.

### PowerDNS does not create its own schema

It has to be seeded once. The schema ships **inside the image**, but at:

```
/usr/local/share/doc/pdns/schema.sqlite3.sql
```

not `/usr/share`. The upstream image builds PowerDNS from source with `--prefix=/usr/local`, so a
search of `/usr/share` finds nothing and the role aborts reporting that PowerDNS cannot create its
own schema — a true statement that reads convincingly like a missing feature.

The migration scripts sit beside it and all carry a version prefix
(`4.3.1_to_4.7.0_schema.sqlite3.sql`), so an exact-name match resolves to exactly one file.

### The container needs `CAP_NET_BIND_SERVICE`

The image drops to an unprivileged `pdns` user, and 53 is a privileged port. Without the capability:

```
Unable to bind UDP socket to '0.0.0.0:53': Permission denied
Fatal error: Unable to bind to UDP socket
```

systemd then restart-loops it, so the visible symptom is a port-53 readiness check timing out with
nothing in the unit's own output. The container logs carry the real reason.

### The database must be owned by the container's user

The schema is applied by root, so the database the container has to **write** ends up owned by the
wrong user, and PowerDNS starts and then dies with:

```
gsqlite3: connection failed: attempt to write a readonly database
```

The **directory** needs the same ownership as the file — SQLite writes its journal alongside the
database, so a writable file in a read-only directory is still unusable.

The account is `pdns`, uid 953 in the current image. The role reads the uid out of the image rather
than hardcoding it, so an image bump that renumbers the account cannot silently reintroduce this.

This one hides behind the capability problem: it only appears once the server gets far enough to
open its backend.

### `pdnsutil` record names are relative to the zone

`pdnsutil replace-rrset ZONE NAME TYPE` treats `NAME` as **relative**, so passing the zone name
produces `zone.zone` rather than the apex. The apex is `@`:

```bash
# wrong - creates tdemo.mobile.deevnet.net.tdemo.mobile.deevnet.net
pdnsutil replace-rrset tdemo.mobile.deevnet.net tdemo.mobile.deevnet.net NS 3600 ...

# right
pdnsutil replace-rrset tdemo.mobile.deevnet.net @ NS 3600 dv02idn001v01.mobile.deevnet.net
```

### `default-soa-content`, and it is not retroactive

4.9 has `default-soa-content`; `default-soa-name` does not exist. Unset, every created zone gets the
literal placeholder `a.misconfigured.dns.server.invalid` as its SOA primary.

Setting it fixes zones created **afterwards only**. An existing zone's SOA is a stored row, not
something synthesized at query time, so the apex of existing zones has to be reconciled explicitly —
which is why the role does that on every run rather than at creation
([ADR-0005](/docs/architecture/decisions/naming-and-dns/0005-tenant-zone-apex-ownership/)).

### The apex NS cannot be `tdns`

`tdns` is a host **alias** on the resolver, so it resolves as a CNAME, and RFC 2181 §10.3 forbids an
NS record pointing at an alias. The apex NS names the host's own address record,
`dv02idn001v01.mobile.deevnet.net`. `tdns` remains an operator convenience and the value tenants
point their updates at — neither of which is a delegation.

---

## Deliberate configuration choices

**The HTTP API is on for the Deevnet API alone.** Its key is global to the server, so any holder can
write every tenant's zone — the reason ADR-0004 chose dynamic update for tenants. The key is given
only to the Deevnet API ([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)
§6), and `webserver-allow-from` refuses every address but the API host's. Tenants still publish over
RFC 2136 with a TSIG key bound to their own zone. With no API key in the vault the role turns the
API off, and `pdnsutil` is the only way in.

**AXFR is disabled.** No secondary exists yet. When one is added, it is allowed by address rather
than by opening transfers generally.

**`version-string=anonymous`, `log-dns-details=no`.**

---

## Zone lifecycle

The Deevnet API creates a tenant's zones on admission and re-ensures them on every reconcile, through
the PowerDNS HTTP API. For each tenant it ensures:

- a forward zone, `<tenant>.<site>.deevnet.net`, and its reverse zone
- a TSIG key named for the tenant
- `TSIG-ALLOW-DNSUPDATE`, binding that key to the tenant's zones only
- `ALLOW-DNSUPDATE-FROM`, the management, trusted and tenant-transit subnets
- the apex NS, `dv02idn001v01.mobile.deevnet.net`

**The TSIG secret comes from the API, never generated on the server.** A generated key would not
survive a rebuild, and every tenant's IaC would need re-issuing. After a rebuild, a reconcile puts
the same keys back.

The apex SOA is reconciled rather than replaced wholesale: the serial is carried forward and bumped
when the content actually changes. Resetting it would make the zone look permanently stale to any
future secondary; bumping it unconditionally would churn it on every run.

A healthy apex names the server, not the placeholder:

```
tdemo.mobile.deevnet.net  3600 IN NS   dv02idn001v01.mobile.deevnet.net.
tdemo.mobile.deevnet.net  3600 IN SOA  dv02idn001v01.mobile.deevnet.net. hostmaster.tdemo.mobile.deevnet.net. ...
```

To check the service, see [Verify Site → Tenant DNS](/docs/runbook/substrate/building-recovery/build-verification/#tenant-dns).
