---
title: "2026-10 Tenant PKI"
weight: -20261021
---

# Review: Tenant PKI, October 2026

| | |
|---|---|
| **Date** | 2026-10-21 |
| **Scope** | The tenant PKI direction (ADR-0039, 0040, 0041, 0042) against the PKI, OpenBao, the API, the broker, the ceremony tools, `deevnet-kit` and the records they touch |
| **Criteria** | The owner's principles for the mobile site as a tenant factory: identity outlives location; the factory is autonomous; CA custody is stable; certificates travel, authorities remain; runtime does not need PKI availability; PKI availability is deliberate; onboarding is self-service within a PKI session; human-facing names are friendly; boundaries are enforceable; independence is a choice; trust transitions are explicit; recovery is tested; architecture matches operational reality |
| **Method** | A read of ADR-0012, 0016, 0031, 0037, the Certificates and Naming standards, `deevnet.mgmt` (OpenBao, VerneMQ, the service proxy, `scripts/pki/`), `deevnet-provisioning-api` (issuance, admission, the OpenBao client, `deevnet-kit`) and the inventory, at their GitHub heads on 2026-10-21. Findings come from reading code and records, not running them; the [validation plan](#validation-plan) is what would run them |
| **Status** | Owner's responses complete (round 3, 2026-10-25). Rounds 1 and 2 (2026-10-21) assessed the drafts and consolidated the owner's first direction; round 3 records the owner's decisions, which redirected all four records. All four are Proposed, as rewritten. Nothing is open: revocation is an accepted risk, and a tenant at another site is a Deevnet Pi |

---

## Round 3: the owner's decisions

**The owner's decisions on 2026-10-25 return the design to ADR-0031's hierarchy, and every item in the
[decision register](#decision-register) is now answered.** The records were rewritten to match. The
[Summary](#summary) through [What uses OpenBao](#what-uses-openbao) record rounds 1 and 2 as they
stood; the dependency matrix, the migration and validation plans and the register below are round
3's.

**The model, in one picture:**

```
Deevnet Root CA                     offline · the one anchor for people, computers and devices
├── Deevnet Mobile Site CA          offline · the Mobile Factory
│   ├── Deevnet Mobile Substrate CA     the factory's own infrastructure      key: vault, used by Ansible
│   ├── Deevnet Tenant Service CA       tenant servers, at every site         key: vault → imported into OpenBao
│   └── Deevnet Tenant Device CA        tenant devices, at every site         key: vault → imported into OpenBao
└── Deevnet <Site> Site CA          offline · any other site
    └── Deevnet <Site> Substrate CA     that site's own infrastructure        key: that site's vault, used by Ansible
```

**What the owner decided:**
- **Only the Mobile Factory creates tenants.** It is a contractor site: it goes to the devices, or
  devices are brought to it, for creation, renewal and development. Its long form is the Deevnet
  IoTaaS Mobile Development Factory.
- **Identity outlives location by names, not by CAs.** The owner first set the principle aside: being
  in development on the kit is part of a deployment's identity. The design that followed keeps
  identity site-less anyway. A service's identity is its site-less name, and a device's is its URI.
  A site appears only as an extra SAN on a service's certificate and as a device's registration,
  its visa. A move to a site already in the SANs needs no new certificate.
- **A site has only its substrate's CAs**; the Mobile Factory's existing tenant CAs serve every site;
  devices trust the Deevnet Root (ADR-0039).
- **A tenant service is named without a site**, `<service>.<tenant>.deevnet.net`, in its CN and first
  SAN; its sites are extra SANs; devices dial the site-less names (ADR-0040).
- **A take-home Pi is a Deevnet Pi by default**; a `non-deevnet` card carries a starter kit, built
  from the ceremony tools, for a two-tier PKI of the owner's own (ADR-0041).
- **One OpenBao, sealed by Shamir shares**, three with a threshold of two and one held in the vault,
  opened for a work session and rebuilt from the vault, with no snapshots (ADR-0042).

**What the round found in the rewritten design, now requirements in the records:**

| | Finding | Where it is required |
|---|---|---|
| R3-1 | **The API treats a sealed OpenBao as a lost secret.** A stored secret that will not open is marked unreadable, or emptied and re-minted (`deevnet-provisioning-api` `internal/store/store.go`). Under a seal that is routine, that would damage tenants | ADR-0042 §3: refuse before changing anything; built before the seal changes |
| R3-2 | **A stolen Tenant Device CA key could impersonate any registered device**, because authorization is by URI | ADR-0039 §5: the broker checks the key against a fingerprint recorded at issuance |
| R3-3 | **The vault password guards every key OpenBao uses**, and git history keeps old ciphertext | ADR-0042 §5: a vault password exposed means replacing the keys, not only the password |
| R3-4 | **The secret store's signing role cannot tell a site-less tenant name from a site's substrate name** by label count | ADR-0040 §3; its open question |
| R3-5 | **A certificate carrying the bus name could answer for every site's broker** | ADR-0040 §5: only a site broker's certificate carries it |
| R3-6 | **A device CN under the tenant's name could collide with a service name** | ADR-0039 §4, ADR-0040 §4: devices under a reserved `device` label |
| R3-7 | **Revocation is still absent.** A stolen issuing CA key can make server certificates that root-anchored devices accept until the CA expires | Accepted by the owner, 2026-10-25: [risk R-14](/docs/policies/risk-management/risk-register/) |
| R3-8 | **Another site cannot host a tenant yet**: it has no device registry and no tenant DNS | Resolved, 2026-10-25: at another site a tenant is a Deevnet Pi, its devices' broker and registry; the site gives it a network and DNS from its inventory (ADR-0039 §8) |

---

## Summary

**The direction holds, with one premise corrected.** A Tenants CA beside the Site CAs fits the root's
`pathlen:2`. Per-tenant CAs give pinned devices a boundary they enforce. A tenant subtree gives the
Tenants CA a bound that does not age. Keeping CA keys sealed except in sessions removes the largest
risk of the first draft. **The premise corrected: there is no runtime OpenBao.** Nothing a deployed
tenant runs on uses OpenBao today. The second store is the platform's provisioning store, and the
split is still worth having, for the reasons in ADR-0042.

**Three things are not settled by reading and need proofs of concept**: whether devices can keep one
anchor across sites through SNI routing (ADR-0039 §6); what mbedTLS does with a non-self-signed,
renewed anchor; and whether a restored PKI store keeps its issuers' identities.

**Two things must come before any new CA exists**: backups of OpenBao that have been restored, and
the PKI store's manual seal.

---

## Assessment

### What is sound

- **The hierarchy fits as built.** Root `pathlen:2` → Tenants CA `pathlen:1` → tenant CAs
  `pathlen:0` → leaves. The Names CA is a `pathlen:0` sibling. No re-root.
- **Per-tenant CAs give an enforceable device boundary**, qualified: a pinned device refuses a CA made
  with another key, including one made with a stolen Tenants CA. Relying parties that anchor at the
  root (browsers, computers, tools) are not protected by it (ADR-0039 §4).
- **A request does not authorize.** The API admits only the operator or the tenant's own token
  (`ownTenant`), and reads a request for its public key alone (ADR-0037 §2).
- **A tenant subtree bounds the Tenants CA durably**; exclusions could not.
- **Runtime already survives a sealed OpenBao.** The broker authenticates from its own database, and
  ADR-0012 says an API outage stops provisioning, never devices. The code confirms it.
- **VerneMQ can run a listener per tenant**, each with its own certificate and CA file (2.2.0's
  `listener.ssl.<name>`).

### Findings from the first round, and where each stands

| | Finding | Now |
|---|---|---|
| F1 | Moving CA keys between sites changes custody with every move | Rejected (ADR-0039 §1) |
| F2 | The online Tenants CA would sit on a kit that unseals itself, with no backup | Addressed: a separate PKI store, sealed by Shamir, backed up and restore-tested (ADR-0042) |
| F3 | Custody rules disagree: standard §5.2, CHG-0036, the draft | Resolved: PKI keys are generated in the PKI store and recovered from snapshots; CHG-0036's vault rule is kept for the platform store only (ADR-0042 §4) |
| F4 | The ceremony tools have no path for the root to sign a request | Still true: an implementation change (migration P2) |
| F5 | "The API has one path" was wrong | Corrected (ADR-0039 Consequences) |
| F6 | "No operator" was wrong: admission is the operator's | Corrected, and onboarding's five steps separated (ADR-0039 §9) |
| F7 | Exclusions are fixed at signing | Resolved by the subtree (ADR-0040 §1) |
| F8 | A URN cannot be name-constrained | Stated; tenant binding is the broker's (ADR-0039 §5) |
| F9 | Standard 1.3 allows only the root as an anchor | To be amended, for devices only (ADR-0039 §5) |
| F10 | A shared broker presents a site certificate | Unresolved: SNI routing to per-tenant listeners, pending a proof of concept (ADR-0039 §6) |
| F11 | `deevnet-kit` puts addresses and `localhost` in its certificate | Resolved for `deevnet`: devices verify a canonical name; Pi services dial canonical names (ADR-0041 §2) |
| F12 | Tenant names are checked for shape only | Reserved labels, now including `t` (ADR-0040 §3) |
| F13 | The Mobile Tenant Service CA has issued probe certificates too | Recorded (ADR-0039 §11) |

---

## Conflict analysis

**"Runtime operation does not require PKI availability" was already true.** It does not motivate a
"runtime" store; it describes the system as it is. What a second store buys is different: the API
starts and provisions unattended while CA keys stay sealed. The owner's description of the runtime
store as holding broker credentials and service-to-service secrets does not match the code.
Broker passwords are bcrypt hashes in the broker's own database, and no service reads OpenBao.

**"Self-service onboarding" against "PKI availability is deliberate."** They meet in the PKI session:
self-service holds within a session the operator opens, and a tenant created outside one is refused
cleanly. At a meetup the operator is present anyway.

**"The factory is autonomous" against "recovery must be tested off the kit."** Backups have to live
somewhere other than the kit. A copy at the home site is a backup, not a dependency, provided the
factory never needs it to operate. ADR-0042 leaves the place open.

**"Certificates travel" against "the substrate holds no tenant key"** (ADR-0037 §6 in the other
direction). Under SNI routing, a site's broker holds a key for a tenant's canonical broker name,
issued by the tenant's Service CA. It is the site's key, for the tenant's name, and is recorded as a
consequence rather than hidden.

**"Human-facing names are friendly" against "one authority per namespace."** Vanity names need an
issuer outside the tenant subtree. The Names CA (ADR-0040 option A) is another online issuer, broad in
scope, whose control is the API's ownership rule. That is the same position the Tenant Service CA is
in today.

**"Trust transitions are explicit" against firmware reality.** A device must take a new anchor at
graduation, and perhaps when its tenant CA is renewed. Many devices, EdS's included, take an anchor
only by cable. The PKI can require the transition; the application decides its cost (ADR-0011).

**Revocation is still absent.** Leaves last a year. A stolen server key is good until it expires. A
stolen device key is refused only by deregistering the device. A stolen CA key is good until the CA
expires. Nothing in these records changes that; ADR-0031's open question remains the most important
one.

---

## What uses OpenBao

| Consumer | Mount and path | Purpose | When |
|---|---|---|---|
| Deevnet API | `deevnet-api/data/backends` | credentials for PowerDNS, OPNsense, MinIO, Proxmox, Omada, the broker and log writers, Grafana; the tenant-token HMAC key | at start. A failure exits the process, and systemd retries every 10 s |
| Deevnet API | `transit/decrypt/tenant-secrets` | opening tenant secrets | per request (every tenant-token authentication); fails soft to an empty value |
| Deevnet API | `transit/encrypt/tenant-secrets` | sealing tenant secrets | per request (create, reconcile, Wi-Fi keys, admissions); fails hard |
| Deevnet API | `sys/wrapping/wrap`, `unwrap` | enrollment tokens | admission; first creation |
| Deevnet API | `pki-tenant-service/sign/tenant-service` | tenant server certificates | per request |
| Ansible | `sys/*`, policies, AppRoles, KV, Transit keys, `pki-*` | configuration | deploy time |
| `pve-creds` (Packer, tenant fabric) | `image-factory/data/proxmox/<node>` | Proxmox tokens | build time, with an inventory fallback |
| VerneMQ, writers, log bridge, VictoriaLogs, Grafana, MinIO, PowerDNS, Omada, tenant workloads, the provider | — | — | never |

**OpenBao shares the identity VM with PowerDNS**, has its Raft data on the OS disk, no audit device
and no snapshot, and three AppRoles with no secret-ID TTL or address binding.

---


## Dependency matrix

**What each record touches, as rewritten in round 3:**

| Area | ADR-0039 | ADR-0040 | ADR-0041 | ADR-0042 |
|---|---|---|---|---|
| **ADRs** | ADR-0031 §3, §5; ADR-0037 §1, §6 | ADR-0004 §2; ADR-0015 §13; ADR-0037 §3 | ADR-0030 §4 | ADR-0016 §2, §6; resolves its conflict with ADR-0033 |
| **Standards** | Certificates §1 tables | Naming §5.1–§5.3; §4.3 gains the bus name | — | Certificates §5 |
| **Records** | CHG-0034 re-planned | — | — | CHG-0036 extended |
| **API** | device URI and CN without a site; key fingerprint at issuance | site-less CN and site SANs; reserved labels; the tenant's sites | request and install for Pi certificates | sealed means unavailable (R3-1) |
| **OpenBao** | — | the signing role's guard (R3-4) | — | Shamir seal; Transit and tenant CA keys imported from the vault |
| **Ceremony tools** | another site's Site and Substrate CAs (exist: paths 2 and 3); the tenant CAs re-keyed (path 3) | — | parameters for the owner's names; a leaf step | — |
| **DNS** | — | `<tenant>.deevnet.net` zones; `mqtt.deevnet.net` per site | — | — |
| **Broker** | registration and key fingerprint checks | the bus name as a SAN | — | — |
| **Firmware (tenants')** | trust the Deevnet Root | dial site-less names | dial an address, verify a name | — |
| **deevnet-kit** | — | site-less names | `deevnet` / `non-deevnet`; request and install; `pki init` | — |
| **Risk register** | tenant CAs serve every site; no revocation | — | — | the vault as the one custody |

---

## Migration plan

**Each phase has a change record, Planned, and none starts without the owner's approval.** P3 and
P4 share one. Nothing below is built.

| Phase | Work | Done when | Rolls back by |
|---|---|---|---|
| **P0** ([CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/)) | The API treats a sealed OpenBao as unavailable: it refuses tenant work before changing anything, and never marks, empties or re-mints a secret for it (R3-1) | V13's API half passes against a sealed test store | the API's previous release |
| **P1** ([CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)) | CHG-0036, extended: a new Transit key from the vault, stored tenant secrets resealed under it; both tenant CAs re-keyed outside OpenBao, signed by the Mobile Site CA, held in the vault and imported; the lock-in stop | V3 and V12 pass | the old Transit key and CAs stay until the reseal is verified |
| **P2** ([CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/)) | The Shamir seal (ADR-0042): three shares, threshold two, one in the vault; every pair proven; Ansible's OpenBao plays stop plainly when sealed | V13 and V14 pass | the static seal, from the vault |
| **P3** ([CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/)) | Names: `<tenant>.deevnet.net` zones, the reserved labels (`device` and the bus name among them), `mqtt.deevnet.net` on each broker's certificate, the signing role's guard | V4 passes | removing the zones; site names untouched |
| **P4** ([CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/)) | Issuance: site-less CN and site SANs. A device's site-less URI and CN, and its key fingerprint, are issued with P6, where device certificates are first signed | V2 and V10 pass | the API's previous release |
| **P5** ([CHG-0055](/docs/changes/2026/0055-reissue-tenants-site-less/)) | Existing tenants (`eds`, `tdemo`, `mabell`, `cdeever`) reissued with site-less names | each serves its site-less name | the site-named certificates stay valid |
| **P6** ([CHG-0034](/docs/changes/2026/0034-device-certificates/)) | Device certificates (CHG-0034 re-planned) with the broker's registration and fingerprint checks | V1 and V6 pass | passwords stay accepted throughout |
| **P7** ([CHG-0056](/docs/changes/2026/0056-kit-deevnet-or-own-pki/)) | `deevnet-kit` and the ceremony tools: `deevnet` / `non-deevnet`, request and install, `pki init` | V7, V8 and V11 pass | the previous image |
| **P8** ([CHG-0057](/docs/changes/2026/0057-build-the-home-site/)) | The home site ([roadmap](/docs/roadmap/infrastructure/home-site/)): its Site CA and Substrate CA, its inventory and network, DNS and DHCP on its router, DNS for the Pis it hosts, deployed from the Builder | a Deevnet Pi served at home, its devices connecting | — |

**P0 comes before P2.** Sealing OpenBao before the API can tell a sealed store from a lost secret
would damage tenants.

---

## Validation plan

**Each test has an acceptance criterion, and the records cite them by number.** V5 and V9 of round
2 are withdrawn with what they tested.

| # | Test | Accepted when |
|---|---|---|
| V1 | **ESP32 trust.** A device holding only the Deevnet Root dials a site broker's address and verifies `mqtt.deevnet.net`; then a Deevnet Pi's address, verifying the Pi's name; then a broker with a certificate from a CA outside Deevnet | it connects to both genuine ones and refuses the outsider |
| V2 | **One CA for every site.** Go, OpenSSL, a browser and an ESP32 verify a Tenant Service CA certificate for `console.eds.deevnet.net` and `console.eds.home.deevnet.net` | all accept both names; a name outside `deevnet.net` fails under Go, OpenSSL and the browser |
| V3 | **Imported keys.** The Transit key and both tenant CA keys made outside OpenBao and imported | each issuer has the expected subject key identifier; a sealed tenant secret opens; a certificate chains to the root |
| V4 | **DNS.** A production site answers `<tenant>.deevnet.net` for what it hosts, and the Mobile Factory does not (D17); each site answers `mqtt.deevnet.net` with its own broker; the API refuses reserved labels | names resolve where D17 says; `home`, `mobile`, `device`, `mqtt` and every global alias are refused as tenant names |
| V5 | *Withdrawn: SNI routing to per-tenant listeners* | — |
| V6 | **Device admission.** A certificate for a registered device's URI with another key; a device not registered at this site; a deregistered device | all three refused by the broker; the genuine device connects |
| V7 | **Renewal away from the Mobile Factory.** A Deevnet Pi renews from a request carried on a USB stick | renewed with the token; the same request without it refused |
| V8 | **Leaving Deevnet.** A Deevnet Pi moves to its owner's PKI with the service up | no connection lost; the Deevnet Root removed last |
| V9 | *Withdrawn: onboarding with a separate PKI store* | — |
| V10 | **Names in a certificate.** A browser opens `console.eds.deevnet.net` and `console.eds.mobile.deevnet.net`; tenant B asks for an `eds` name; a wildcard, the bus name and a `device` label are asked for | both open with one certificate; every request refused |
| V11 | **The starter kit.** `pki init` on a `non-deevnet` card; the card destroyed; a new card given a new issuing CA from the stick | every device connects to the new card unchanged |
| V12 | **Rebuild from the vault.** OpenBao destroyed and rebuilt, nothing restored | tenant secrets open; issuers keep their subject key identifiers; a new certificate chains as before |
| V13 | **Sealed.** OpenBao sealed while the API, the broker and devices run; a tenant request; an Ansible OpenBao play | devices and workloads continue; the request is refused with no secret marked, emptied or re-minted; the play stops with a plain error |
| V14 | **Shares and custody.** Each pair of shares unseals; the kit is inspected | every pair works; no unseal share or seal key is found on the kit |

---

## Decision register

**Every item is answered**, by the owner, on 2026-10-25.

| # | Decision | Answer | Record |
|---|---|---|---|
| D1 | Per-tenant CAs, or shared issuing CAs | **Shared: the Mobile Factory's existing Tenant Service and Device CAs, for every site.** Per-tenant CAs withdrawn | ADR-0039 §2 |
| D2 | How a shared broker serves a tenant's certificate | **It does not.** The broker is the platform's, with its site's certificate and the bus name. SNI routing, a Substrate CA in each bundle and a Bus CA all rejected | ADR-0039, ADR-0040 §5 |
| D3 | Standard 1.3 amended so devices anchor at their tenant's Service CA | **No.** Devices trust the Deevnet Root, like every client | ADR-0039 §3 |
| D4 | Vanity issuer | **The Tenant Service CA.** The site-less name is the service's identity, not a vanity | ADR-0040 §1, §3 |
| D5 | Old site-scoped names kept as CNAMEs | **Not needed.** Site names stay, as SANs | ADR-0040 §2 |
| D6 | Where the PKI store runs | **No separate store.** One OpenBao, sealed | ADR-0042 §1 |
| D7 | Unseal shares | **Three, threshold two; one in the vault**; the others apart and encrypted; no machine holds the vault password and another share | ADR-0042 §1 |
| D8 | Where off-kit backups live | **None.** OpenBao is rebuilt from the vault | ADR-0042 §4 |
| D9 | Session length | **A work session**: opened at a visit's start, sealed at its end | ADR-0042 §2 |
| D10 | `own`: where the CA key lives | **Withdrawn with the mode.** The starter kit puts the owner's root on a USB stick, an issuing CA on the Pi | ADR-0041 §3 |
| D11 | `deevnet`: longer leaf or key backup | **Neither.** A one-year certificate, renewed at a visit | ADR-0041 §2 |
| D12 | `bring` | **Withdrawn** | ADR-0041 |
| D13 | Backups before anything else | **Replaced**: the API's sealed handling (P0), then CHG-0036 (P1) | Migration plan |
| D14 | Does another site create tenants? | **No.** Only the Mobile Factory | ADR-0039 |
| D15 | Revocation | **Accepted risk**, no lifetime changes | R-14 |
| D16 | What a tenant is at another site | **A Deevnet Pi**: its devices' broker and registry. The site gives a network and DNS from its inventory, deployed from the Builder; no self-service | ADR-0039 §8 |
| D17 | Where site-less names resolve | **At production sites only** (2026-10-26). The Mobile Factory names a tenant only under its site zone; certificates carry both. CHG-0054's step 2 is dropped | ADR-0040 §1 |

**Principles, as round 3 leaves them** (the owner's): the Mobile Factory alone creates tenants and is
autonomous, and builds sites as well as tenants; certificates travel, authorities stay; key export between sites is rejected; identity
outlives location by site-less names, with a site only a SAN or a registration; a take-home Pi is a
Deevnet Pi by default; recovery is a rebuild from code and the vault. *"`pki=own` the generic
default"* is withdrawn.
