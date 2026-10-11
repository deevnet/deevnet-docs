---
title: "ADR-0037: Tenant Service Certificates"
weight: -37
---

# ADR-0037: A Tenant Service CA Issues Server Certificates for Names in a Tenant's Own Zone

|  |  |
|--|--|
| **Status** | Proposed: to be built by [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |
| **Date** | 2026-10-11 |
| **Scope** | Where a tenant workload's own service gets a server certificate that chains to the Deevnet Root CA: which CA signs it, who may ask, for which names, and what the certificate says. Not device identity ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §6, unchanged), not who may reach a tenant's service, and not revocation, which stays open. |
| **Extends** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/): answers its open question 2, and adds a third issuing CA to §3's two. |
| **Amends** | ADR-0031 §3 ("Two issuing CAs per site") and §4 ("ADR-0016 §3's `pki/` row becomes: issues tenant device certificates only"): OpenBao also issues tenant service certificates. [Certificates standard](/docs/standards/certificates/) 1.2 and the tables of §1, §2, §4, §5 and §6. |
| **Related** | [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) (the Deevnet API), [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §13 (a tenant's names), [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) (OpenBao), [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §5–§6 (lifetimes and renewal), [ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/) (the substrate's own services on 443) |

---

## Context

**A tenant workload cannot serve HTTPS that the site trusts.** The two issuing CAs each have one
job, and neither is this one:

- the Substrate CA issues the substrate's own server certificates, and only those
  ([Certificates standard](/docs/standards/certificates/) 1.2);
- the Tenant Device CA is for devices' client certificates, and only those.

A tenant that serves a page from a workload either serves it in the clear or makes a CA of its own
that nobody else trusts. ADR-0031 left this open as question 2: *"Where do tenant workloads' own
services get server certificates? From the site, as a third issuing CA, or from the tenant itself."*

**The first tenant service that people look at exists.** The `eds` tenant serves a console from its
workload, at a name in its own zone, over plain HTTP. It is acceptable only because the page changes
nothing. A tenant service with a login or a control cannot be served that way.

**Three things already in place shape the answer.**

- A tenant's names are its own. Its zone is `<tenant>.<site>.deevnet.net`, derived by the API from
  the tenant's name, and the tenant publishes into it through the API or with its own DNS update
  key.
- Every client that matters already trusts the Deevnet Root CA and nothing below it. A certificate
  from any issuing CA under the Site CA is accepted with no new trust to distribute.
- The Site CA is name-constrained to `deevnet.net` and private addresses, so nothing issued beneath
  it can vouch for a public name.

## Decision

### 1. A third issuing CA per site, the Tenant Service CA

**Each site gains a Tenant Service CA**, signed by its Site CA in the same ceremony as the other
two: `O=Deevnet, OU=<Site> Site, CN=Deevnet <Site> Tenant Service CA`. RSA 3072, five years,
`pathlen:0`, the standard issuing profile.

| | Substrate CA | Tenant Device CA | Tenant Service CA |
|---|---|---|---|
| Key | the site's ansible-vault | inside OpenBao | inside OpenBao |
| Issued by | Ansible, on the control node | OpenBao, through the Deevnet API | OpenBao, through the Deevnet API |
| Issues | every substrate server certificate | tenant devices' client certificates | server certificates for names in a tenant's own zone |
| Usage | `serverAuth` only | `clientAuth` only | `serverAuth` only |

**Its key is generated inside OpenBao, on a mount of its own**, and only its signing request goes to
the ceremony, as the Tenant Device CA's did. The two tenant CAs do not share a mount, a key or a
signing role.

### 2. A tenant asks through the Deevnet API, with a signing request

**The tenant makes the key and keeps it.** It sends a signing request for a name; the certificate and
its chain come back. The key never enters the substrate, which is the rule devices already follow
(Certificates standard 5.3).

**Only the tenant itself, or the operator, may ask**, with the tenant's own API token, as for every
other object a tenant owns.

**The request is read for its public key and nothing else.** The subject, the names, the usages and
the lifetime come from the issuer's profile, never from the request (Certificates standard 4.6).

### 3. A certificate names only what is in the tenant's own zone

**A tenant sends labels, never names.** The API builds each name as `<label>.<tenant>.<site>.deevnet.net`,
exactly as it builds the name of a DNS record or a workload. A tenant cannot spell a name outside
its zone, because it never spells a zone.

- One label is the certificate's own, and its CN. More may be added as further DNS names.
- **No wildcard, no IP address, no name outside the zone**, and no URI.
- A label does not have to be one the API published. A tenant may publish names with its own DNS
  update key, which the API does not see, so the API's registry is not the list of names in a zone.
  The zone is the boundary.

**The secret store holds the same line.** The signing role in OpenBao permits only names at least
two labels below the site's zone. Every tenant name is; no substrate name is. So a fault in the API
alone cannot produce a certificate for `grafana.<site>.deevnet.net`.

### 4. What the certificate says

| | |
|---|---|
| Subject | `O=Deevnet, OU=<Site> Tenant Services, CN=<label>.<tenant>.<site>.deevnet.net` |
| Names | DNS only: the CN, and any further names asked for |
| Key | RSA 2048 or larger, or P-256; whichever the tenant made |
| Lifetime | one year |
| Usage | `critical, digitalSignature, keyEncipherment`; `serverAuth` only |

**The OU names the site, not the tenant.** A device's certificate carries its tenant in the OU,
because a broker authorizes a device by what its certificate says. Nothing authorizes a server by
its OU: a client checks the name it dialed, and the tenant is in that name. One profile for every
tenant is what lets OpenBao hold one signing role that the API may use and may not change.

**The server presents the leaf, the Tenant Service CA and the Site CA**, never the root, as every
substrate service does. A client that holds only the root can then build the chain.

### 5. Reissue is the tenant's, and nothing renews by itself

**A certificate is reissued by asking again.** The API keeps each certificate it issued, which is
public, and answers a repeated request for the same key and names with the same certificate while
more than 60 days remain. With fewer, or with a new key or a changed name, it issues another.

**Renewal is an apply.** The provider plans a reissue once fewer than 60 days remain, so a tenant
that applies its configuration inside those 60 days renews. Nothing renews a certificate for a
tenant that does not, as nothing does for the substrate
([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §6).

### 6. The Substrate CA still issues nothing for a tenant

**Certificates standard 1.2 keeps its first sentence.** A tenant never holds a key certified by the
CA that identifies the substrate. The substrate's own certificates still do not depend on OpenBao
(ADR-0031 §4): this CA is for what tenants build, which exists only once the substrate does.

---

## Consequences

**A tenant workload can serve HTTPS that every Deevnet client already trusts.** No trust is
distributed, no port or proxy is added, and the tenant holds its own key.

**Anyone who trusts the root now trusts what this CA issues, for any name under `deevnet.net`.** The
Site CA's name constraints bound it to Deevnet's names; nothing in the hierarchy bounds it to
tenants' names. A certificate from this CA for a substrate name would be accepted by a browser.
Two things stand in the way, and both must fail: the API builds names only inside the caller's zone,
and the signing role refuses a name that is not at least two labels below the site's zone.

**OpenBao is a signer for tenants, and the API can ask it.** The API's policy gains one path, signing
on one role. It cannot read the CA's key, change the role or create another.

**There is no revocation.** No CRL or OCSP is published (ADR-0031). A tenant's leaked key identifies
its service until the certificate expires, up to a year. A tenant that loses a key makes a new one
and asks again; the old certificate is not withdrawn.

**A third issuing CA is a third ceremony**, every five years, and after any loss of it.

**A certificate is a thing that expires, in a model that so far had none.** A tenant's other objects
are right until someone changes them. This one goes wrong by itself after a year, and a tenant that
applies nothing for ten months will find its service refused.

**Tenant service leaves name a site, not a tenant, in their OU.** A person reading *Issued To* finds
the tenant in the name.

**The secret store's key custody question now covers two CAs.** Whether a CA key that OpenBao holds
is also kept elsewhere is
[CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)'s to settle, for both.

---

## Alternatives considered

- **Rejected: the Substrate CA issues tenant certificates.** No ceremony and no new CA. But a tenant
  would hold a key certified by the CA that identifies the substrate, and that CA's key is on the
  control node, where the API cannot use it and should not.
- **Rejected: the Tenant Device CA issues both.** No ceremony. One CA would then certify tenants'
  servers and tenants' devices, and the broker is to accept client certificates from that CA. The
  separation of server and device identity (Certificates standard 4.5) would rest on an extension
  in each certificate, not on which CA signed it.
- **Rejected: a proxy on a service VM fronts tenant services**
  ([ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/)). The substrate
  would hold the certificate and terminate the tenant's TLS. A proxy fronts only its own host's
  services, and the tenant fabric admits nothing inbound from Platform.
- **Rejected: each tenant makes its own CA.** Nothing but that tenant trusts it. Every person who
  opens the page installs another anchor, which is what one root was chosen to avoid.
- **Not now: a signing role per tenant**, with the tenant's zone as the role's only permitted domain
  and the tenant in the OU. The secret store would then enforce the zone exactly. It means the API
  creates roles, which is a wider grant than signing on one, for a check the API already makes.
- **Not now: short-lived certificates renewed by an agent on the workload.** It would answer
  revocation and renewal together. It needs an identity for a workload to ask with, which is
  [ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/)'s, unbuilt.
- **Not now: the API makes the key.** Simpler for a tenant with no tooling. A private key would
  cross the API and rest in a tenant's state, where today only a request does.

---

## Open questions

1. **How is a tenant service certificate revoked?** The same question as ADR-0031's third, for a
   certificate with no party that authorizes it by name.
2. **Should a tenant be told a certificate is close to expiry?** Nothing watches one today.
