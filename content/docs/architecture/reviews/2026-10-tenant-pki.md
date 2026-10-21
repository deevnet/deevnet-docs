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
| **Status** | Open. Two rounds on 2026-10-21: the first assessed ADR-0039's first draft; the second consolidated the owner's direction. All four records are Proposed. The [decision register](#decision-register) lists what awaits the owner |

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

| Area | ADR-0039 | ADR-0040 | ADR-0041 | ADR-0042 |
|---|---|---|---|---|
| **ADRs** | ADR-0031 §3, §5, §6; ADR-0037 §1, §3 | ADR-0004 §2; ADR-0008 note; ADR-0015 §13; ADR-0037 §3 | ADR-0030 §4 | ADR-0016 §1, §2, §3 |
| **Standards** | Certificates §1 (tiers; 1.3), §3.3, §4, §6 | Naming §5.1–§5.3 | — | Certificates §5 |
| **Records** | CHG-0034 re-planned; CHG-0047 probes expire | — | — | CHG-0036 narrowed; INC-0003 action 6 |
| **API** | tenant creation makes issuers; issuance per issuer; device URI; PKI-unavailable refusal | `Site.Zone`; reserved labels; vanity issuance | request/issue for Pi leaves | two OpenBao clients; session credential |
| **OpenBao** | Tenants and per-tenant issuers; policy | Names CA issuer and role | — | a new PKI store; Shamir seal; snapshots |
| **Ceremony tools** | root signs a request; Tenants profile; site-less file names | Names CA profile | — | — |
| **DNS** | — | `t.deevnet.net` tenant zones and vanity zones; resolver forwards | — | — |
| **Broker** | per-tenant listeners; binding check; SNI routing (PoC) | — | Pi's Mosquitto listener | — |
| **Service proxy** | a stream proxy for the broker (PoC) | — | — | — |
| **Proxmox** | — | — | — | one small VM |
| **Firmware (tenants')** | anchor = tenant Service CA; SNI | canonical broker name | address dialed, name verified | — |
| **deevnet-kit** | — | canonical names | `pki=`; request and install; CA backup; enrollment | — |
| **Risk register** | online Tenants CA | Names CA | — | platform seal key on the kit (accepted) |

---

## Migration plan

Each phase is its own change record, and none starts without the owner's approval. Nothing below is
built.

| Phase | Work | Done when | Rolls back by |
|---|---|---|---|
| **P0** | Back up the existing OpenBao: Raft snapshots copied off the kit; the Transit key into ansible-vault (CHG-0036) | a snapshot restored onto a fresh VM opens tenant secrets (V14) | nothing to undo |
| **P1** | Build the PKI store (ADR-0042): a new VM, Shamir seal, its own AppRoles and policies, snapshots | V12 and V13 pass with no CA in it yet | removing the VM |
| **P2** | Ceremony tools: the root signs a request; Tenants and Names profiles; site-less file names. Test on throwaway keys | V2 passes on certificates made by the tools | reverting the scripts |
| **P3** | The ceremony: the root signs the Tenants CA and the Names CA, from requests made in the PKI store | both installed; a restore of the PKI store keeps them (V12) | not reversible; a CA once signed stays valid |
| **P4** | Names: tenant zones under `t.deevnet.net`, vanity zones, reserved labels; old names kept as CNAMEs | V4 | removing the zones; old names untouched |
| **P5** | API: tenant CAs at creation, issuance on tenant issuers, vanity issuance, session credential, clean refusal | V3, V9, V10 | the API's previous release; issuers left unused |
| **P6** | Existing tenants (`eds`, `tdemo`, `mabell`, `cdeever`) get CAs by reconcile; their certificates reissued under the new names | each tenant serves certificates from its own Service CA | old certificates remain valid until expiry |
| **P7** | Broker proof of concept: SNI routing to per-tenant listeners, mTLS end to end, with an ESP32 (V5). Then, if chosen, per tenant | V5 | the proof of concept is separate from the live listener |
| **P8** | Devices move to their tenant's anchor, one tenant at a time: new anchor beside the root, then the root removed | each device connects with only its tenant anchor | the device's previous credentials |
| **P9** | Device certificates (CHG-0034 re-planned) on per-tenant Device CAs | V6 | passwords stay accepted throughout |
| **P10** | `deevnet-kit`: `pki=`, request and install, CA backup, enrollment | V7, V8, V11 | the previous image |
| **P11** | Retire the site-level tenant CAs once nothing they issued is in service | the mounts removed from the platform store | — |

---

## Validation plan

| # | Test | Accepted when |
|---|---|---|
| V1 | **ESP32 trust anchor.** A device holds only its tenant's Service CA (not self-signed); connects; also tested with a CA of the same subject and another key, with an anchor renewed on the same key with new dates, and with an address dialed while a name is verified | it connects to the genuine broker; it refuses the impostor; the renewed-anchor result is recorded; the dialed address and the verified name differ and the connection succeeds |
| V2 | **Name constraints.** Go and OpenSSL verify leaves under a Tenants CA permitting `t.deevnet.net`, and under a tenant Service CA permitting `eds.t.deevnet.net` | `t.deevnet.net`'s subdomains pass; `eds.deevnet.net`, `mobile.deevnet.net`, `x.t.deevnet.net.example` and another tenant's names fail; a URN under a URI constraint fails |
| V3 | **OpenBao issuers.** Two issuers per tenant on one mount under a Tenants issuer; `sign-intermediate` writes the constraints asked for; a policy that allows signing and nothing else | 100 tenants' issuers created and listed; the policy refuses key reads and role changes |
| V4 | **DNS.** The resolver forwards a tenant zone under `t.deevnet.net` and a vanity zone; the API refuses reserved labels | names resolve on the site; `t`, `home`, `mobile` and every alias label are refused |
| V5 | **Broker SNI proof of concept.** A stream proxy routes by SNI, without terminating TLS, to per-tenant VerneMQ listeners; an ESP32 with only its tenant anchor and a client certificate connects | mTLS completes end to end; a device of another tenant is refused at its listener; the broker sees the device's own certificate |
| V6 | **Device binding.** A device certificate from tenant A's Device CA naming tenant B in its URI; a deregistered device | both refused by the broker |
| V7 | **Renewal away from the factory.** A Pi under `deevnet` renews from a request carried on a USB stick | renewed with the token; the same request without the token is refused |
| V8 | **Graduation.** `deevnet` to `own` with the service up | no connection lost; the old anchor removed last |
| V9 | **Onboarding at a meetup.** The factory with no upstream: a session opened, a tenant created, its CAs signed, a leaf issued, a device enrolled. Then creation with the session closed, and a creation interrupted midway | all of it works offline; with the session closed, refusal before any change; the interrupted creation completes on retry with the same issuers |
| V10 | **Vanity names.** A browser opens `console.eds.deevnet.net`; tenant B asks for an `eds` vanity name; a wildcard is asked for | the vanity certificate is presented and trusted; both requests refused |
| V11 | **`own` recovery.** A card's CA backed up at first boot; the card destroyed; a new card restored | every device connects to the new card unchanged |
| V12 | **PKI store restore.** A snapshot restored on other hardware with the shares | issuers have the same keys and subject key identifiers; a new leaf chains as before; a pinned device accepts it |
| V13 | **Sealed PKI.** The PKI store sealed while the platform runs; a session credential past its expiry | devices, workloads and the API's other work continue; PKI operations refused cleanly; the expired credential refused |
| V14 | **Platform store restore, and the kit's custody.** A platform snapshot restored on a fresh VM; the kit inspected for unseal material | tenant secrets open; no PKI unseal share is found anywhere on the kit |

---

## Decision register

Every item is the owner's to approve. Leanings are the reviewer's.

| # | Decision | Options | Leaning | Record |
|---|---|---|---|---|
| D1 | Per-tenant CAs, or shared issuing CAs | A per-tenant / B shared / C offline | A | ADR-0039 §2 |
| D2 | How a shared broker serves a tenant's certificate | SNI routing to per-tenant listeners / Substrate CA in the device bundle | SNI routing, after V5 | ADR-0039 §6 |
| D3 | Standard 1.3 amended so devices anchor at their tenant's Service CA | yes / no | yes | ADR-0039 §5 |
| D4 | Vanity issuer | Names CA / public CA (DNS-01) / site ingress | Names CA | ADR-0040 §2 |
| D5 | Old site-scoped names kept as CNAMEs, and for how long | — | for one year of leaf lifetimes | ADR-0040 |
| D6 | Where the PKI store runs | new VM / container beside the platform store / dedicated hardware | new VM | ADR-0042 §2 |
| D7 | Unseal shares: how many, threshold, where kept | — | three, threshold two: password manager, offline signer media, a second off-kit place | ADR-0042 §3 |
| D8 | Where off-kit backups live | — | open | ADR-0042 §4 |
| D9 | PKI session length | — | a working day at most | ADR-0042 §3 |
| D10 | `own`: where the CA key lives | card + backup / owner-held root / card only | card + backup | ADR-0041 §4 |
| D11 | `deevnet`: a longer take-home leaf, or a key backup | — | open | ADR-0041 §3 |
| D12 | `bring`: issuing CA or leaves only | — | open | ADR-0041 §5 |
| D13 | Phase P0 (OpenBao backups) before anything else | yes / no | yes | Migration plan |

**Accepted principles** (the owner's, not up for decision here): identity outlives location; CA
custody is stable; key export between sites is rejected; canonical names under `t.deevnet.net`;
`pki=own` the generic default, with managed cards set deliberately; no offline ceremony per tenant.
