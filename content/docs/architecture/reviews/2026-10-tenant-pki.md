---
title: "2026-10 Tenant PKI"
weight: -20261021
---

# Review: Tenant PKI, October 2026

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Scope** | The first draft of [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) (tenants beside sites in the PKI), against the PKI, OpenBao, the API, the ceremony tools, `deevnet-kit` and the records it touches |
| **Criteria** | The owner's principles for the mobile site as a tenant factory: identity outlives location; the factory is autonomous; CA custody is stable; certificates travel, authorities remain; renewal is maintenance; independence is a choice; trust transitions are explicit; security boundaries are enforceable; no dependency on the home site; onboarding is self-service |
| **Method** | A read of ADR-0016, 0031, 0037 and the Certificates and Naming standards, `deevnet.mgmt` (the OpenBao role, the PKI playbooks, `scripts/pki/`), `deevnet-provisioning-api` (issuance, admission, `deevnet-kit`) at their GitHub heads, and the records they cite. Findings come from reading code, not running it; the [validation plan](#validation-plan) is what would run it |
| **Status** | Open. Its findings are taken up by ADR-0039 (rewritten), [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) and [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/), all Proposed |

---

## Summary

**The first draft's shape holds.** A Tenants CA beside the Site CAs fits the root's `pathlen:2`;
per-tenant CAs let a device pin an anchor no other tenant shares; and the API already refuses a
request from anyone but the tenant or the operator, so a request alone authorizes nothing.

**Its custody does not.** It moved a tenant's CA keys between sites, which the owner rejects; it put
an online key that can make CAs on a kit that unseals itself and has no backup; and it leaned on
name constraints in places where the clients that matter do not enforce them.

**Its scope was too wide.** Names and the take-home Pi are decisions of their own, and are now
ADR-0040 and ADR-0041.

---

## Assessment

### What is sound

- **A Tenants CA beside the Site CAs fits the hierarchy as built.** Root `pathlen:2` → Tenants CA
  `pathlen:1` → tenant CAs `pathlen:0` → leaves. No re-root.
- **Per-tenant CAs give an enforceable device boundary.** mbedTLS verifies a chain against its
  anchor's key, so a device anchored at its tenant's Service CA refuses a CA made with any other key,
  whatever its name. That holds even if the Tenants CA is stolen.
- **A request does not authorize.** `ownTenant` admits only the operator or the tenant's own token
  (`internal/server/tenants.go`); the request is read for its public key alone (ADR-0037 §2).
- **Separating server and device identity by signer** is what ADR-0031 §3 and ADR-0037 already
  chose; two CAs per tenant keeps it.

### What must change

| | Finding | Taken up in |
|---|---|---|
| F1 | **Moving CA keys between sites** (draft §6) changes custody with every move. Rejected by the owner | ADR-0039 §1 |
| F2 | **The online Tenants CA sits on a kit that unseals itself.** The static seal key is written to the same host as the data (ADR-0016 §2), and nothing backs OpenBao up (backup runbook: "Nothing yet"). A lost kit loses every tenant CA; a stolen one exposes a key that can make CAs | ADR-0039 §3 |
| F3 | **Custody rules disagree.** Standard §5.2 says an issuing key is "generated where it lives"; CHG-0036 (agreed in review R1) says a key OpenBao can't re-derive is held in ansible-vault; the draft said inside OpenBao | ADR-0039 §3 |
| F4 | **The ceremony tools have no path for the root to sign a request.** Only a Site CA signs `pathlen:0` requests, and file names assume a site (`scripts/pki/`, standard §6) | ADR-0039 §2, Consequences |
| F5 | **"The API has one path" is wrong.** Making a tenant's CAs needs issuer generation, `sign-intermediate` (whose constraints the caller sets) and signing per issuer | ADR-0039 Consequences |
| F6 | **"No operator" is wrong.** Creating a tenant follows an operator's admission (`POST /v1/admissions` is operator-only). Self-service means no ceremony, not no admission | ADR-0039 §2 |
| F7 | **Exclusions are fixed at signing.** A site added later, the Builder (`dv00bld001p01.deevnet.net`) and apex aliases are not excluded, and with no revocation a re-signed CA leaves the old certificate valid | ADR-0039 §4, ADR-0040 §1 |
| F8 | **A URN cannot be name-constrained**, so a device's tenant is bound by the broker or not at all | ADR-0039 §6 |
| F9 | **Standard 1.3 allows only the root as an anchor**, and devices anchor at the root today | ADR-0039 §5 |
| F10 | **A site's shared broker presents a Substrate certificate**, so a device moving between sites changes anchor unless the site presents a tenant-issued certificate | ADR-0039 §5 |
| F11 | **`deevnet-kit` puts the Pi's addresses in its certificate**, which a tenant Service CA would refuse | ADR-0041 §2 |
| F12 | **Tenant names are checked for shape only**: `home` and `mobile` pass, and there is no reserved list | ADR-0040 §2 |
| F13 | **"The Service CA has issued one certificate"** leaves out CHG-0047's probe certificates, reissued on every run | ADR-0039 §9 |

### What is unresolved

- **The seal** (ADR-0039 open question 1): operator unseal, a seal key carried apart, or the risk
  accepted. This is the one that most decides how much the Tenants CA can be trusted.
- **Tenant names at the apex or under a subtree** (ADR-0040 §1): the owner prefers the apex; the
  subtree is the only constraint that does not age.
- **SNI on the broker** (ADR-0039 open question 2).
- **Where an independent Pi's CA key lives** (ADR-0041 §4).

### Where the principles pull against each other

- **"Onboarding is self-service" against "the Tenants CA is offline".** A tenant's CAs can only be
  made at creation by an online key. ADR-0039 keeps the CA online and puts the weight on its custody.
- **"The factory is autonomous" against "a stolen factory is a stolen authority".** Unattended
  restarts need the seal key on the kit. ADR-0039 leaves the seal open.
- **"Certificates travel" against "the substrate never holds a tenant key"**: a site's broker
  presenting a tenant's certificate holds a key for a name in a tenant zone. It is the opposite
  direction from ADR-0037 §6, which keeps tenants from holding substrate keys, and is recorded as a
  consequence.

---

## Decomposition

| Record | Decides |
|---|---|
| [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) (rewritten) | Tenant PKI identity and CA ownership independent of location: the factory as authority, the hierarchy, the Tenants CA's custody and risks, what constraints do and don't do, device anchors, device binding, renewal as maintenance, lifecycles in principle, the site-level tenant CAs' retirement |
| [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) (new) | Tenant names without a site: apex or subtree, reserved labels, who answers a tenant's zone |
| [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) (new) | The take-home Pi: `pki=deevnet`, `own`, `bring`; provisioning, renewal, devices away from the factory, recovery, and changing choice |

---

## Impact

| Area | What changes, on acceptance |
|---|---|
| **ADRs** | ADR-0031 §3, §5, §6 (amended); ADR-0037 §1, §3 (amended); ADR-0004 §2 and ADR-0015 §13 (names, amended); ADR-0016 §2 (if the seal changes); ADR-0008's note on the tenant pattern; ADR-0030 §4's "the Pi's own CA" (now one choice of three) |
| **Standards** | Certificates §1 (a tier beside the Site CAs; 1.3's root-only anchor), §3.3 (device URI), §4 (Tenants CA profile), §5 (where the Tenants and tenant CA keys live), §6 (file names for a CA with no site). Naming §5.1–§5.3 |
| **Records** | CHG-0034 planned again against per-tenant Device CAs; CHG-0036's scope widened to the Tenants CA; CHG-0047's probe certificates left to expire |
| **API** | `Site.Zone`; tenant creation makes two issuers; issuance signs on the tenant's issuer; device certificates set the new URI; reserved names |
| **OpenBao** | A Tenants issuer, two issuers per tenant, a wider API policy, Raft snapshots kept off the kit, and possibly a different seal |
| **DNS** | Tenant zones outside the site zone, forwarded by the resolver; reverse zones unchanged |
| **Broker** | Client certificates from the Tenants branch with an issuer-to-URI check; a tenant-issued certificate per tenant by SNI, or a stream proxy |
| **Firmware** (tenants') | The anchor becomes the tenant's Service CA; the broker's name is verified while its address is dialed |
| **deevnet-kit** | `pki=`; a request and install path; a CA backup; a constraint on its own CA; no address names under `deevnet` |
| **Ceremony tools** | The root signs a request; a Tenants profile; file names without a site |
| **Risk register** | Proposed rows: the online Tenants CA on a travelling kit; OpenBao's seal key with its data; tenant CAs lost with OpenBao until snapshots exist |

---

## Validation plan

Each test settles a line of one of the three records.

| # | Test | Settles |
|---|---|---|
| V1 | **On an ESP32**, mbedTLS accepts a tenant's Service CA, which is not self-signed, as its only anchor; refuses a CA with the same subject and another key; holds a two-CA bundle in its CA field; dials an address while verifying a name | ADR-0039 §5, ADR-0041 §2 |
| V2 | **Go and OpenSSL** refuse a tenant CA's certificate for a site's name, for another tenant's, and (under ADR-0040 B) for a name outside the subtree; refuse a URN under a URI constraint | ADR-0039 §4, §6; ADR-0040 |
| V3 | **OpenBao**: two issuers per tenant on one mount under a Tenants issuer; `sign-intermediate` writes the permitted and excluded names asked for; a policy that lets the API sign and nothing more; a snapshot restored to an empty instance keeps every issuer | ADR-0039 §2, §3 |
| V4 | **Disconnected provisioning**: the mobile site with no upstream creates a tenant, signs its CAs, issues a leaf and enrolls a device | ADR-0039 §1, §2 |
| V5 | **Relocation**: a tenant's devices move from the mobile site to a Pi and back; no CA, anchor or key changes; a device reaches the site's shared broker by SNI with a tenant-issued certificate | ADR-0039 §1, §5 |
| V6 | **Renewal**: a Pi under `deevnet` renews from a request carried on a USB stick; the same request without the tenant's token is refused | ADR-0039 §7, ADR-0041 §3 |
| V7 | **Trust transition**: a tenant moves from `deevnet` to `own` with its service up throughout, and the old anchor is removed last | ADR-0039 §8, ADR-0041 §6 |
| V8 | **Recovery**: a card under `own` is lost and restored from its backup with no device changing; OpenBao is rebuilt and the Tenants CA comes back from the vault | ADR-0039 §3, ADR-0041 §4 |
