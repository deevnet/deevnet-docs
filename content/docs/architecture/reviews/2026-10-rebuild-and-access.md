---
title: "2026-10 Rebuild and Access"
weight: -202610
---

# Review: Rebuild and Access, October 2026

| | |
|---|---|
| **Date** | 2026-10-06 |
| **Scope** | The Mobile Factory: substrate, tenants, and the accounts that build and run them |
| **Criteria** | Every part rebuilds cleanly from code; no rebuild depends on what it is rebuilding; infrastructure and configuration are code; accounts and access are practical and least-privilege |
| **Method** | A read of the inventory, the Ansible collections, the image factories, the Deevnet API and provider, the reference tenant, and every ADR, runbook and record. Findings cite the files they come from. Where a finding comes from reading code rather than running it, it says so. |
| **Status** | Open. Nothing here is decided; each finding acted on becomes an ADR or a change record |

---

## Summary

**The substrate has no hard rebuild cycle.** Every loop that looks circular, such as building a VM
template with a token from OpenBao, which runs in a VM built from that template, falls back to
ansible-vault. Certificates no longer depend on OpenBao at all ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)).

**Three things stand between the site and a clean rebuild of any part of it:**
- **Data that can't be re-derived sits inside runtime services.** The Tenant Device CA's key exists
  only inside OpenBao, with no snapshot. The tenant registry and the tenants' state share one VM's OS
  disk.
- **A tenant can't heal itself after a backend is rebuilt.** A reconcile re-ensures six things; a
  tenant's workloads, DNS records, Wi-Fi keys and broker accounts are not among them, and a plain
  apply sees no change.
- **The Builder is a single point for both recovery and access.** Losing it without warning has no
  documented path, and an operator session on it reaches every secret on the site.

**Accounts are mostly well-placed, but broad.** Most credentials have one clear authoritative copy
and a rebuild path. Several are wider than their job, a few are shared between consumers, and
rotation is written down for only a handful.

**Tenant secrets are an open design question, not a defect.** The review lays out what exists and
the criteria for deciding ([S1](#s1-tenant-secrets)), without deciding.

---

## Current state

### Rebuild tiers

**The site rebuilds in four tiers, each from the one below it.** The tiers aren't named anywhere in
the docs today; this review names them to make the dependency rule testable.

| Tier | What | Built from | Holds anything that can't be re-derived? |
|---|---|---|---|
| **T0: the manual floor** | The offline Root and Site CAs; the vault password; the Proxmox and OPNsense installs from ISO and USB; the OPNsense API key; the Omada setup wizard, Owner and Open API clients; the hand-issued Proxmox tokens | People, by procedure | Yes, by design. That is what the floor is |
| **T1: the substrate** | The Builder, the core router's configuration, the switch and AP, both hypervisors, the VM templates, every management VM, the tenant fabric | Inventory and ansible-vault, through Ansible, Packer and Terraform | No, with two exceptions: the Builder's own local state ([R3](#r3-losing-the-builder)) and the fabric's state, which is committed to git |
| **T2: runtime services** | OpenBao, the Deevnet API and its database, PowerDNS, the state store, the broker, the log store, Grafana, the Omada controller | T1, seeded from ansible-vault | **Yes**: the Tenant Device CA key ([R1](#r1-tenant-device-ca-key)), the registry and the tenants' state ([R2](#r2-registry-and-state-on-one-vm)), the controller's keys ([R7](#r7-omada-controller)) |
| **T3: tenants** | Each tenant's networks, workloads, names, devices and applications | The tenant's repository, through the provider, and its own push ([ADR-0034](/docs/architecture/decisions/tenant-model/0034-tenants-deliver-their-own-code/)) | Device secrets, today in tenant state ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) moves them) |

**The rule this review applies:** a tier may depend on the tiers below it to build, and never on its
own tier or one above. T2 may hold copies, but nothing that exists nowhere below it.

### Where credentials live

| Class | Examples | Authoritative copy | Rebuild path |
|---|---|---|---|
| The floor | Vault password, offline CA keys, Proxmox `root@pam`, the router's web login | Kept outside every system | By procedure |
| Automation | `a_autoprov`'s key, ansible-vault contents, OpenBao's seal key, its `ansible` AppRole | ansible-vault, and the operator's computer for the private key | Roles re-seed from the vault |
| Service-to-service | API operator token, PowerDNS key, MinIO admin, broker writer and log writer keys, OPNsense key, Omada clients, Proxmox tokens | ansible-vault, copied into OpenBao KV for the API | Roles re-seed; OpenBao is a copy |
| Issued to tenants | API token, TSIG key, state keys, Wi-Fi keys, broker passwords, log tokens, dashboard password | Tenant state; the API keeps sealed working copies | The provider resupplies from state, for some ([T1](#t1-reconcile-coverage)) |
| Tenant-held | Workload SSH keys, the tenant's own secrets | The tenant | The tenant |

---

## Findings

Severity: **High** blocks a clean rebuild or exposes the whole site; **Medium** costs a manual
recovery or widens access beyond need; **Low** is drift or an unforced gap.

### Rebuild and dependencies

#### R1 Tenant Device CA key

**High. The Tenant Device CA's key exists only inside OpenBao, and nothing copies it.**
- It is generated inside OpenBao and never exported, by design (ADR-0031 §3). No Raft snapshot is
  taken; the snapshot drill is listed as unproven.
- An OpenBao rebuild from empty storage loses it. Recovery is a new key, a ceremony to sign it, and,
  once device identity is built (CHG-0034), every device enrolling again.
- It is the one T2 secret with no copy in a lower tier, and it breaks the tier rule.

*Evidence:* `ansible-collection-deevnet.mgmt/roles/openbao/defaults/main.yml` (`openbao_tenant_device_mount`),
`roles/openbao/tasks/tenant_device_ca.yml`, `runbook/substrate/recovery/substrate-secrets-drills.md`,
ADR-0033 open question 2.

*Recommendation:* decide this **before CHG-0034**. Issue the Tenant Device CA the way the Substrate CA
is issued, with its key in ansible-vault, imported into OpenBao's PKI mount. OpenBao keeps doing the
issuing; it stops being the only holder of the key.

#### R2 Registry and state on one VM

**High. The tenant registry and the tenants' state share the provisioning VM's OS disk.**
- ADR-0012 §5's one case that costs a re-flash of every device, losing both together, is a single
  failure of one disk.
- ADR-0033 decides the fix: device secrets move into tenant code. It is not built.

*Evidence:* `ansible-inventory-deevnet/mobile/hosts.yml` (`dv02prv001v01` in both groups), ADR-0033
Current state.

*Recommendation:* build ADR-0033's device-secret change first among tenant work. A data disk for both
stores is a cheap interim convenience: it survives an image rebuild, though not the disk.

#### R3 Losing the Builder

**High. The Builder can be rebuilt only when it is still there to help.**
- The repave runbook assumes a planned repave, with a temporary builder made from a template that
  itself needs the Builder (Packer's HTTP server, the artifact server, the key it fetches).
- Without warning, the control node is "a trusted-segment machine", with no steps to make one.
- The Builder holds state found nowhere else: the locally built images (the Deevnet API, VerneMQ),
  the router's configuration copies, the only Omada controller snapshot.

*Evidence:* `runbook/substrate/building-recovery/repave-builder.md`,
`policies/risk-management/resiliency.md`, `deevnet-container-image-factory/README.md`.

*Recommendation:* a short runbook to make a control node from nothing: clone the repositories,
install the tools, unlock the vault. Then move the Builder's unique state into git or rebuildable
form: images by tag from source, router configuration exported into the inventory.

#### R4 Build credentials from OpenBao

**Medium. Template and fabric builds read their Proxmox token from OpenBao by default, with no
automatic fallback.**
- `pve-creds` defaults to OpenBao and stops on an error. Rebuilding the management hypervisor or the
  identity VM needs the documented `PVE_CREDS_SOURCE=inventory` by hand.
- After a hypervisor rebuild, OpenBao holds the old token until `--tags openbao` runs again.
- It contradicts the control-plane rule: *"A control-plane service may make a rebuild easier; it must
  never be needed for one."*

*Evidence:* `deevnet-image-factory/Makefile` (`PVE_CREDS_SOURCE ?= openbao`), `scripts/pve-creds`,
`architecture/substrate/control-plane/`, `runbook/substrate/building-recovery/build-secrets.md`.

*Recommendation:* keep OpenBao as the everyday source, and fall back to the vault on its own when
OpenBao doesn't answer, saying so on the screen. Then no rebuild needs anyone to remember a flag.

#### R5 OpenBao re-initialization

**Medium. Re-initializing OpenBao leaves the vault holding credentials that no longer work.**
- The image-factory AppRole is reissued only when its vaulted values are empty; after a re-init they
  are present but dead, and builds get `400` until someone clears them by hand.
- The `ansible` AppRole and the recovery key are regenerated into a local file that must be vaulted,
  committed and pushed by hand (the lesson of INC-0003).

*Evidence:* `roles/openbao/tasks/build_secrets.yml`, `roles/openbao/tasks/init.yml`,
`playbooks/openbao.yml`, INC-0003.

*Recommendation:* reissue any AppRole whose vaulted credentials fail a login, as the API's role
already does for its own. Keep the one manual lock-in step, and make the play stop until it is done.

#### R6 Four rebuild orders

**Medium. The rebuild order is written in four places, and they disagree.**
- The greenfield runbook, ADR-0013 §8, ADR-0016 §6 and the `certs.yml` play each give an order.
- ADR-0016 §6 still says PowerDNS, the state store and the router need certificates from OpenBao;
  ADR-0031 removed that.
- One order is implied by code and nowhere written: the API's play needs the messaging and
  observability VMs up first, to read their host keys.

*Evidence:* `runbook/substrate/building-recovery/_index.md`, ADR-0013 §8, ADR-0016 §6, ADR-0031 §4,
`ansible-collection-deevnet.mgmt/playbooks/site.yml`, `playbooks/certs.yml`.

*Recommendation:* one page in the runbook holds the dependency graph by tier, including the manual
floor, and every ADR links to it rather than restating an order.

#### R7 Omada controller

**Medium. The controller has no backup, and rebuilding it loses the tenants' Wi-Fi keys.**
- The live controller has no snapshot; the cold fallback holds data an older image can't open.
- A fresh controller repeats the manual floor, and the AP is adopted again.
- The registry still lists every Wi-Fi key, and nothing pushes them back ([T1](#t1-reconcile-coverage)).

*Evidence:* `runbook/substrate/recovery/omada-controller-recovery.md`, ADR-0009 §5,
`deevnet-provisioning-api/internal/tenant/service.go` (`ensure`).

*Recommendation:* treat the controller as T2: site structure from inventory (ADR-0009), tenant keys
re-pushed from the registry by a reconcile. A scheduled export is a convenience, not the path.

#### R8 Packages from the internet

**Medium. Hosts install packages from the internet after their first boot.**
- The Correctness standard says substrate hosts *"MUST be provisionable without upstream internet
  dependencies"* (§5.4).
- The local mirror carries only the release repository, and installed hosts aren't pointed at it, so
  a role that installs a package needs the internet.

*Evidence:* `standards/correctness.md` §5.4,
`platforms/management-plane/builder-node/artifacts-role.md`.

*Recommendation:* either mirror the update repositories and point hosts at them, or narrow §5.4 to
the install and record the rest as an accepted exception. Today the standard and the site disagree
silently.

#### R9 The manual floor

**Low. The manual floor isn't written down in one place, and some of it needn't be manual.**
- Floor items are spread across six runbooks.
- Some could be code: Proxmox tokens (a role already declares the users and ACLs), staging the
  Fedora ISO into each hypervisor (a hidden step after a reinstall), and the PXE VM shell.
- Two leftover objects are never recreated: VMs 100 and 104, and `packer-prov@pve`.

*Evidence:* `runbook/substrate/building-recovery/build-hypervisor.md`,
`build-management-hypervisor-vm.md`, `packer/proxmox/fedora-base-image/fedora.pkr.hcl`.

*Recommendation:* list the floor on the rebuild graph page ([R6](#r6-four-rebuild-orders)), automate
the three above, and remove the leftovers.

### Tenant rebuild

#### T1 Reconcile coverage

**High. After a backend is rebuilt, a tenant's workloads, names, Wi-Fi keys and broker accounts don't
come back.**
- A reconcile re-ensures six steps: the zone and TSIG key, the resolver forwards, the state user, the
  network, the log store and the dashboards.
- A tenant's apply resends a resource only when the **registry** says it's gone. After a tenant
  hypervisor, controller or broker rebuild the registry still lists everything, so the plan is
  empty.
- The tenant runbook says so for workloads and names; it doesn't mention Wi-Fi keys or broker
  accounts.

*Evidence:* `deevnet-provisioning-api/internal/tenant/service.go` (`ensure`, `Read`),
`runbook/tenant/recovery/after-a-site-rebuild.md`, the Tenant Platform roadmap.

*Recommendation:* make the reconcile push **everything the registry holds** back into its backend,
idempotently: workloads, records, Wi-Fi keys, broker accounts. One operator command after any T2
rebuild then restores every tenant, without asking tenants to do anything.

#### T2 State-key recovery

**High. A tenant that loses its state-store keys has no way back in, and the docs say it does.**
- The keys live inside the state they unlock.
- The tenant runbook and the API's page say a reconcile returns the state secret. The code
  deliberately doesn't, and a test enforces it. The operator script also discards the response.

*Evidence:* `runbook/tenant/recovery/lost-credentials.md`, `platforms/deevnet-software/deevnet-api.md`,
`deevnet-provisioning-api/internal/server/tenants.go` (reconcile response),
`ansible-collection-deevnet.mgmt/scripts/tenant-reconcile.sh`.

*Recommendation:* under ADR-0033 the tenant keeps its backend credentials in its own repository,
encrypted, which ends the circularity. Until then, an operator-only reissue of the state key, and fix
both pages now.

#### T3 Tenant index

**Medium. A tenant can't ask for its own index, so a full rebuild can renumber tenants.**
- The API accepts a requested index, but admission takes only a name and a MAC, and the provider sends
  only the name on create. Only the restore path sends one.
- The API won't give a zone that still exists to another name, so this bites only when the fabric
  is gone too, which is a full rebuild.
- ADR-0033 says *"a tenant asks for its own index at creation"*. That isn't true yet.

*Evidence:* `deevnet-provisioning-api/internal/server/tenants.go`, `internal/tenant/service.go`
(`pickIndex`), `terraform-provider-deevnet/internal/provider/resource_tenant.go` (`index` computed).

*Recommendation:* make `index` an optional provider input, and record it in the tenant's repository.
Correct ADR-0033's sentence.

#### T4 Tenant tokens

**Medium. A tenant's API token can be neither reissued nor revoked.**
- There is no route to reissue a token while the tenant is registered.
- A removed tenant's token still verifies, and could create the tenant again. The removal runbook
  records this.

*Evidence:* `internal/tenant/service.go` (`Authenticate`), `runbook/substrate/tenant-removal.md`.

*Recommendation:* a token generation number inside the signed token, kept in the registry, which
makes both reissue and revoke one increment.

#### T5 OpenBao rebuild edges

**Medium, from reading the code, untested. Three edges in how tenants recover after OpenBao is
rebuilt:**
- A restore re-mints log tokens but doesn't return them, so tenant state keeps dead ones until an
  operator reconcile, whose output the script discards.
- The dashboard password is re-minted, but the provider doesn't mark it unknown, which likely fails
  the apply with an inconsistent-result error.
- A reconcile run before tenants resupply their secrets has no guard against unreadable values, and
  may push empty TSIG and state secrets into PowerDNS and the state store.

*Evidence:* `internal/tenant/service.go` (`restoreExisting`, `Reconcile`), `internal/tenant/logtokens.go`,
`terraform-provider-deevnet/internal/provider/resource_tenant.go`.

*Recommendation:* guard the reconcile, return what a restore re-mints, and add an OpenBao-rebuild case
to the integration tests.

#### T6 Credential handover

**Low. Admission credentials are handed over by hand, and the record describing another way is
stale.**
- ADR-0012 §9's age-encrypted delivery isn't built; the admission script writes a text file for a
  person to hand over.
- §9 still names a retired registry and Makefile target.

*Evidence:* `runbook/substrate/tenant-admission.md`, `scripts/tenant-admission.sh`, ADR-0012 §9.

*Recommendation:* decide whether the text-file handover is the design. If it is, amend §9 to say so.

#### T7 Full-rebuild plan

**Low. The full-rebuild roadmap has no tenant steps, and the tenant runbook omits re-admission.**
After a full rebuild every tenant needs a new admission just to reach `DVNTM-TD`.

*Evidence:* `roadmap/infrastructure/mobile/full-rebuild.md`,
`runbook/tenant/recovery/after-a-site-rebuild.md`.

*Recommendation:* add re-admission and re-apply to both.

### Accounts and access

#### A1 Exposure tracking

**High. Credentials known to have been exposed earlier in the site's life aren't tracked.**
The risk register holds no entry for them, and whether each was rotated isn't recorded.

*Evidence:* `policies/risk-management/risk-register.md`.

*Recommendation:* a register entry, and a check of each exposed credential against its current value.
The details belong with the operator, not on this page.

#### A2 One session reaches everything

**High. An operator session on the Builder reaches every secret on the site.**
- The secure-identity standard forwards the operator's SSH agent. The forwarded `a_autoprov` key has
  passwordless sudo on every substrate host, including the identity VM (OpenBao's seal key and data)
  and the provisioning VM (the operator token).
- ADR-0016 §2 kept the vault password out of a file so that a shell on the Builder would not equal
  every secret. Agent forwarding makes that true anyway, for the length of a session.

*Evidence:* `standards/secure-identity.md`, `runbook/substrate/network/operator-access.md`,
ADR-0016 §2, `deevnet-image-factory/packer/proxmox/fedora-base-image/http/kickstart.cfg.pkrtpl` (sudo rule).

*Recommendation:* short-lived SSH certificates from OpenBao's SSH engine, by role, in place of one
forwarded key that works everywhere. ADR-0025's open question 2 already points there. Recording
forwarding as an accepted risk is also a fair answer.

#### A3 Bootstrap over plain HTTP

**Medium. The bootstrap fetches the automation key and a root script over plain HTTP.**
- Kickstart and the template build fetch `a_autoprov`'s public key from the artifact server by HTTP.
- The hypervisor bootstrap runs `curl http://… | bash` as root.
- Anything that can answer for the artifact server on that segment can plant a key or run code.

*Evidence:* `runbook/substrate/building-recovery/build-hypervisor.md`,
`packer/proxmox/fedora-base-image/http/kickstart.cfg.pkrtpl`.

*Recommendation:* check each fetched file against a SHA-256 kept in the inventory. That works before
any TLS trust exists, so it adds no cycle.

#### A4 OpenBao's own access

**Medium. OpenBao's automation identity is root in practice, and nothing audits it.**
- The `ansible` AppRole can write any ACL policy and any AppRole, which reaches everything. Its
  definition says *"Not root"*.
- No AppRole sets a secret-id lifetime or binds to an address.
- There is no audit device, although the build-secrets runbook and the role's comments say every
  read is audited.

*Evidence:* `roles/openbao/defaults/main.yml`, `roles/openbao/tasks/configure.yml`,
`runbook/substrate/building-recovery/build-secrets.md`, ADR-0016 open question 2, INC-0003
follow-up 5.

*Recommendation:* turn on a file audit device; bind each AppRole's secret-id to the hosts that use it;
call the `ansible` AppRole what it is in its comment, or split policy-writing out of it.

#### A5 Proxmox permissions

**Medium. Proxmox tokens hold far more than their jobs need.**
- The build token on both hypervisors is Administrator at `/`.
- The API's tenant-builder role is granted at `/`, not per tenant pool as ADR-0015 §6 describes.
- Two leftovers hold Administrator with nothing using them.

*Evidence:* `ansible-inventory-deevnet/mobile/host_vars/dv02hyp00*/vars.yml`, ADR-0015 §6, the Tenant
Platform roadmap.

*Recommendation:* scope the build token to templates and storage, the API's role to a tenant pool,
and remove the leftovers.

#### A6 Shared credentials

**Medium. Some credentials are shared between consumers that need different things.**
- One OPNsense API key serves both Ansible and the API, which only writes DNS forwards.
- The Grafana server admin is shared between Grafana and the API.
- The API's MinIO admin can attach any policy, including to itself.
- The log bridge's single token writes every tenant's partition, by design (ADR-0027).

*Evidence:* `group_vars/deevnet_api/vars.yml`, `roles/minio/defaults/main.yml`, ADR-0015 open
question 3.

*Recommendation:* a key per consumer where the product allows it, starting with OPNsense. Record the
rest as accepted.

#### A7 Secrets in container environments

**Medium. Running containers carry their secrets in their environment, readable with
`podman inspect`.**
The API's container holds the operator token and its OpenBao secret-id there; Grafana's holds its
admin password. The operator scripts read the operator token that way on purpose.

*Evidence:* `roles/deevnet_api/tasks/main.yml`, `scripts/lib/deevnet-api.sh`.

*Recommendation:* mount secrets as files with Podman secrets, and have the operator scripts read the
token from the vault.

#### A8 Rotation

**Medium. Rotation is written down for only a few credentials.**
- The credential-rotation roadmap has none of its tasks done, and its inventory leaves out several
  classes: Omada, the switch, OpenBao, Grafana, the bridge, the token signing key.
- The OpenBao role describes a seal-key rotation setting that nothing implements.
- Some rotation pages still name retired files and settings.

*Evidence:* `roadmap/infrastructure/credential-rotation.md`, `roles/openbao/defaults/main.yml`,
`templates/openbao.hcl.j2`.

*Recommendation:* one rotation page per credential class, ordered by blast radius, with the
automation first.

### Tenant secrets

#### S1 Tenant secrets

**Open. How a tenant's secrets reach its workloads is undecided, and this review does not decide it.**

**What exists:**
- Secrets the substrate issues come back as resource attributes, land in tenant state, and reach a
  workload in `kit.env`, which the tenant pushes (ADR-0034). That is how eds runs.
- Secrets a tenant brings itself, such as a third-party API key, have no defined home.
- [ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/)'s OpenBao namespaces are
  unbuilt, and the channel it relied on to give each workload its OpenBao identity went with ADR-0017.

**The criteria a decision should meet,** from the rest of this review:
- The authoritative copy is the tenant's code (ADR-0033); any substrate copy can be lost.
- Delivery is the tenant's push (ADR-0034); no new channel is needed to start a service.
- A substrate rebuild costs the tenant at most a redeploy.
- OpenBao, if used, holds copies only ([R1](#r1-tenant-device-ca-key)'s rule).

**The shapes that meet them:**

| Shape | The tenant keeps | The workload gets | Gains | Costs |
|---|---|---|---|---|
| Secrets as code | Its secrets, encrypted in its repository | An env file the tenant pushes | Nothing to build; matches eds today | A secret on the workload's disk; rotation is a push; no per-workload revocation or read audit |
| OpenBao as a runtime copy | The same | An OpenBao identity the tenant pushes once; reads at start | Rotation without a push, per-workload revocation, an audit trail, secrets in memory | Namespaces, a provider resource, a read client; OpenBao needed to start a service |
| Both | The same | Its choice per workload | Tenants choose their own trade | Two paths to document and support |

---

### Documentation drift

#### D1 Stale records and pages

**Low. Many pages describe a past state.**
- **ADR Current-state sections** that say something is unbuilt that is built, or name retired hosts:
  ADR-0004, 0005, 0006, 0007, 0010, 0011, 0012, 0013, 0014, 0015, 0018, 0020, 0021, 0023, 0026, 0027.
- **Claims that are wrong:**
  - the state-key recovery ([T2](#t2-state-key-recovery));
  - "every read is audited" ([A4](#a4-openbaos-own-access));
  - the build verification page saying a reconcile exercises broker accounts;
  - the security-controls page still describing the retired ADR-0030 hierarchy and "no passwords in
    inventory";
  - the tenant guide's provider version (`~> 0.4` against the published 0.5).
- **Code comments** still naming the bootstrap intermediate and "the site CA in OpenBao".

*Recommendation:* one sweep, records first.

---

## Recommendations

### Principles

**A tier depends only on the tiers below it.** The four tiers above become the stated rebuild model,
on one runbook page, with the manual floor listed ([R6](#r6-four-rebuild-orders), [R9](#r9-the-manual-floor)).

**OpenBao stays, as a T2 service that holds copies.** It keeps issuing, encrypting, wrapping and
serving builds. Nothing in T1 needs it to build ([R4](#r4-build-credentials-from-openbao)), and nothing
in it exists nowhere else ([R1](#r1-tenant-device-ca-key)). That keeps everything built so far and
makes losing it a rebuild, not a ceremony.

**The registry heals its backends.** One reconcile puts back everything the registry holds, so any T2
rebuild ends with one operator command ([T1](#t1-reconcile-coverage)).

**Every credential has an owner, a scope and a reissue path.** Per consumer where possible, short-lived
where practical, and written down ([A4](#a4-openbaos-own-access) to [A8](#a8-rotation), [T4](#t4-tenant-tokens)).

### Sequence

| When | What | Findings | Becomes |
|---|---|---|---|
| **Now** | Correct the wrong claims: state-key recovery, the audit claim, ADR-0033's index sentence | T2, A4, T3, D1 | A docs PR |
| **Now** | Register entry and rotation check for previously exposed credentials | A1 | Risk register, then a change |
| **Now** | Decide where the Tenant Device CA's key lives | R1 | An ADR (ADR-0033 open question 2) |
| **Next** | Reconcile re-pushes everything the registry holds; guard and test the OpenBao-rebuild edges | T1, T5, R7 | A change |
| **Next** | Device secrets into tenant code; `index` as a provider input; token generations | R2, T3, T4 | ADR-0033's change |
| **Next** | `pve-creds` falls back on its own; AppRoles reissue themselves; an audit device | R4, R5, A4 | A change |
| **Next** | The rebuild graph page with the floor; a control node from nothing | R6, R9, R3 | Runbook pages |
| **Later** | SSH certificates by role in place of a forwarded key | A2 | An ADR, with ADR-0025 |
| **Later** | Checksums on bootstrap fetches; Proxmox least privilege; per-consumer keys; secrets as files | A3, A5, A6, A7 | Changes |
| **Later** | Update mirror, or narrow §5.4 | R8 | A change or a standards amendment |
| **When decided** | Tenant secrets | S1 | An ADR, superseding or amending ADR-0021 |

---

## Open for the operator

**These are choices this review can inform but not make:**
- **Tenant secrets** ([S1](#s1-tenant-secrets)): code, an OpenBao copy, or both.
- **Agent forwarding** ([A2](#a2-one-session-reaches-everything)): replace it with SSH certificates,
  or accept it as a recorded risk.
- **The manual floor** ([R9](#r9-the-manual-floor)): which parts stay manual on purpose.
- **Offline provisioning** ([R8](#r8-packages-from-the-internet)): mirror updates, or narrow the
  standard.
