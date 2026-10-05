---
title: "ADR-0030: Site Certificate Hierarchy"
weight: -30
---

# ADR-0030: An Offline Site Root, an OpenBao Intermediate, and Certificates Laid Down by the Build

|  |  |
|--|--|
| **Status** | Proposed; **§1–§4 superseded by [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)** (an offline Deevnet root and Site CAs; the substrate issued by Ansible, not OpenBao). §5–§8 stand. |
| **Date** | 2026-10-02 |
| **Scope** | Where the site's root of trust lives, what issues TLS certificates, how long they last, how a build or repave puts certificates and trust on substrate hosts, appliances, images and the operator's computer, and how tenants keep trusting it. Not automatic renewal, not expiry alerting, not client certificates. |
| **Extends** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) §3 (the `pki/` row) and §6 (rebuild order); answers its open question 1 |
| **Related** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/), [CHG-0030](/docs/changes/2026/0030-state-store-tls/), [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) |

---

## Context

OpenBao's `pki/` mount is the site's certificate authority (ADR-0016 §3). It holds a self-generated
root, `CN=Deevnet mobile internal CA`, valid ten years, and one role, `platform`, that issues 90-day
leaves. Ansible issues six of them as it builds each service: the Deevnet API, the state store, the
broker, the log store's proxy, Grafana and tenant downloads. Tenants, the provider and the scripts that
check the site trust that root as `site-ca.pem`, passed to each tool by file.

Four things are not covered:

- **The root lives where it can be lost.** It was generated inside OpenBao and never left it. When
  OpenBao was rebuilt without its data (INC-0003), the new instance generated a new root under the
  same name, and every tenant, script and host had to be handed the new CA by hand. ADR-0016 left
  this as open question 1: should `pki/` be the root, or an intermediate under a root kept offline?
- **The substrate's own interfaces are untrusted.** Proxmox, the core router and the Omada controller
  serve the certificates their installers generated. The Deevnet API, Packer, the tenant fabric's
  Terraform and the Ansible roles that reach them skip verification, and the operator's browser
  shows a warning for each.
- **Nothing trusts the CA at the operating-system level.** No substrate host, the Builder, the
  operator's computer or the VM template has it in its trust store, so every client needs a CA flag.
- **Renewal happens only when a role is re-run.** A 90-day leaf on a service nobody re-applies expires
  without notice, and nothing watches.

The TLS Cert Automation roadmap planned step-ca on the Builder. ADR-0016 replaced that with OpenBao,
and this record finishes the job that roadmap described.

## Decision

### 1. A root per site, kept offline in ansible-vault

- **Generated once, on the control node,** by a playbook that refuses to run if the site already has a
  root. `CN=Deevnet <site> root CA`, valid twenty years.
- **The private key lives only in the inventory vault** (`vault_site_root_ca_key`), the store that
  already holds OpenBao's seal key (ADR-0016 §2). It is encrypted, committed and pushed before anything
  is signed with it.
- **The certificate is public** and lives in plain inventory (`site_root_ca_cert`).
- **It signs intermediates and nothing else.** It is never loaded into OpenBao and never signs a leaf.

### 2. OpenBao holds an intermediate, and issues from it

- **The intermediate's key is generated inside OpenBao** (`pki/intermediate/generate/internal`) and
  never leaves it. Ansible signs the request with the root on the control node and installs the result
  (`pki/intermediate/set-signed`). Valid five years.
- **Everything that issues today keeps issuing from it:** the `platform` role for substrate services,
  and the API's grant for tenant issuance.
- **A rebuild costs an intermediate, not a root.** An OpenBao that comes back without its data gets a
  new intermediate under the same root. Certificates the old one signed still chain to the root
  and stay in service until they are due; new ones come from the new intermediate. No client is
  handed anything. The `openbao` role signs a new intermediate when OpenBao has none, or when the one
  it has does not chain to the inventory root.

### 3. What comes before OpenBao is signed by a bootstrap intermediate

The core router and the hypervisors come up before OpenBao does, and OpenBao's VM is built through
them (ADR-0016 §6). A certificate they could only get from OpenBao would make a from-scratch rebuild
wait on itself, so they don't get one from it.

- **A second intermediate, the bootstrap intermediate, sits under the same root.** Its key lives in the
  inventory vault beside the root's (`vault_site_bootstrap_ca_key`), and its certificate in plain
  inventory. Valid five years.
- **Ansible signs with it on the control node**, with no OpenBao involved, for everything that comes
  before OpenBao in the rebuild order: the core router and the Proxmox hypervisors.
- **It is installed without needing what it replaces.** Proxmox takes its certificate over SSH. The
  core router's install step trusts the router's own certificate on first use, then verifies from then
  on.
- **Everything after OpenBao in the rebuild order issues from OpenBao**, the Omada controller included:
  OpenBao does not need the controller to come up.

### 4. The root is the only trust anchor

- **The root's file is `deevnet-<site>-root-ca.pem`** (`deevnet-mobile-root-ca.pem` here), on hosts,
  in trust stores, in tenant repositories and on the downloads server. It replaces `site-ca.pem` and the
  `deevnet-mobile-ca.pem` download. Admission still prints its fingerprint.
- **Applications read the CA from a variable, not a fixed file name** (`MQTT_CA_FILE`,
  `GRAFANA_CA_CERT`, `DEEVNET_API_CACERT`). At Deevnet it names the root. On a take-home Pi it names
  the Pi's own CA, which deevnet-kit writes as `deevnet-kit-ca.pem`, so an application moves between
  the two without a change.
- **Services serve their full chain:** leaf, then intermediate.
- **"Has the CA changed" means "does this leaf still chain to the root".** Roles verify the leaf
  against the root with the intermediate as an untrusted link, instead of comparing the host's CA file
  with `pki/cert/ca`. An intermediate rotation fails that check and reissues; a root rotation is a
  deliberate act, not a side effect of a rebuild.

### 5. Leaves last a year

- **One year, reissued by any run that finds fewer than 60 days left.** No timer renews certificates
  (§6), so the lifetime has to outlast the gaps between deliberate runs.
- **Names:** the CN is the name clients dial (`<service>.<site>.deevnet.net`), with the host's FQDN and
  address as SANs. `127.0.0.1` is added only where the role's own health check dials it.
- **To confirm when building:** that macOS accepts a one-year leaf under a user-trusted root. Apple
  caps TLS server certificates at 825 days; whether that cap or the 398-day one for public roots
  applies to a user-installed root is to be read from Apple's current guidance, not assumed.

### 6. Certificates are laid down by the build, not by a clock

- **The roles that build a host issue its certificates and install its trust.** A new build or a
  repave comes up with the right certificate and the right root, with no extra step.
- **One playbook, `certs.yml`, runs every certificate and trust task across the site.** It is how the
  operator renews: re-run it.
- **No automatic renewal in this version.** An expiring leaf is a known risk, held in the risk register
  and narrowed by the one-year lifetime, not a gap.

### 7. Trust is installed where the tools run

| Where | How |
|---|---|
| Every substrate host and domain VM | the build installs the root into the OS trust store (`update-ca-trust` on Fedora, `update-ca-certificates` on Proxmox) |
| The Builder | the same, so Ansible, Packer and Terraform verify without flags |
| The VM template | the image factory bakes the root in, so a fresh VM trusts it before Ansible reaches it |
| The operator's computer | a documented manual step, trusting the root in the system keychain |
| Tenants | unchanged: the downloads URL and the fingerprint at admission, passed to each tool by file |

Tools that already pass the CA by file keep doing so. The trust store is what lets the rest stop
skipping verification.

### 8. The appliances get site certificates

- **Proxmox and the core router** are issued leaves from the bootstrap intermediate (§3), and **the
  Omada controller** from OpenBao's. Each has its leaf installed through each product's own documented mechanism, chosen and quoted when the
  change is built. Where a product offers no API for it, the runbook carries the manual step.
- **Once an appliance serves a site certificate, every client that skips verification to reach it
  stops.** The Deevnet API's `*_INSECURE_TLS` settings default to off.

---

## Consequences

**An OpenBao rebuild no longer re-roots the site.** INC-0003's cost, handing a new CA to every tenant
and script, becomes a reissue on the next run.

**One last re-root.** Moving to this hierarchy changes the trust anchor once:
- every tenant replaces `site-ca.pem` with `deevnet-mobile-root-ca.pem` (eds, tdemo, mabell, cdeever);
- the copies embedded in `install-provider.sh`, `tenant-check.sh` and `segment-check.sh` are updated.

No device firmware embeds the CA today, so nothing is reflashed; builds from here on carry the root.

**The root's custody is ansible-vault's, and so is the bootstrap intermediate's.** Anyone with the
vault password can sign an intermediate, or a router or hypervisor certificate, that the whole site
trusts. It joins the seal key in the category ADR-0016 already gave the same care as the
vault password.

**The substrate's interfaces verify.** The browser warnings, and the `-k`, `insecure` and
`validate_certs: false` settings that answer them, go away.

**Renewal is a person running a playbook.** Until it is automated, a certificate on a host nobody
re-applies for ten months will expire.

---

## Alternatives considered

- **Keep the root in OpenBao, and rely on snapshots.** No re-root now, but a rebuild without a snapshot
  re-roots everything again, and ADR-0016 §6 still lists snapshot restore as unconfirmed. Rejected.
- **One Deevnet root for every site, with a CA per site under it.** One anchor for an operator or a
  tenant who works at more than one site, and the conventional shape. Rejected for now: there is one
  site, sites are standalone instances, and the mobile kit travels, so its vault is the likelier to be
  lost, and a per-site root keeps that loss to one site. Open question 4 keeps the way there open.
- **Put the root in ansible-vault and load it into OpenBao.** One fewer level, but the root's key would
  then live in two places, one of them online. Rejected.
- **An intermediate generated outside OpenBao and imported.** A rebuild could restore the very same
  intermediate, but its key would sit in ansible-vault beside the root and gain nothing over §2's
  reissue. Rejected.
- **The root signs the core router's and the hypervisors' leaves directly.** One fewer key, but the
  root would be used on every repave of them. Rejected for §3's bootstrap intermediate.
- **OpenBao issues the core router's and the hypervisors' certificates, and a from-scratch rebuild
  skips verification until it is up.** No new key, but skipping verification stays in the bootstrap
  path, which is where a spoofed endpoint matters most. Rejected.
- **Renew on a timer now** (a scheduled play, an OpenBao Agent per host, or ACME from OpenBao's PKI).
  Each is a real design, with a dependency on the control node, a credential on every host, or
  challenge plumbing. Deferred, not rejected: see open question 1.

---

## Open questions

1. **Automatic renewal.** A scheduled `certs.yml` from the control node, an agent on each host, or ACME
   from OpenBao (which would also serve Proxmox and the core router through their own ACME clients).
2. **Expiry monitoring.** Folded into ADR-0023's metrics and alerting, probing every endpoint including
   the appliances and the take-home Pi.
3. **The remaining untrusted endpoints.** OpenBao's own listener (self-signed, pinned by every role),
   PowerDNS's HTTP API and the Builder's artifact server. The offline root lets Ansible sign OpenBao's
   listener directly, which removes the reason it was left self-signed.
4. **An organization root, if a second site is built.** An offline `Deevnet root CA` can cross-sign
   each site root, so that one anchor trusts every site while everything that trusts a site root
   keeps working, with no re-root.
