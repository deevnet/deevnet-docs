---
title: "ADR-0025: Identity Directory"
weight: -25
aliases:
  - /docs/architecture/decisions/0025-identity-directory/
---

# ADR-0025: Keycloak Is the Substrate's Identity Provider, and the Rebuild Path Stays Clear of It

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21; revised 2026-11-15 (the substrate only: tenants' people and their applications' users are out of scope) |
| **Scope** | How the operator signs in to the substrate's UIs and hosts, and what stays reachable when the directory is down. Not tenants: neither a tenant's people nor its applications' end users. Not machine credentials, which the API and OpenBao issue. |
| **Extends** | [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/), which placed *"later an LDAP or Active Directory–compatible directory"* in the identity VM without choosing one |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/), [ADR-0024: Dashboards](/docs/architecture/decisions/platform-services/0024-dashboards/), [ADR-0028: Tenant Workload Login](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/), [ADR-0033: Code Is the State](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) |

---

## Context

### Every system has its own accounts

Today, each system keeps its own accounts:
- Proxmox has `root@pam` and tokens.
- The core router has local users.
- The Omada controller has a local Owner.
- OpenBao has AppRoles and a recovery key.
- Grafana has its server admin, and one local login per tenant (ADR-0024).

Hosts trust one shared key, `a_autoprov`. The management-plane roadmap has carried *"Evaluate
identity solutions (Keycloak, Authentik, etc.)"* and *"Configure SSO for infrastructure services"*
since it was written.

### What is wanted

1. **The operator signs in once** to the substrate UIs, with a second factor.
2. **Operator login to substrate hosts** comes from short-lived certificates, rather than only from
   a shared key.
3. **Use OIDC first, and SAML or LDAP only where a consumer can't do OIDC.**

### Tenants are out of scope

**Tenants keep the logins they have.** A tenant's person signs in to Grafana with the tenant's
login and reads alerts with its ntfy login; everything else a tenant holds is a machine credential.
One login per person instead of a shared one buys little while those are the only two. A tenant
whose application needs a user directory runs one in its own fabric, as ADR-0010 allows. This
record's first version also covered tenants, with a realm per tenant brokered through the
substrate's; that was set aside on 2026-11-15 and is the first thing that would reopen it.

### What the consumers accept

Vendor documentation was checked on 2026-09-21.

| Consumer | OIDC | SAML | LDAP |
|---|---|---|---|
| Proxmox VE | yes, a realm type, with `autocreate` and a groups claim | — | yes |
| OpenBao | yes, the built-in `jwt`/`oidc` method | — | only as an external plugin |
| Grafana OSS | yes, generic OAuth, with `org_attribute_path` and `org_mapping`, which are in OSS | — | yes |
| **Omada controller** | **no** | **yes, the only admin SSO** | no, its LDAP is for client portals |
| **Core router (OPNsense CE)** | **no**, *"The business edition includes OpenID Connect support"* | — | yes, but *"the privileges have to be defined with the local user manager"* |

**Omada decides the protocol floor.** An identity provider that can't speak SAML can't sign the
operator in to the Omada controller.

---

## Options considered

| | Keycloak | Zitadel | authentik | Kanidm | FreeIPA | lldap + Authelia / Pocket ID |
|---|---|---|---|---|---|---|
| **License** | Apache 2.0 | AGPL-3.0 | MIT (except its enterprise directory) | MPL-2.0 | GPL | GPL-3.0 / Apache 2.0 / BSD |
| **SAML, for Omada** | yes | yes | yes | no | no | no |
| **Hard per-tenant boundary** | **realms**: *"Realms are isolated from one another"* | **organizations** | no; its tenancy is *"alpha"* and Enterprise | no | no | no |
| **Terraform provider** | `keycloak/keycloak`, published by Keycloak | `zitadel/zitadel`, partner tier | `goauthentik/authentik` | third-party | third-party | third-party |
| **Footprint** | Java; *"base memory usage ... 1250 MB"*; PostgreSQL | *"roughly 512MB"*, but four cores for hashing; PostgreSQL | *"2 CPU cores and 2 GB of RAM"*; PostgreSQL | one Rust binary | 4 GB and up; 389-ds, Kerberos, a CA, DNS | small |
| **Linux login** | through federation | no | through its LDAP outpost | **native, `unixd`** | **native, SSSD** | through LDAP |

- **SAML rules out Kanidm, FreeIPA, and lldap with Authelia or Pocket ID.** Kanidm is the best fit
  for Linux login and the lightest, but has no SAML.
- **FreeIPA** brings its own CA and DNS, which would compete with the site's PKI and PowerDNS.
- **That leaves Keycloak, Zitadel and authentik.** The per-tenant boundary, which narrowed the
  first version to Keycloak or Zitadel, no longer counts.

**Keycloak**, for now:
- Its Terraform provider is published by the project.
- It is Apache-licensed; Zitadel is AGPL.
- It is the name every consumer's documentation uses in its own examples.

Its cost is memory. With tenants out, authentik's or Zitadel's lighter footprint may weigh more
(open question 2).

---

## Decision

**Keycloak on the identity VM, with one realm, `deevnet`, for the operator.** No rebuild step and no
machine credential depends on it.

### 1. Placement

- **Keycloak and its PostgreSQL run as separate containers on `dv02idn001v01`**, the identity
  domain ADR-0013 reserved for a directory, beside OpenBao and tenant DNS.
- **The VM grows.** It is 2 vCPU and 2 GB today, and Keycloak's own baseline is 1250 MB. Its size is
  To confirm.
- Its TLS certificate comes from the Substrate CA, as every substrate service's does.

### 2. One realm

**`deevnet` holds the operator's account and the client for each substrate UI**, and is configured
by substrate automation. The operator's account requires passkeys or TOTP.

### 3. The operator signs in once

| Consumer | How |
|---|---|
| Proxmox VE | an OpenID Connect realm against `deevnet` |
| OpenBao | the `oidc` auth method, mapping the operator's group to an operator policy |
| Grafana | generic OAuth against `deevnet`, for the operator; tenants' logins are unchanged |
| Omada controller | SAML against `deevnet`, access through its *"SAML User Group"* |
| Core router | **no SSO.** It stays on local accounts. |

**Why the router has no SSO:**
- OIDC is Business Edition only, and the community plugins are third-party code on the device that
  enforces every zone.
- LDAP would need an LDAP server Keycloak doesn't provide, and the router would still need a local
  user for every account.
- The router is on the rebuild path in any case (§5).

### 4. Host login uses short-lived SSH certificates, not a directory lookup

**The directory never takes part in an SSH login.**
- The operator authenticates to OpenBao through `deevnet`, and OpenBao's SSH secrets engine signs a
  short-lived certificate for the operator's key.
- Hosts trust that CA through `TrustedUserCAKeys`, and don't ask anyone at login time.
- A certificate that has been issued works whether Keycloak, OpenBao or the network is up or not,
  until it expires.
- **`a_autoprov` and its key stay**, as the automation account and as break-glass. This record
  reduces how often a person uses them, not whether they exist.
- **Rejected: SSSD against a directory,** which puts the directory in the path of every login.

### 5. The rebuild path stays clear of the directory

**The site must be rebuildable when Keycloak is gone.** That rule sets these limits:
- **Every consumer keeps a local break-glass administrator:** Proxmox `root@pam`, the router's
  local admin, the Omada local Owner, OpenBao's recovery key and Ansible's AppRole, and Grafana's
  server admin.
- **No machine credential comes from the directory.** Ansible, the API, the egress agent and tenant
  Terraform all authenticate as they do today. The directory is for the operator.
- **Keycloak comes up after OpenBao and the API in the rebuild order** (ADR-0016 §6), and nothing
  before it waits on it.

### 6. The directory holds nothing that can't be made again

- **Its configuration is re-derived** from substrate automation.
- **The operator's credentials are enrolled again** after a loss: a new account, a new passkey or
  TOTP seed, through the break-glass accounts of §5.
- **So its database is not kept data**, as ADR-0033 requires: no backup, and no restore on the
  recovery path.

---

## Consequences

**The operator signs in once**, to everything except the core router, and with a second factor.
Host access moves from a shared key to certificates that expire.

**Tenants see no change.** Their logins, and the API, are untouched.

**The identity VM becomes the heaviest on Platform.** It runs Keycloak's JVM and PostgreSQL beside
OpenBao and tenant DNS. Rebooting it interrupts the operator's sign-in, but not anything already
running, and not SSH with an unexpired certificate.

**One more rule:** a new substrate UI isn't finished until it signs in through `deevnet` and keeps a
local break-glass account.

---

## To accept

**This record is accepted when every item below is done.**

- [ ] An acceptance test: none is stated yet (no What would settle it).
- [ ] Built by a change record: none planned yet.
- [ ] Open question 1 answered: SSH certificate lifetime and principals.
- [ ] Open question 2 answered: Keycloak or a lighter provider.

## Open questions

1. **SSH certificate lifetime and principals.** How long an operator certificate lives, and which
   principals it carries. Whether tenants ever get certificates for their own workloads is
   ADR-0028's question.
2. **Keycloak or a lighter provider.** With one realm and no tenants, authentik or Zitadel may fit
   the identity VM better. Measure before building.

## What would reopen this

- **Tenants needing identity:** their people across more than two logins, or a directory for their
  applications' users as a platform service.
- **Keycloak's memory becoming the reason the identity VM can't hold its other services.**
- **Omada gaining OIDC**, which removes the SAML floor and admits lighter providers.

## To confirm when building

- That OpenBao's SSH secrets engine signs certificates as described on the deployed version, and
  that the site's sshd accepts them.
- That Omada 6.x SAML works against a Keycloak client, following the vendor's current guide.
- Keycloak's actual memory use on the identity VM, next to OpenBao and PowerDNS.

---

## Current state

- **Proposed. Nothing is built.**
- The identity VM runs OpenBao and tenant DNS.
- Every system keeps its own accounts.
