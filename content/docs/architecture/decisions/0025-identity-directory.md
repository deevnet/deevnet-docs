---
title: "ADR-0025: Identity Directory"
weight: 25
---

# ADR-0025: Keycloak Is the Identity Provider, With a Realm per Tenant and the Rebuild Path Kept Clear of It

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21 |
| **Scope** | Who can sign in to what, and how. This covers the operator on substrate UIs and hosts, each tenant's people on the UIs the substrate offers them, and a tenant application's own end users. It also covers how tenants are separated and what stays reachable when the directory is down. Not machine credentials, which the API and OpenBao issue. |
| **Extends** | [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), which placed *"later an LDAP or Active Directory–compatible directory"* in the identity VM without choosing one; [ADR-0024: Dashboards](/docs/architecture/decisions/0024-dashboards/), whose local Grafana logins it replaces for people |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §4, [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/), [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/), [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/), [ADR-0023: Metrics and Alerting](/docs/architecture/decisions/0023-metrics-and-alerting/) |

---

## Context

### Every system has its own accounts

Today, each system keeps its own accounts:
- Proxmox has `root@pam` and tokens.
- The core router has local users.
- The Omada controller has a local Owner.
- OpenBao has AppRoles and a recovery key.
- Grafana, once built, will have one local login per tenant (ADR-0024).

Hosts trust one shared key, `a_autoprov`. The management-plane roadmap has carried *"Evaluate
identity solutions (Keycloak, Authentik, etc.)"* and *"Configure SSO for infrastructure services"*
since it was written.

### What is wanted

1. **The operator signs in once** to the substrate UIs.
2. **Operator login to substrate hosts** comes from the directory, rather than only from a shared key.
3. **Each tenant's people sign in** to what the substrate offers them, such as dashboards, and are
   managed by the tenant rather than by the operator.
4. **A tenant's application can use the directory for its own end users.** This is identity as a
   service.
5. **Tenants are separated hard.** Each has its own user namespace, not a group in a shared one.
6. **Use OIDC first, and LDAP only where a consumer can't do OIDC.**

### What the consumers accept

Vendor documentation was checked on 2026-09-21.

| Consumer | OIDC | SAML | LDAP |
|---|---|---|---|
| Proxmox VE | yes, a realm type, with `autocreate` and a groups claim | — | yes |
| OpenBao | yes, the built-in `jwt`/`oidc` method | — | only as an external plugin |
| Grafana OSS | yes, generic OAuth, with `org_attribute_path` and `org_mapping`, which are in OSS | — | yes |
| vmauth | validates JWTs in the open-source build, from v1.137.0 | — | — |
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

- **Only Keycloak and Zitadel meet requirement 5 and speak SAML.**
- **Kanidm** is the best fit for Linux login and the lightest option, but it has no SAML and no
  tenant boundary.
- **FreeIPA** brings its own CA and DNS, which would compete with the site's OpenBao PKI and
  PowerDNS.
- **authentik** would need tenant separation built out of policies inside one instance.

**Keycloak or Zitadel.**
- Zitadel is lighter and its organizations are an explicit multi-tenant hierarchy. Keycloak's
  realms are the older and more widely integrated boundary.
- Keycloak's Terraform provider is published by the project.
- Keycloak is Apache-licensed; Zitadel is AGPL.
- Keycloak is also the name every consumer's documentation uses in its own examples. MinIO's reads
  *"such as Okta, Auth0, Keycloak"*.

The weight tips to Keycloak. Its cost is memory.

---

## Decision

**Keycloak on the identity VM, with one realm for the substrate and one realm per tenant.** No
rebuild step and no machine credential depends on it.

### 1. Placement

- **Keycloak and its PostgreSQL run as separate containers on `dv02idn001v01`**, the identity
  domain ADR-0013 reserved for a directory, beside OpenBao and tenant DNS.
- **The VM grows.** It is 2 vCPU and 2 GB today, and Keycloak's own baseline is 1250 MB. Its size is
  To confirm.
- It is on Platform, so tenants, the operator and every OIDC consumer reach it with rules that exist
  today.
- Its TLS certificate comes from the site CA in OpenBao, as every Platform service's does.

### 2. Realms

| Realm | Holds | Managed by |
|---|---|---|
| `deevnet` | the operator's account; the OIDC and SAML clients for every substrate UI; the brokers to tenant realms (§4) | substrate automation |
| one per tenant, named for it | the tenant's people and its applications' end users and clients | the tenant, through its own Terraform |

- **The API creates a tenant's realm when it creates the tenant** (ADR-0015). It also creates a
  service-account client in that realm with realm-management roles for that realm only, and returns
  the client's secret like every other tenant credential.
- **The tenant uses the `keycloak/keycloak` provider from the offline mirror**, authenticated as that
  client. Keycloak scopes a realm's management roles to that realm, so the tenant can manage its own
  users, groups, clients and flows, and nothing in another realm.
- **The client secret is set by the API, not generated by Keycloak**, so that after a rebuild it can
  be restored from tenant state (ADR-0012 §4). To confirm.

### 3. The operator signs in once

The operator's account is in `deevnet`, with passkeys or TOTP required.

| Consumer | How |
|---|---|
| Proxmox VE | an OpenID Connect realm against `deevnet` |
| OpenBao | the `oidc` auth method, mapping the operator's group to an operator policy |
| Grafana | generic OAuth against `deevnet` (§4) |
| Omada controller | SAML against `deevnet`, access through its *"SAML User Group"* |
| Core router | **no SSO.** It stays on local accounts. |

**Why the router has no SSO:**
- OIDC is Business Edition only, and the community plugins are third-party code on the device that
  enforces every zone.
- LDAP would need an LDAP server Keycloak doesn't provide, and the router would still need a local
  user for every account.
- The router is on the rebuild path in any case (§6).

### 4. Tenant people reach substrate UIs through the `deevnet` realm

A substrate UI such as Grafana supports one OIDC issuer. With a realm per tenant, there are many.
So:

- **Each tenant realm is linked into `deevnet` as an identity provider** (Keycloak's realm-to-realm
  brokering). A tenant's person signs in to Grafana through `deevnet`, chooses their tenant, and
  authenticates in their own realm.
- **`deevnet` stamps a `tenant` claim from the broker the login came through.** The claim is not
  copied from anything the tenant realm asserts, so a tenant realm's administrator can't make its
  users claim another tenant. This is the pattern ADR-0023 uses when the substrate stamps the tenant
  label on alerts.
- **Grafana maps that claim to the tenant's organization** with `org_attribute_path` and
  `org_mapping`, at Editor. ADR-0024's restriction still holds.
- **ADR-0024's per-tenant Grafana login becomes machine-only**, used by the tenant's Terraform.
  People sign in through the directory.
- **vmauth can later accept the same tokens.** It validates JWTs and routes on claims in its
  open-source build. That would let a person's browser query their tenant's partitions with no
  shared read token. It is not done in v1, and a recent vmauth advisory fixed an *"authorization
  bypass in JWT-based routing when `match_claims` values are used"*, which argues for waiting.

### 5. Host login uses short-lived SSH certificates, not a directory lookup

**The directory never takes part in an SSH login.**
- The operator authenticates to OpenBao through `deevnet`, and OpenBao's SSH secrets engine signs a
  short-lived certificate for the operator's key.
- Hosts trust that CA through `TrustedUserCAKeys`, and don't ask anyone at login time.
- A certificate that has been issued works whether Keycloak, OpenBao or the network is up or not,
  until it expires.
- **`a_autoprov` and its key stay**, as the automation account and as break-glass. This record
  reduces how often a person uses them, not whether they exist.
- **Rejected: SSSD against a directory,** which puts the directory in the path of every login, and
  Kanidm's `unixd`, which would be a second identity system.

### 6. The rebuild path stays clear of the directory

**The site must be rebuildable when Keycloak is gone.** That rule sets these limits:
- **Every consumer keeps a local break-glass administrator:** Proxmox `root@pam`, the router's
  local admin, the Omada local Owner, OpenBao's recovery key and Ansible's AppRole, and Grafana's
  server admin.
- **No machine credential comes from the directory.** Ansible, the API, the egress agent, vmagent,
  and tenant Terraform's own client all authenticate as they do today. The directory is for people.
- **Keycloak comes up after OpenBao and the API in the rebuild order** (ADR-0016 §6), and nothing
  before it waits on it.

### 7. The directory holds data that exists nowhere else

- **Realm configuration can be re-derived.** `deevnet` comes from substrate automation, and each
  tenant realm comes from the tenant's Terraform.
- **Its users' credentials can't be re-derived.** That covers passwords, passkeys and TOTP seeds,
  for the operator, for tenants' people, and for tenants' application end users.
- **This is an exception to ADR-0010 §4**, which says the substrate is *"never the only copy"* of
  tenant content. For credentials, the directory is the only copy, and no tenant copy can exist.
- **The exception is accepted, and it is what makes Keycloak's database kept data**, under the
  ADR-0014 approach:
  - a data disk
  - a scheduled backup, copied off the VM
  - a restore rehearsed before this record is accepted
- **A tenant may decline** requirement 4 and run its own identity provider in its fabric, as
  ADR-0010 allows. The cost of declining is stated: no brokered sign-in to substrate UIs for its
  people.

---

## Consequences

**The operator signs in once**, to everything except the core router, and with a second factor.
Host access moves from a shared key to certificates that expire.

**Tenants get a directory of their own.** They get their people for substrate UIs and their
applications' end users, managed in their Terraform, with a boundary Keycloak enforces between
realms.

**The substrate now holds tenant credentials that exist nowhere else.** That is a first for this
site. Losing Keycloak's database without a backup locks every tenant's end users out, and nothing in
any tenant's repository can restore them.

**The identity VM becomes the heaviest on Platform.** It runs Keycloak's JVM and PostgreSQL beside
OpenBao and tenant DNS. Rebooting it now also interrupts sign-in everywhere, but not anything already
running, and not SSH with an unexpired certificate.

**The API grows again.** It gains a Keycloak backend: realms, the tenant's management client and the
broker link, with the same reconcile and resupply as the others.

**One more rule:** a new substrate UI isn't finished until it signs in through `deevnet` and keeps a
local break-glass account.

---

## Open questions

1. **Keycloak Organizations instead of realms.** Keycloak also has an in-realm organizations
   feature, which would give one issuer for everything and no brokering. Can a tenant administer
   only its own organization's members? If so, it might replace §4's brokering.
2. **SSH certificate lifetime and principals.** How long an operator certificate lives, and whether
   tenant people ever get certificates for their own workloads. That would connect this record to
   the tenant SSH-key backlog.
3. **Backup target.** The same off-VM replica ADR-0014 plans for the provisioning VM, or a separate
   one?
4. **Tenant realm limits.** Brute-force protection, password policy and user counts. Are these the
   tenant's choice, or does the substrate set a floor?

## What would reopen this

- **Keycloak's memory becoming the reason the identity VM can't hold its other services.** Zitadel
  is the fallback, with the same shape.
- **Omada gaining OIDC**, which removes the SAML floor and admits lighter providers.

## To confirm when building

- That a realm-management service account in a tenant realm is refused in every other realm and in
  `deevnet`.
- That a client secret can be set by the API on create, and set again on resupply.
- That a claim `deevnet` stamps from the broker can't be overridden by anything the tenant realm
  sends. Test it, don't assume it.
- That Grafana OSS's `org_mapping` places a brokered user in the right organization at Editor, and
  in no other.
- That OpenBao's SSH secrets engine signs certificates as described on the deployed version, and
  that the site's sshd accepts them.
- That Omada 6.x SAML works against a Keycloak client, following the vendor's current guide.
- Keycloak's actual memory use on the identity VM, next to OpenBao and PowerDNS.

---

## Current state

- **Proposed. Nothing is built.**
- The identity VM runs OpenBao and tenant DNS.
- Every system keeps its own accounts.
