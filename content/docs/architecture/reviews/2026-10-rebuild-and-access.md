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
| **Status** | Responded. The operator answered all 26 findings by 2026-10-06 (A2 and T4 deferred); each response is under its finding. Each finding acted on becomes an ADR or a change record |

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

### Responses so far

**The operator has responded to all 26 findings: 24 decided, two deferred.** Each response is under
its finding; in short:

| Finding | Response |
|---|---|
| [R1](#r1-tenant-device-ca-key) Tenant Device CA key | **Agreed.** The key goes into ansible-vault and is loaded into OpenBao as configuration on a rebuild |
| [R2](#r2-registry-and-state-on-one-vm) Registry and state on one VM | **Agreed, with a framing:** a backup is a *recovery shortcut*. Tenants must still rebuild from nothing when no backup survives. Direction for a backup target: encrypted backups on USB drives |
| [R3](#r3-losing-the-builder) Losing the Builder | **Agreed.** A new first page, *Build the Builder*, makes a control node from a bare machine |
| [R4](#r4-build-credentials-from-openbao) Build credentials from OpenBao | **Decided differently:** substrate builds use ansible-vault only and never OpenBao. OpenBao exists to serve tenants |
| [R5](#r5-openbao-re-initialization) OpenBao re-initialization | **Agreed.** The play stops until the lock-in is done |
| [R6](#r6-four-rebuild-orders) Four rebuild orders | **Agreed,** plus a recovery chart of what a failed component's blast radius is |
| [R7](#r7-omada-controller) Omada controller | **Agreed.** The controller is a T2 service |
| [R8](#r8-packages-from-the-internet) Packages from the internet | **Narrow the standard now, mirror later.** §5.4 covers the install; package installs and updates afterwards are a recorded exception |
| [R9](#r9-the-manual-floor) The manual floor | **Mixed:** Proxmox tokens stay manual; the Fedora ISO and the network-boot VM shell are automated; the stray VMs are moved by a change, not deleted |
| [T1](#t1-reconcile-coverage) Reconcile coverage | **Agreed.** The reconcile puts back everything the registry holds, with the same secrets. The Transit key moves to the vault, like the Tenant Device CA's |
| [T2](#t2-state-key-recovery) State-key recovery | **Agreed:** the tenant keeps its own copy in the long term; an operator reissue now; the docs corrected |
| [T3](#t3-tenant-index) Tenant index | **Accept renumbering,** with a rule: tenants use names, never addresses |
| [T4](#t4-tenant-tokens) Tenant tokens | **Deferred** |
| [T5](#t5-openbao-rebuild-edges) OpenBao rebuild edges | **Agreed,** fixed in the same change as T1 |
| [T6](#t6-credential-handover) Credential handover | **The text file is the design;** the ADRs amended |
| [T7](#t7-full-rebuild-plan) Full-rebuild plan | **Agreed:** tenant steps added to both pages |
| [A1](#a1-exposure-tracking) Exposure tracking | **Agreed:** a register entry, a check of each credential, secret scanning; no history rewrite |
| [A4](#a4-openbaos-own-access) OpenBao's own access | **Agreed:** an honest description, bound logins, a file audit device |
| [A5](#a5-proxmox-permissions) Proxmox permissions | **Agreed:** narrow the build tokens, amend ADR-0015 to the API's role as built, remove the leftovers |
| [A6](#a6-shared-credentials) Shared credentials | **Agreed:** separate OPNsense and Grafana credentials for the API; MinIO and the bridge accepted |
| [A7](#a7-secrets-in-container-environments) Secrets in container environments | **Agreed, later:** secrets as files |
| [A8](#a8-rotation) Rotation | **Agreed:** the list fixed, rotation written as each change touches a credential |
| [S1](#s1-tenant-secrets) Tenant secrets | **Secrets as code now;** ADR-0021 parked |
| [D1](#d1-stale-records-and-pages) Stale records and pages | **Agreed:** one sweep |
| [A2](#a2-one-session-reaches-everything) One session reaches everything | **Deferred,** with the mechanics of short-lived SSH certificates recorded |
| [A3](#a3-bootstrap-over-plain-http) Bootstrap over plain HTTP | **Agreed, extended:** the artifact server moves to HTTPS, with plain HTTP kept only where nothing can verify |

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

**Response (2026-10-06): agreed.** The Tenant Device CA's key is generated outside OpenBao, kept in
ansible-vault, and imported into OpenBao's PKI mount on every build, as configuration data. OpenBao
keeps issuing device certificates; losing it costs a re-import, not a ceremony and a re-enrollment of
every device. It lands before device identity (CHG-0034), and answers ADR-0033's open question 2.

#### R2 Registry and state on one VM

**High. The tenant registry and the tenants' state share the provisioning VM's OS disk.**
- ADR-0012 §5's one case that costs a re-flash of every device, losing both together, is a single
  failure of one disk.
- ADR-0033 decides the fix: device secrets move into tenant code. It is not built.

*Evidence:* `ansible-inventory-deevnet/mobile/hosts.yml` (`dv02prv001v01` in both groups), ADR-0033
Current state.

*Recommendation:* build ADR-0033's device-secret change first among tenant work. A data disk for both
stores is a cheap interim convenience: it survives an image rebuild, though not the disk.

**Response (2026-10-06): a backup is a recovery shortcut, never the recovery path.** Tenants must be
able to rebuild from nothing if no backup survives; when one does, it makes recovery faster.

**That holds fully only once device secrets leave tenant state.** A backup of the provisioning VM
restores the registry, the audit log and every tenant's state in one step. Without one, tenants
rebuild from their repositories, but today a device's broker password and Wi-Fi key live only in
that state, so every device would need re-provisioning. ADR-0033's device-secret change removes that
cost, and from then on the backup is only a shortcut.

**A restored backup is a starting point.** It is always followed by a reconcile that brings the
registry's backends back in line ([T1](#t1-reconcile-coverage)), since a backup older than a tenant's
last apply would otherwise put old values back.

**Direction for a backup target, not yet decided:** one or two USB drives on the management
hypervisor.
- **The backup files are encrypted before they reach the drive**, with a key in ansible-vault (`age`
  or `restic`). A lost drive is ciphertext, and a restore needs only the vault. Not disk encryption
  with a key on the host, which protects only a removed drive, and not a key in OpenBao, which a
  restore would need running first.
- **Data, not the VM:** a database dump and a mirror of the state bucket, small and restorable onto a
  freshly built VM.
- **Two drives, one kept away from the kit**, which also covers losing the whole site and a
  compromise that would wipe a connected drive.
- **On the management hypervisor**, on media separate from the VM's disk; never on the tenant
  hypervisor. A small USB SSD outlasts a thumb drive.
- **A missing drive fails loudly**, and a restore is tried now and then.

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

**Response (2026-10-06): agreed, as *Build the Builder*.** Building the Builder was a core idea from
the start, and the runbook never captured it. It becomes the first page of Building Infrastructure,
before Stage Artifacts.

**What already exists, and what the page adds:**
- **The tooling is code.** The Builder collection's `workstation` role installs the control node's
  tools: Ansible's dependencies, Packer, Terraform and the image-build prerequisites.
- **Repave the Builder covers a planned repave**, through a temporary builder cloned from a template
  on the management hypervisor. It calls the machine Ansible runs from "a trusted-segment machine",
  never the **Ansible control node**.
- **The page adds the start from a bare machine:** on any Fedora machine, install Ansible and git,
  clone the repositories, install the collections, run the `workstation` role against `localhost`,
  then load the automation key and unlock the vault. From there, the Builder stages artifacts and
  builds everything else, with no help from anything already on the site.
- **The Builder's unique state** (locally built images, the router's configuration copies, the
  controller snapshot) is moved to git or made rebuildable, so nothing is lost with it.

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

**Response (2026-10-06): substrate builds never use OpenBao.** Images, hypervisors, management-plane
VMs and the tenant fabric take their credentials from ansible-vault, always. OpenBao exists to serve
tenants. The two are separate uses, with separate accounts.

**What follows:**
- **The build path leaves OpenBao.** `pve-creds` reads the vault only; the `image-factory` AppRole
  and its copies of the Proxmox tokens in OpenBao are removed. That reverses most of
  [CHG-0026](/docs/changes/2026/0026-build-secrets/), and with it this finding and half of
  [R5](#r5-openbao-re-initialization) disappear.
- **Proxmox accounts split by purpose:** the substrate's build tokens, in the vault only, and the
  Deevnet API's own account for building tenant workloads.
- **The Deevnet API's backend credentials stay in OpenBao.** The API serves tenants, and it is among
  the last things restored in a recovery.
- **OpenBao keeps** the API's backend credentials, Transit for tenant secrets, the Tenant Device CA
  (its key imported from the vault, [R1](#r1-tenant-device-ca-key)), and response wrapping for
  enrollment.

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

**Response (2026-10-06): agreed; the play stops until the lock-in is done.**

**What the lock-in is.** OpenBao on empty storage is initialized once. That creates a recovery key
and a one-time root token, which the role uses to create its own login, the `ansible` AppRole, and
then discards. The recovery key and the AppRole's credentials are written only to a file on the
control node; until they are in the vault, committed and pushed, that file is their only copy. That
is the step INC-0003 missed.

**What changes.** After an initialization, the next run checks that the vault's `ansible` AppRole can
log in, and stops with a message naming the file if it can't. The lock-in itself stays manual:
secrets are never committed automatically. The dead-credential half of this finding goes with the
`image-factory` AppRole ([R4](#r4-build-credentials-from-openbao)); the API's own AppRole already
reissues itself. With [R1](#r1-tenant-device-ca-key), a re-initialization costs time, not a CA.

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

**Response (2026-10-06): agreed, plus a recovery chart.** Beside the one rebuild-order page, a chart
answers the other question: *this failed; what do I redo?* For each component:

| Failed component | Rebuild | Then redo, downstream | Tenants affected | Who acts |
|---|---|---|---|---|
| Identity VM (OpenBao, tenant DNS) | The VM; OpenBao from the vault; PowerDNS | API restart; tenants resupply on their next apply; a reconcile | Names, until republished | Operator, then tenants |
| Provisioning VM (API, registry, state store) | The VM, the API, the store | Restore from a backup if one survives, or re-admit; a reconcile | All, until restored or re-admitted | Operator, then tenants |
| Management hypervisor | The host, then every domain VM | Everything in T2 | All | Operator |
| Tenant hypervisor | The host, the fabric, egress | A reconcile; tenants push their applications again | Workloads | Operator, then tenants |
| Omada controller | The VM, the manual floor, AP adoption | Wi-Fi keys re-pushed | Device Wi-Fi | Operator |
| Broker | The VM, VerneMQ | Broker accounts re-pushed | Device MQTT | Operator |
| Builder | Build the Builder ([R3](#r3-losing-the-builder)) | Re-stage artifacts; rebuild local images | None directly | Operator |
| Core router | USB install, then its configuration | The API's tenant DNS forwards | Tenant name resolution | Operator |

**The chart is also a check on the tier rule.** A row whose recovery needs a backup, rather than a
rebuild from code, marks a place where something can't be re-derived.

#### R7 Omada controller

**Medium. The controller has no backup, and rebuilding it loses the tenants' Wi-Fi keys.**
- The live controller has no snapshot; the cold fallback holds data an older image can't open.
- A fresh controller repeats the manual floor, and the AP is adopted again.
- The registry still lists every Wi-Fi key, and nothing pushes them back ([T1](#t1-reconcile-coverage)).

*Evidence:* `runbook/substrate/recovery/omada-controller-recovery.md`, ADR-0009 §5,
`deevnet-provisioning-api/internal/tenant/service.go` (`ensure`).

*Recommendation:* treat the controller as T2: site structure from inventory (ADR-0009), tenant keys
re-pushed from the registry by a reconcile. A scheduled export is a convenience, not the path.

**Response (2026-10-06): agreed; the controller is a T2 service.** Its site structure comes back from
inventory (ADR-0009), tenants' Wi-Fi keys are re-pushed from the registry by the reconcile
([T1](#t1-reconcile-coverage)), and a scheduled export is only a convenience. The setup wizard, the
Owner account and the Open API clients stay on the manual floor ([R9](#r9-the-manual-floor)).

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

**Response (2026-10-06): narrow §5.4 now, mirror later.** The standard is amended to match the site:
the install stays offline (the OS install, network boot and artifacts), and package installs and
updates after first boot are a recorded exception that needs the internet. Mirroring Fedora's
`updates` repository, and Proxmox's, stays on the roadmap through the existing
[package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/) evaluation,
and restores the stricter rule if an offline rebuild comes to matter.

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

**Response (2026-10-06), item by item:**
- **Proxmox API tokens stay manual.** Proxmox shows a token's secret once; automating it would only
  trade one manual step (issuing it) for another (locking it into the vault). The role already stops
  when a declared token is missing.
- **The Fedora ISO is automated.** The artifacts role publishes the ISO for every release the image
  factory still builds, and the template build fetches it, so a reinstalled hypervisor needs no
  hand-placed ISO.
- **The network-boot VM shell is automated,** as an empty-shell mode of the role that creates VMs.
- **The stray VMs are moved, not deleted.** VMs 100 and 104 on the management hypervisor are kept,
  and a change record moves them off it. **The substrate hypervisors run the lab now: anything
  experimental lives in a tenant.** The unused `packer-prov@pve` user goes with
  [A5](#a5-proxmox-permissions).

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

**Response (2026-10-06): agreed; the reconcile puts back everything the registry holds.** One operator
command after any T2 rebuild restores every tenant:
- **Workloads** missing from their hypervisor are cloned again with the same identity (VMID, MAC,
  address and name, all derived from the tenant's index) and the tenant's SSH keys. They come back
  as the template: the tenant pushes its application again
  ([ADR-0034](/docs/architecture/decisions/tenant-model/0034-tenants-deliver-their-own-code/)), and
  its SSH client sees new host keys once.
- **DNS records** are published again.
- **Wi-Fi keys and broker accounts** are written back with **the same secrets**, from the API's stored
  copies, so devices reconnect without a visit. A tenant's own `-replace` today would mint new
  secrets and cost every device a visit; once a tenant supplies its device secrets from code
  ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)), its own
  `-replace` becomes safe too.
- **A stored copy that can't be read is skipped and reported**, never written empty
  ([T5](#t5-openbao-rebuild-edges)); the tenant's next apply resupplies it.

**The registry is what this restores from, so the registry belongs in the backup
([R2](#r2-registry-and-state-on-one-vm)):** the API's database and the state bucket. The API's stored
copies are encrypted with OpenBao's Transit key, which today exists only inside OpenBao; a rebuilt
OpenBao has a new one that can't open a restored database. **So the Transit key is handled like the
Tenant Device CA's key ([R1](#r1-tenant-device-ca-key)):** held in ansible-vault and imported into
OpenBao on every build. A database backup is then readable with the vault alone. The rule this makes:
**any key OpenBao uses that can't be re-derived is held in the vault and loaded as configuration.**

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

**Response (2026-10-06): agreed, in three parts.**
- **Long term:** the tenant keeps its state-store credentials in its own repository, encrypted, beside
  its device secrets ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)),
  which ends the circle.
- **Now:** an operator-only **reissue** that mints a new state secret, updates the tenant's user in the
  store, and hands the secret over like an enrollment token. The reconcile keeps refusing to return
  the existing one, as the code intends.
- **The docs are corrected** to say what is true until then: there is no recovery path for a lost
  state secret yet.

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

**Response (2026-10-06): accept renumbering, with a rule: tenants use names, never addresses.**
- **A tenant can't choose its index well.** Tenants can't see each other's indexes, so a chosen index
  is a blind pick, and keeping them stable would need an ordering rule for every re-admission.
- **Renumbering is rare and mostly invisible.** It happens only in a full rebuild where a tenant has
  also lost its state; a tenant that kept its state keeps its index through the restore path. Names
  stay the same and are published to the new addresses; topics use the tenant's name; the operator's
  route covers every tenant; dashboards use fixed data-source identifiers.
- **What breaks is an address pinned somewhere,** so the tenant guide says to use names, never
  addresses, and ADR-0033's sentence is corrected to what is true: a tenant with its state keeps its
  index, and one without may get a new one.

#### T4 Tenant tokens

**Medium. A tenant's API token can be neither reissued nor revoked.**
- There is no route to reissue a token while the tenant is registered.
- A removed tenant's token still verifies, and could create the tenant again. The removal runbook
  records this.

*Evidence:* `internal/tenant/service.go` (`Authenticate`), `runbook/substrate/tenant-removal.md`.

*Recommendation:* a token generation number inside the signed token, kept in the registry, which
makes both reissue and revoke one increment.

**Response (2026-10-06): deferred.** The leading option is a generation number inside each token,
kept in the registry: a reissue bumps it, and removing a tenant leaves a small tombstone so its old
token is refused. With the registry lost, tokens verify by signature alone, as today, so recovery is
unchanged. Rotating the signing key, which replaces every tenant's token at once, stays the emergency
option.

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

**Response (2026-10-06): agreed, in the same change as [T1](#t1-reconcile-coverage).** A restore
returns what it re-mints, the operator's reconcile shows new log tokens instead of discarding them, the
provider expects a changed dashboard password, unreadable copies are skipped, and an "OpenBao rebuilt"
case joins the integration tests. With the Transit key held in the vault (T1), a rebuilt OpenBao keeps
its key, and these become defense in depth.

#### T6 Credential handover

**Low. Admission credentials are handed over by hand, and the record describing another way is
stale.**
- ADR-0012 §9's age-encrypted delivery isn't built; the admission script writes a text file for a
  person to hand over.
- §9 still names a retired registry and Makefile target.

*Evidence:* `runbook/substrate/tenant-admission.md`, `scripts/tenant-admission.sh`, ADR-0012 §9.

*Recommendation:* decide whether the text-file handover is the design. If it is, amend §9 to say so.

**Response (2026-10-06): the text file is the design.** The handover is one-time and short-lived (a
single-use enrollment token, and the developer Wi-Fi key), and handing it over by hand is adequate
here. ADR-0012 §9 and ADR-0015 §10 are amended to say so. If tenants adopt age for their own secrets
([S1](#s1-tenant-secrets)), encrypted delivery can be revisited.

#### T7 Full-rebuild plan

**Low. The full-rebuild roadmap has no tenant steps, and the tenant runbook omits re-admission.**
After a full rebuild every tenant needs a new admission just to reach `DVNTM-TD`.

*Evidence:* `roadmap/infrastructure/mobile/full-rebuild.md`,
`runbook/tenant/recovery/after-a-site-rebuild.md`.

*Recommendation:* add re-admission and re-apply to both.

**Response (2026-10-06): agreed.** The Full Site Rebuild roadmap gains a "bring tenants back" step,
and *After a Site Rebuild* says what a tenant does after a whole-site rebuild: wait for the new
handover, apply, and push its application again.

### Accounts and access

#### A1 Exposure tracking

**High. Credentials known to have been exposed earlier in the site's life aren't tracked.**
The risk register holds no entry for them, and whether each was rotated isn't recorded.

*Evidence:* `policies/risk-management/risk-register.md`.

*Recommendation:* a register entry, and a check of each exposed credential against its current value.
The details belong with the operator, not on this page.

**Response (2026-10-06): a register entry, a check, and secret scanning; no history rewrite.** The
risk register records the exposure as a class (R-15). Each exposed credential is compared with its
current value without either being displayed, and any still in use is rotated. Public repositories
get a secret scan on every push. History is not rewritten: copies may already exist elsewhere, so
rotation is the fix.

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

**Response (2026-10-06): deferred.** The choice is between accepting forwarding as a recorded risk, a
vault-held SSH certificate authority with short-lived certificates, and the same with principals per
tier or role. The mechanics are recorded here for when it is taken up.

**What a certificate changes.** The operator keeps a key pair. A certificate authority signs its
public key into a certificate naming who it is, what it may log in as (its principals), and when it
expires. Each host trusts the authority once, in place of a list of keys. A leaked certificate stops
working in hours; principals can narrow what one opens; adding or removing a key is a signing
decision with nothing pushed to hosts. It does not close the window while a forwarded session is
open; it shortens and narrows it.

**Where the authority lives.** Not in OpenBao: substrate access is not a tenant service
([R4](#r4-build-credentials-from-openbao)). Its key sits in ansible-vault like the Substrate CA's, and
a make target on the control node signs the operator's key for a few hours and loads it into the
agent.

**A fresh host has no chicken-and-egg problem.** Today the install plants one public key and a sudo
rule: kickstart's `%post` fetches the automation key into `authorized_keys`, the hypervisor bootstrap
does the same, and the Pi images carry it. With certificates the install plants the authority's
**public** key and one sshd line, `TrustedUserCAKeys`, instead. Signing happens on the control node
before Ansible connects, so the new host needs nothing but what its install gave it. The automation
key stays as a break-glass key, kept offline. The switch and the core router, reached by password
and by API, are outside this. The same authority could also sign host keys, which would end the
"host identification has changed" warning after every repave.

#### A3 Bootstrap over plain HTTP

**Medium. The bootstrap fetches the automation key and a root script over plain HTTP.**
- Kickstart and the template build fetch `a_autoprov`'s public key from the artifact server by HTTP.
- The hypervisor bootstrap runs `curl http://… | bash` as root.
- Anything that can answer for the artifact server on that segment can plant a key or run code.

*Evidence:* `runbook/substrate/building-recovery/build-hypervisor.md`,
`packer/proxmox/fedora-base-image/http/kickstart.cfg.pkrtpl`.

*Recommendation:* check each fetched file against a SHA-256 kept in the inventory. That works before
any TLS trust exists, so it adds no cycle.

**Response (2026-10-06): agreed, and extended to HTTPS.** With the Deevnet PKI in place, the artifact
server gets a Substrate CA certificate. Plain HTTP stays only where nothing can verify yet:
- **Everything after install uses HTTPS**: Ansible's fetches, the control node, and hosts once they
  trust the Deevnet Root.
- **The boot payload stays on HTTP.** Firmware and GRUB fetch the kernel and initrd and can't do
  HTTPS.
- **The kickstart carries the Root CA's certificate.** It is public; `%post` writes it into the trust
  store, and every fetch after that is HTTPS, verified. The templates already carry the root
  (ADR-0030 §7).
- **The hypervisor bootstrap is pinned by hash**, since a freshly installed Proxmox doesn't trust the
  root yet. After it runs, the rest is HTTPS.
- **The first network-boot hop stays unverified** on the management segment. Closing it would need
  UEFI HTTP boot with an enrolled certificate, which is out of proportion for this site.

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

**Response (2026-10-06): agreed on all three.**
- **The `ansible` AppRole is described as what it is:** root-equivalent, held only in ansible-vault.
  It isn't split; both halves would sit in the same vault.
- **Logins are bound:** the API's secret ID to the provisioning VM's address, with an expiry (its role
  reissues it); Ansible's to the Builder's addresses, without one.
- **A file audit device** on the identity VM's disk, rotated, since the log store holds tenant data
  only. The docs say what is true until then.

#### A5 Proxmox permissions

**Medium. Proxmox tokens hold far more than their jobs need.**
- The build token on both hypervisors is Administrator at `/`.
- The API's tenant-builder role is granted at `/`, not per tenant pool as ADR-0015 §6 describes.
- Two leftovers hold Administrator with nothing using them.

*Evidence:* `ansible-inventory-deevnet/mobile/host_vars/dv02hyp00*/vars.yml`, ADR-0015 §6, the Tenant
Platform roadmap.

*Recommendation:* scope the build token to templates and storage, the API's role to a tenant pool,
and remove the leftovers.

**Response (2026-10-06): agreed on all three.** The build tokens get a custom role with only what
Packer and the fabric need, its privileges confirmed against Proxmox's documentation and a test build,
in the same change as [R4](#r4-build-credentials-from-openbao). The API's role stays at `/`, and
ADR-0015 §6 is amended to that: per-tenant pools would need the API to hold the right to grant
permissions. The two unused accounts are removed.

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

**Response (2026-10-06): separate the two that can be separated.** The Deevnet API gets its own
OPNsense user, limited to the resolver's settings, which takes it off the firewall; and its own Grafana
server-admin login, with the same rights but its own credential. The MinIO admin's ability to grant
itself access, and the log bridge's single token, are recorded as accepted.

#### A7 Secrets in container environments

**Medium. Running containers carry their secrets in their environment, readable with
`podman inspect`.**
The API's container holds the operator token and its OpenBao secret-id there; Grafana's holds its
admin password. The operator scripts read the operator token that way on purpose.

*Evidence:* `roles/deevnet_api/tasks/main.yml`, `scripts/lib/deevnet-api.sh`.

*Recommendation:* mount secrets as files with Podman secrets, and have the operator scripts read the
token from the vault.

**Response (2026-10-06): secrets as files, as a low-priority later item.** Grafana reads its admin
password from a mounted file; the API learns to read its secrets from files at its next change; the
operator scripts read the token from that file instead of through `podman inspect`. The exposure is
root-only either way; the gain is fewer accidental leaks.

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

**Response (2026-10-06): fix the list, and rotate as we go.** The rotation roadmap's list is rewritten
to the real set of credentials, ordered by what each reaches. Every change that touches a credential
documents how to rotate it. The three at the top (the vault password, the automation key and
OpenBao's seal key) get procedures of their own.

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

**Response (2026-10-06): secrets as code now; ADR-0021 parked.** A tenant keeps its own secrets
encrypted in its repository and merges them into the settings file it pushes, which is how eds
already works; the tenant guide now says so. ADR-0021 stays Proposed as an optional service for a
tenant that needs rotation without a redeploy, per-workload revocation or a read audit, with each
workload's OpenBao credential pushed by the tenant now that ADR-0017 is gone. Nothing built in OpenBao
is undone.

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

**Response (2026-10-06): agreed; one sweep.** Each stale ADR's Current state gains a dated update
saying what is true now, with the earlier text kept below it as history, and the wrong claims on other
pages are corrected. Code comments are fixed in the next change to each file.

---

## Recommendations

### Principles

**A tier depends only on the tiers below it.** The four tiers above become the stated rebuild model,
on one runbook page, with the manual floor listed ([R6](#r6-four-rebuild-orders), [R9](#r9-the-manual-floor)).

**OpenBao stays, as a T2 service that holds copies.** It keeps issuing, encrypting, wrapping and
serving builds. *(Response: it stops serving builds; see [R4](#r4-build-credentials-from-openbao).)* Nothing in T1 needs it to build ([R4](#r4-build-credentials-from-openbao)), and nothing
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

**The first responses change four rows:** R4 becomes *builds use the vault only* rather than a
fallback; R3's page is *Build the Builder*; A3 gains HTTPS on the artifact server; A2 is deferred.

### Planned changes

**The responses are planned as nine change records, highest priority first** (2026-10-06):

| Change | Findings |
|---|---|
| [CHG-0035: Previously Exposed Credentials Checked and Rotated](/docs/changes/2026/0035-exposed-credentials/) | A1 |
| [CHG-0036: OpenBao's Keys From the Vault](/docs/changes/2026/0036-openbao-keys-from-the-vault/) | R1, T1 (the Transit key), R5, A4 |
| [CHG-0037: Substrate Builds Off OpenBao](/docs/changes/2026/0037-builds-off-openbao/) | R4, A5, R9 |
| [CHG-0038: The Reconcile Restores Everything](/docs/changes/2026/0038-reconcile-restores-everything/) | T1, T5, T2, R7, A6, A7 |
| [CHG-0039: Backup to an Attached SSD](/docs/changes/2026/0039-backup-to-an-attached-ssd/) | R2 |
| [CHG-0040: Device Secrets in Tenant Code](/docs/changes/2026/0040-device-secrets-in-tenant-code/) | R2, T2 (ADR-0033) |
| [CHG-0041: The Artifact Server Over HTTPS](/docs/changes/2026/0041-artifact-server-https/) | A3 |
| [CHG-0042: Two Undeclared VMs Moved Off the Management Hypervisor](/docs/changes/2026/0042-rehome-stray-vms/) | R9 |
| [CHG-0043: A Local Package Mirror](/docs/changes/2026/0043-local-package-mirror/) | R8 |

[CHG-0034: Device Certificates Through the Deevnet API](/docs/changes/2026/0034-device-certificates/),
planned before this review, builds on CHG-0036.

R3, R6, T3, T6, T7, A8 (the list), S1 and D1 needed only documentation, already done.
A2 and T4 are deferred.

---

## Open for the operator

**These are choices this review can inform but not make:**
- **Tenant secrets** ([S1](#s1-tenant-secrets)): code, an OpenBao copy, or both. *Answered,
  2026-10-06: code now, the OpenBao copy parked.*
- **Agent forwarding** ([A2](#a2-one-session-reaches-everything)): replace it with SSH certificates,
  or accept it as a recorded risk. *Deferred, 2026-10-06.*
- **The manual floor** ([R9](#r9-the-manual-floor)): which parts stay manual on purpose. *Answered,
  2026-10-06.*
- **Offline provisioning** ([R8](#r8-packages-from-the-internet)): mirror updates, or narrow the
  standard. *Answered, 2026-10-06: narrow now, mirror later.*
- **Tenant tokens** ([T4](#t4-tenant-tokens)): how to reissue and revoke. *Deferred, 2026-10-06.*
