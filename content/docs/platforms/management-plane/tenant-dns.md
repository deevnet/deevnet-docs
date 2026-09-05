---
title: "Tenant DNS"
weight: 3
---

# Tenant DNS Implementation

The authoritative service behind
[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/). For the model — who owns
what, and why forwarding a zone is not delegating it — see
[Naming and Addressing](/docs/architecture/substrate/naming-and-addressing/). This page is the
implementation: what runs, and the specifics that are not guessable from the design.

---

## What runs where

| | |
|---|---|
| **Service** | PowerDNS Authoritative 4.9.17 |
| **Backend** | SQLite (`gsqlite3`) |
| **Runtime** | Podman container, `pdns-auth`, managed by a systemd unit |
| **Host** | `tenant-mgmt-vm01` on the management hypervisor (hv01) |
| **Address** | `10.20.99.30`, DHCP reservation keyed on its declared MAC |
| **Operator alias** | `tdns.mobile.deevnet.net` |
| **Provisioned by** | `deevnet.mgmt`, role `powerdns` |

It runs on the **management** hypervisor, not the tenant one: a service every tenant depends on does
not belong inside the tenant compute domain.

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
pdnsutil replace-rrset tdemo.mobile.deevnet.net @ NS 3600 tenant-mgmt-vm01.mobile.deevnet.net
```

### `default-soa-content`, and it is not retroactive

4.9 has `default-soa-content`; `default-soa-name` does not exist. Unset, every created zone gets the
literal placeholder `a.misconfigured.dns.server.invalid` as its SOA primary.

Setting it fixes zones created **afterwards only**. An existing zone's SOA is a stored row, not
something synthesised at query time, so the apex of existing zones has to be reconciled explicitly —
which is why the role does that on every run rather than at creation
([ADR-0005](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/)).

### The apex NS cannot be `tdns`

`tdns` is a host **alias** on the resolver, so it resolves as a CNAME, and RFC 2181 §10.3 forbids an
NS record pointing at an alias. The apex NS names the host's own address record,
`tenant-mgmt-vm01.mobile.deevnet.net`. `tdns` remains an operator convenience and the value tenants
point their updates at — neither of which is a delegation.

---

## Deliberate configuration choices

**The HTTP API is off.** Its key is global to the server, so exposing it would give any holder write
access to every tenant's zone — the reason ADR-0004 chose dynamic update over the API. Zone and key
administration is done with `pdnsutil`, which reads the database directly.

**AXFR is disabled.** No secondary exists yet. When one is added, it is allowed by address rather
than by opening transfers generally.

**`version-string=anonymous`, `log-dns-details=no`.**

---

## Zone lifecycle

Onboarding a tenant creates, per tenant, a forward and a reverse zone:

```bash
pdnsutil create-zone      tdemo.mobile.deevnet.net
pdnsutil import-tsig-key  tdemo hmac-sha256 <secret from vault>
pdnsutil set-meta         tdemo.mobile.deevnet.net TSIG-ALLOW-DNSUPDATE tdemo
pdnsutil set-meta         tdemo.mobile.deevnet.net ALLOW-DNSUPDATE-FROM 10.20.99.0/24
pdnsutil replace-rrset    tdemo.mobile.deevnet.net @ NS  3600 tenant-mgmt-vm01.mobile.deevnet.net
```

All of it is driven from the declared tenant list, so it is one automation run rather than a
checklist.

TSIG secrets are **imported from the vault, never generated on the server**. A generated key would
not survive a rebuild, and every tenant's IaC would need re-issuing.

The apex SOA is reconciled rather than replaced wholesale: the serial is carried forward and bumped
when the content actually changes. Resetting it would make the zone look permanently stale to any
future secondary; bumping it unconditionally would churn it on every run.

---

## Verifying it

```bash
# the service itself
dig @10.20.99.30 tdemo.mobile.deevnet.net SOA
dig @10.20.99.30 tdemo.mobile.deevnet.net NS

# through the resolver, which is what clients actually do
dig @10.20.99.1 tdemo.mobile.deevnet.net SOA

# what the server actually holds
podman exec pdns-auth pdnsutil list-all-zones
podman exec pdns-auth pdnsutil list-zone tdemo.mobile.deevnet.net
```

A healthy apex names the server, not the placeholder:

```
tdemo.mobile.deevnet.net  3600 IN NS   tenant-mgmt-vm01.mobile.deevnet.net.
tdemo.mobile.deevnet.net  3600 IN SOA  tenant-mgmt-vm01.mobile.deevnet.net hostmaster.tdemo... 1 ...
```

The namespace boundary is worth testing rather than assuming: an update signed with one tenant's key
and aimed at another tenant's zone must be REFUSED by the server.
