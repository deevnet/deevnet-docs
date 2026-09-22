---
title: "CHG-0018: The Central Log Store"
weight: 18
bookCollapseSection: true
---

# CHG-0018: The Central Log Store

| | |
|---|---|
| **Date** | 2026-09-21 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | **Complete 2026-09-22.** The store is built and verified (Steps 1–4). Steps 5 and 6 were **withdrawn** on 2026-09-22 and move to later changes (see *Scope change*). |
| **Window** | 2026-09-21 19:42 to 2026-09-22 08:09 |
| **Site** | mobile |
| **Systems** | `dv02tob001v01` and `dv02sob001v01` (destroyed), `dv02obs001v01` (new; runs the store), `dv02col001v01` (new; ADR-0023's collector, empty here), `dv02hyp001p01` (hosts all four), every Fedora domain VM (`nms`, `col`, `idn`, `prv`, `obs`, `msg`), `dv02hyp001p01` and `dv02hyp002p02` (ship logs), `dv02cor002p01`, `dv02acc001p01`, `dv02wap001p01` (send syslog) |
| **Automation** | `deevnet.mgmt` `site.yml`: `proxmox_vm` and `data_disk` (`--tags vms`), a new `victorialogs` role, and a new shipping role; `deevnet.builder` `artifacts` for the images. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. The riskiest thing is a vmauth user entry without both tenant headers: VictoriaLogs defaults to `(0, 0)`, so that entry fails open into substrate logs. No tenant token is issued in this change, which keeps that exposure theoretical until the follow-up. |
| **Related changes** | [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) (built `tob` and `sob` empty), [CHG-0003](/docs/changes/2026/0003-host-rename/) (the reservation and record hazards), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) (why the containers use host networking; the forced-SSH pattern the follow-up reuses) |
| **Related incidents** | [INC-0004](/docs/incidents/2026/0004-core-router-lost/): the core router stopped answering at about 20:14, during Step 4 |
| **Related runbooks** | [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/) |

---

## Summary

Every host keeps its own journal, and the core router's log buffer holds about fifty seconds.
[ADR-0022](/docs/architecture/decisions/0022-central-logging/) decides one log store on Platform:
VictoriaLogs behind vmauth on `dv02obs001v01`, which replaces `dv02tob001v01`, partitioned by tenant index. This change builds the
store and ships the **substrate's** logs into partition `(0, 0)`.

Tenants get nothing from this change directly. Their tokens, the API issuing them, and the API
publishing tenant events into `(index, 1)` are the follow-up record. The store is built so that
follow-up adds vmauth users and nothing else.

## Scope change, 2026-09-22

**This change now builds the central log store and stops there.** The operator withdrew Steps 5 and
6, which ship logs from existing hosts, on 2026-09-22:

- **Making existing substrate hosts write to the store is later work, in its own changes.** That
  covers journal shipping from the domain VMs, and syslog from the hypervisors, switch and AP.
- **The core router sends nothing to the store until its LAN NIC is stable.**
  [INC-0004](/docs/incidents/2026/0004-core-router-lost/) found repeated `re0` watchdog timeouts, and
  adding traffic across that NIC is not wanted until they stop.

The plan below is left as it was written, as the template requires. The Goal rows and Steps that the
decision withdrew are marked, and what did happen is under *Outcome*.

## Goal

| | |
|---|---|
| `dv02obs001v01` | has the memory it needs and a data disk at `/srv`, and runs VictoriaLogs and vmauth as containers with host networking |
| VictoriaLogs HTTP | listens on `127.0.0.1` only; unreachable from any other host |
| vmauth | listens on HTTPS with a certificate from the site CA, and refuses any request without a known bearer token |
| Every Fedora domain VM | ships its journal to `(0, 0)` through vmauth with its **own** ingest token. *Withdrawn: a later change.* The store holds a vmauth user and token for each already. |
| Both hypervisors | ship to the syslog listener, which stores into `(0, 0)`. *Withdrawn: a later change.* |
| Core router, switch, AP | send syslog to the same listener. *Withdrawn: a later change; the router only once its NIC is stable.* |
| Syslog listener | reachable only from the addresses above, **measured** from one that is not |
| The operator | reads `(0, 0)` with the operator read token, from the Builder |
| The Builder | ships nothing (ADR-0022 §5) |

## Scope

**In scope:** replacing `tob` and `sob` with `obs` and `col`; the two images; the `victorialogs` role; a per-host ingest token for each
`log_shippers` host and the operator read token, in the inventory vault; journal shipping from the domain VMs; syslog from the
hypervisors and network devices; host firewall rules on `obs`.

**Out of scope:**
- tenant ingest and read tokens, and the API writing vmauth's configuration
- the API publishing tenant events
- Grafana (ADR-0024)
- a collector for third-party services' tenant events (ADR-0022 Q3, deferred)
- metrics (ADR-0023)

## What this is not

**It is not a new zone rule.** Every source already reaches Platform: `management -> platform`,
`trusted -> platform`, and the domain VMs on Platform itself. The only new filtering is firewalld on
`obs`.

**It is not authoritative data.** Losing the store loses history, not state (ADR-0022 §6). The
data disk gets no off-host copy.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A vmauth user without both headers reads or writes `(0, 0)` | vmauth config | every user entry sets `AccountID` and `ProjectID`; there is no `unauthorized_user` and no `default_url`; negative tests in Verification |
| The syslog port is reachable from a tenant | `obs` | host networking, so firewalld filters it (CHG-0016 showed a published port is not filtered); measured from a non-allowed source |
| A secret is written into a log | every shipping host | ADR-0022's rule: a secret never goes into a log. Spot-check the first day of `(0, 0)` for tokens and passwords |
| The store fills `/srv` | `obs` | `-retention.maxDiskUsagePercent` drops the oldest data first |
| Memory pressure on `obs` | `obs` | built at 4 GB; measured under the real ingest rate before Complete |
| A network device's syslog change misbehaves | router, switch, AP | each is a single setting with a noted prior value; the router's is applied through its API with a readback |

## Prerequisites

- [ ] Inventory on a branch cut from `main`, vault decrypted, collections built
- [ ] The operator is present to run `make vault` and push at Step 3. The vault password is
  human-held (ADR-0016 §2)
- [ ] Free space on `local-lvm-big-thin` on `dv02hyp001p01` for the data disk: `lvs` on the hypervisor
- [ ] `dv02hyp002p02`'s systemd version read (only `dv02hyp001p01`'s is known: 252)
- [ ] `dv02hyp002p02`'s host key in the Builder's `known_hosts` (verification failed on 2026-09-21; do not bypass it)
- [ ] Each network device's syslog options quoted from its **current** manual into this record before Step 6

## Procedure

### Step 1: Replace `tob` and `sob` with `obs` and `col`

ADR-0022 put every log in one store, so the audience split in the old names no longer exists (naming
§3.4). Both VMs are empty, so they are **replaced, not renamed**. A rename would mean following
`runbook/lifecycle/host-rename`. A fresh build at the right size is simpler and leaves nothing
behind.

| Old | New | Role | Address (kept) | Sizing |
|---|---|---|---|---|
| `dv02tob001v01` | `dv02obs001v01` | observability store | `10.20.25.22`, Platform, static, no DHCP | 4 GB, data disk 100G at `/srv` |
| `dv02sob001v01` | `dv02col001v01` | collector (ADR-0023) | `10.20.99.41`, management, **DHCP reservation** | as `sob`, 2 GB |

Each new VM keeps its predecessor's address, so the old VM must be gone **before** the new one boots.

**Inventory, on one branch:**
- `hosts.yml`: `tenant_observability` becomes **`observability_store`**, holding `dv02obs001v01`.
  `substrate_observability` becomes **`observability_collectors`**, holding `dv02col001v01`. The
  two are swapped in `management_plane` as well.
- `host_vars/dv02obs001v01/vars.yml` and `host_vars/dv02col001v01/vars.yml` are copied from the old
  files, with `env.role` updated. `obs` gets `memory: 4096` and
  `data_disk: { device: scsi1, size: 100, storage: local-lvm-big-thin, mount: /srv }`.
- The old `host_vars` directories are deleted.
- `ansible-playbook playbooks/vm-identity.yml -e vm_identity_assign=true` allocates new VMIDs and
  MACs, and writes each `identity.yml`. VMIDs 206 and 207 are **not** reused while the old VMs exist.

**The two hazards, both from the host rename (CHG-0003):**
1. **`col` keeps a DHCP-reserved address under a new MAC.** `opnsense_dhcp` reconciles by MAC and
   does not prune. **Delete `sob`'s reservation on the core router first**, then run `opnsense_dhcp`
   to add `col`'s, before `col` is built. Otherwise Kea holds two reservations for one address, and
   `col` boots on a pool lease.
2. **DNS A records for the old names stay unless removed.** Delete the `dv02tob001v01` and
   `dv02sob001v01` records by hand, since `dns_delete_unmanaged` is off by default. Then run
   `opnsense_dns` for the new names.

**Run, in order:**

1. Destroy `dv02tob001v01` and `dv02sob001v01` on `dv02hyp001p01`. Neither has data.
2. Remove `sob`'s reservation and both old A records, then run `opnsense_dhcp` and `opnsense_dns`
   for the new hosts.
3. Build the new VMs:

   ```bash
   cd ansible-collection-deevnet.mgmt
   ansible-playbook playbooks/site.yml --tags vms --limit dv02obs001v01,dv02col001v01
   ```

**Verify:**

1. `obs`: `free -m` shows about 4 GB, and `findmnt /srv` shows the `deevnet-data` XFS filesystem.
2. Each new VM answers on its address and resolves by its new name.
3. The old names no longer resolve. Kea holds exactly one reservation for `10.20.99.41`, and it is
   `col`'s MAC.
4. `vm-identity.yml` (audit mode) passes.
5. A rerun of the build is `changed=0`.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: Stage the images

Add both images to `artifacts_podman_images` in `group_vars/artifact_servers.yml`, pinned like
`pdns-auth`:

| Image | Tag |
|---|---|
| `docker.io/victoriametrics/victoria-logs` | `v1.52.0` |
| `docker.io/victoriametrics/vmauth` | `v1.152.0` |

Both tags were confirmed on Docker Hub on 2026-09-21. Re-check for newer patch releases before the
window.

**Run:** the `deevnet.builder` `artifacts` play.

**Verify:** both tarballs are under `/srv/deevnet-http/container-images/`.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Put the tokens in the vault

The same pattern as the broker's `vault_vernemq_*` credentials (CHG-0015).

**One ingest token per shipping host, not one shared token.** A shared token would sit in plaintext
on six hosts, so root on any one of them could write as all of them, and the only revocation would
be rotating it everywhere. Per-host tokens make each host a separate vmauth user. That means one
host can be revoked alone, and a forged line can be traced to the token that sent it.

A new inventory group, **`log_shippers`**, lists the hosts that ship by journal-upload: the six
Fedora domain VMs (`nms`, `col`, `idn`, `prv`, `obs`, `msg`). The Builder is deliberately absent
(ADR-0022 §5). The hypervisors are absent too, because they ship by syslog and hold no token.

| Variable | File | Read by |
|---|---|---|
| `vault_log_ingest_token` | `host_vars/<host>/vault.yml`, one per `log_shippers` host (new files where absent) | that host, and `obs` (vmauth) |
| `vault_victorialogs_operator_read_token` | `group_vars/observability_store/vault.yml` (new) | `obs` (vmauth) |

1. Generate each token with `openssl rand -hex 32`, and write them into the decrypted files. That
   is seven tokens.
2. **Stop.** The operator runs `make vault`, then `git add` **each file by path**, because new
   `vault.yml` files are untracked and `-u` misses them. Then commit and push, and `make unvault`
   to continue.
3. Confirm the commit is on origin before Step 4 reads the tokens.

A token that exists only in a decrypted working tree is one `git restore` away from gone
(INC-0003).

**Verify:**
- `git log origin/main -- <every file>` shows the commit.
- `head -1` of each file is `$ANSIBLE_VAULT`.
- The seven tokens are distinct.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Deploy the store

A new `victorialogs` role in `deevnet.mgmt`, and a play for `hosts: observability_store` in
`site.yml` that replaces the "Observability tooling is not chosen yet" comment. The role:

- runs two `podman_service` containers with `podman_service_network: host`, which is **required**,
  not a style choice (ADR-0022 §5, CHG-0016)
- runs VictoriaLogs with:
  - `-httpListenAddr=127.0.0.1:9428`
  - data on `/srv/victorialogs`
  - `-retentionPeriod` (proposed `30d`) and `-retention.maxDiskUsagePercent` (proposed `80`)
  - `-syslog.listenAddr.tcp` with `-syslog.tls` and `-syslog.tenantID.tcp=0:0`
  - a UDP listener only if a device can't send over TCP; if so, record which device and why
- runs vmauth on the host's HTTPS port with a certificate issued from the site CA, following the
  pattern of `roles/vernemq/tasks/openbao.yml`
- writes vmauth's `-auth.config`, in which every user sets **both** headers:
  - one ingest user per `log_shippers` host, named after the host, holding that host's
    `vault_log_ingest_token`: `/insert/.*` only, `AccountID: 0`, `ProjectID: 0`
  - one operator read user: `/select/.*` only, with one `url_map` entry per partition to read. In
    this change that is `(0, 0)` alone
- has no `unauthorized_user`
- reads every token from the inventory vault (through `hostvars` for the shippers) and **asserts
  each one is present and that no two are equal**. It never generates them, as the `vernemq` role
  doesn't generate its credentials (see Step 3)
- adds firewalld rules on `obs`:
  - vmauth's port from Management and Platform
  - the syslog port only from `10.20.99.1` (router), `10.20.99.10` (switch), `10.20.99.9` (AP),
    `10.20.99.21` and `10.20.99.22` (hypervisors)

**Run:**

```bash
ansible-playbook playbooks/site.yml --limit observability_store
```

**Verify:**

1. From the Builder, `curl` to `10.20.25.22:9428` fails. VictoriaLogs' HTTP port is not reachable.
2. A request to vmauth with no token gets `401`. A request with an unknown token gets `401`.
3. With the ingest token, write one JSON line. With the read token, read it back from `(0, 0)`.
4. The ingest token on `/select/` is refused. The read token on `/insert/` is refused.

**Undo:** [Undo Step 4](#undo-step-4)

### Step 5: Ship the Fedora domain VMs

> **Withdrawn from this change on 2026-09-22.** It was trialled on one host before the decision. See
> *Outcome*. The role is kept on branch `journal-upload-wip` of the mgmt collection for the later change.

A new shipping role on `log_shippers`:
- installs `systemd-journal-remote`
- configures `URL=https://<obs>/insert/journald`, plus `Header=Authorization: Bearer <this host's
  token>`, taken from the vault
- trusts the site CA
- enables `systemd-journal-upload`

The domain VMs run systemd 259, and `Header=` needs 258 or later. Assert the version rather than
assume it.

**How the token is kept on the host is unresolved. Settle it before writing the role.** It depends on
which user `systemd-journal-upload.service` runs as on Fedora 44, and that has not been checked.
- If it runs as root, a `0600 root` config file is enough.
- If it runs as its own unprivileged or dynamic user, a `0600 root` file breaks the service, and the
  stock `0644` exposes the token to every local user. In that case the token goes in through
  systemd's credential passing (`LoadCredential=` in a drop-in), provided `journal-upload` can take
  its header from a credential. If it can't, use a `0640` file owned by the service's group, if it
  has a static one.

Read the unit file from the Fedora 44 package, and record what it says here before choosing. Do not
decide from memory.

**Store and forward, not a switch-over.** The local journal stays exactly as it is and is still the
first copy. `journal-upload` reads from it and records how far it got in a state file, so it can
resume from that point after `obs` or the network has been down. That resume behaviour should be
confirmed on the F44 unit (`--save-state`), not assumed. Nothing on the host changes how it logs, so
no later change is needed to "cut over". The one loss window is local journal rotation: an outage
longer than the journal's retention loses the lines rotated out before upload.

**Verify:**
- Each host's `_HOSTNAME` appears in `(0, 0)`, and `systemctl status systemd-journal-upload` is
  active with no retry loop.
- A non-root user on one host cannot read that host's token.
- Stop vmauth for five minutes, then start it. The lines from that gap arrive, and none are
  duplicated.

**Undo:** disable the unit and remove the config.

### Step 6: Ship the hypervisors and network devices

> **Withdrawn from this change on 2026-09-22, and never started.** The core router is excluded until
> INC-0004's NIC fault is resolved.

- **Hypervisors:** Debian 12 has systemd 252, so there is no `Header=`. They use rsyslog forwarding
  over TLS to the syslog listener, with a **disk-assisted action queue**. That gives them the same
  store and forward as the VMs: rsyslog's default queue is in memory, and it is lost if rsyslog
  restarts during an outage.
- **Network devices** have no buffer of their own worth relying on (the router's holds about fifty
  seconds). Lines they send while `obs` is down are lost. That is accepted: it is no worse than today.
- **Core router:** the syslog target is set through the OPNsense API, with a readback, because
  rejected writes return HTTP 200.
- **Switch and AP:** the syslog server setting. The AP's is through the Omada controller.

Quote each device's options from its current manual here before the window. Don't write them from
memory.

**Verify:** a known event from each device appears in `(0, 0)` within a minute. For example, make a
config read on the router, or bounce a port that isn't in use on the switch.

**Undo:** restore each device's prior syslog setting, recorded before the change.

## Verification

The change is Complete only when all of these pass, measured from the network, not from Ansible.
*Results from 2026-09-21/22 are marked on each item; items 3 and 5 went with Steps 5 and 6.*

1. **The syslog port is filtered.** From a source that is not on the allowed list (a tenant
   workload, and the Builder), connecting to the syslog port **fails**. From the router it succeeds.
   Before trusting that failure, remove the firewalld rule and watch the same test **succeed**
   (feedback: verify in the production context).
   **Result: passed, with a different control.** From the Builder (not listed) the connection is
   refused, `No route to host` from firewalld's reject, while vmauth's 8427 answers the Builder
   normally. From `dv02hyp001p01` (listed) it connects, and `obs`'s TLS certificate is served. The
   same port and listener behave differently only by source, which is the control the rule-removal
   step was meant to supply, so the rule was not removed. The router was deliberately not tested (INC-0004), and
   neither was a tenant workload.
2. **Headers are overwritten.** From a tenant workload, send an ingest request with no token
   and `AccountID: 0` / `ProjectID: 0` headers set. It is refused. With one host's ingest token and
   a forged `AccountID: 5`, the line lands in `(0, 0)`, not `(5, 0)`.
   **Result: passed, from the Builder rather than a tenant workload.** With no token: 401 on
   `/select` and `/insert`, and 401 for an unknown token. A forged `AccountID: 5` with `msg`'s token
   landed in `(0, 0)`. **Control:** querying VictoriaLogs directly on `obs`'s loopback, bypassing
   vmauth, gives 2 marker lines for `AccountID=0` and 0 for `AccountID=5`, and `tenant_ids` lists only
   `(0, 0)`. So the backend would have honoured the header, and vmauth replaced it.
3. **Per-host revocation works.** Remove one host's vmauth user. That host's uploads are refused,
   and every other host keeps shipping. Restore the user, and the host's backlog arrives.
   *Withdrawn with Step 5.*
4. **An unmatched route is refused.** The read token on a path outside its `url_map` gets an error,
   not `(0, 0)` data.
   **Result: passed.** 400 `missing route` for the read token on `/-/reload`, the ingest token on
   `/select/` and `/metrics`, and the read token on `/insert/`. VictoriaLogs `:9428` and vmauth's
   internal `:8426` do not answer off-host.
5. **Every source is present.** Each domain VM, both hypervisors, the router, the switch and the AP
   have at least one line in `(0, 0)`. The Builder has none.
   *Withdrawn with Steps 5 and 6.*
6. **Memory holds.** `obs`'s memory after 24 hours of real ingest is recorded here, with headroom.
   **Result, with one host's ingest rather than the site's:** after about 370,000 lines (`nms`'s whole
   journal plus its overnight trickle), VictoriaLogs used 115 MB and vmauth 7 MB of the 4 GB, and the
   data took 32 MB of the 100 GB `/srv`. Re-measure when shipping is turned on.
7. **No secrets.** Spot-check the first day of `(0, 0)` for tokens, PSKs and passwords.
   **Result: passed, after the first check turned out to be broken.** Across the 370,952 lines in
   `(0, 0)`, none of the seven tokens appears, as a phrase or a substring. The 27 `password` matches are
   all systemd unit names (`systemd-ask-password-*`). The two `key` matches are man-page `grep`
   commands. The first pass returned zero for everything, including terms certain to be present,
   because its filter syntax was wrong. It was redone with positive controls for the phrase,
   substring and case-insensitive filters, and each of those controls returned hits.

## Undo

Steps are backed out in reverse order. Nothing depends on the store yet, so every step can be
undone.

### Undo Step 6

Restore each device's recorded prior syslog setting. Remove the rsyslog forwarding file from the
hypervisors.

### Undo Step 5

`systemctl disable --now systemd-journal-upload` and remove the config.

### Undo Step 4

Stop and remove both containers, the firewalld rules, and the `site.yml` play. Keep the vaulted
tokens until the record is closed.

### Undo Step 3

Remove the tokens and the `log_shippers` group, then vault, commit and push again. Do this only after Step 4 is undone.

### Undo Step 2

Remove the two `artifacts_podman_images` entries and the tarballs.

### Undo Step 1

The old VMs held nothing, so there is nothing to restore, only names. To go back, destroy the new
VMs, restore the old inventory from git, and rebuild `tob` and `sob` the same way, reversing the
reservation and records. Up to Step 4, going forward is always cheaper than going back.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 2026-09-21 19:42:51, 19:43:07 | 1 | The operator destroyed `dv02sob001v01` (VMID 206) and `dv02tob001v01` (VMID 207) on `dv02hyp001p01`. Both were checked beforehand, read-only: no containers, no services beyond the base OS, nothing in `/srv`. |
| 2026-09-21 19:43 | 1 | `vm-identity.yml` audit: 206 and 207 free on both hypervisors. Allocation gave `dv02col001v01` 206 (`02:de:20:00:00:ce`) and `dv02obs001v01` 207 (`02:de:20:00:00:cf`). |
| 2026-09-21 | 1, 3 | Inventory [#47](https://github.com/deevnet/ansible-inventory-deevnet/pull/47): the groups become `observability_store` and `observability_collectors`, `log_shippers` is added, the host_vars move to the new names, and `obs` gets 4 GB and a 100G `/srv`. Seven tokens were generated straight into new vault files and never printed; all seven are distinct. The operator ran `make vault`; the commit was pushed, and origin was checked to hold ciphertext for every new file. |
| 2026-09-21 ~19:50 | 1 | `opnsense_dns` added the `obs` and `col` A records. The run with `dns_delete_unmanaged=true`, to remove the two stale records, was **blocked by the session's permission classifier** and is left to the operator. `opnsense_dhcp` updated `col`'s reservation in place, on the unchanged MAC. It also rewrote 14 other reservations with identical values, the known idempotency defect. |
| 2026-09-21 19:53 | 1 | Both VMs built with `--tags vms`. `obs` has 4 GB and `/srv` on the `deevnet-data` XFS disk; `col` has 2 GB. Both came up on their addresses, and the `vm-identity` audit passes. A rerun is **not** `changed=0`: `proxmox_kvm` with `update: true` reports changed every time, although the readback assertions pass. |
| 2026-09-21 19:55–20:04 | 2 | Both images staged. The newest releases were re-checked on GitHub, so the pins are current. The command used was the builder collection's whole `site.yml`; see Departures. |
| 2026-09-21 ~20:10 | 4 | The log store's first deploy. It **stalled at 20:14:20** while pushing the vmauth image, because the core router hung ([INC-0004](/docs/incidents/2026/0004-core-router-lost/)). VictoriaLogs was running; vmauth and the firewall rules were not yet in place. |
| 2026-09-21 20:44 | 4 | Deploy re-run after the router's power-cycle; it completed. The role's own check, that a request with no token is refused, passed. Then Verification 1, 2 and 4 were run from the Builder: see *Verification*. |
| 2026-09-21 20:50–21:19 | 5 (trial) | Journal shipping trialled on `dv02nms001v01` only. Three defects were found and fixed in the role: an SELinux denial, a client-certificate default, and the token's file permissions (see Departures). By 21:19 it was uploading. |
| 2026-09-21 21:19 → 2026-09-22 07:5x | 5 (trial) | `nms` shipped **194,077 lines**, its full journal backfill, then its live journal. It restarted 337 times overnight because the router kept dropping. That retry log became evidence for INC-0004. |
| 2026-09-22 ~07:55 | — | **Scope change** (see above). On `nms`, journal-upload was stopped and disabled, and its token drop-in was removed. The package `systemd-journal-remote`, the site CA at `/etc/pki/deevnet/site-ca.pem` and the SELinux label on 8427 were left in place; each is harmless. What `nms` shipped stays in the store. |
| 2026-09-22 | 4 | Verification 6 and 7 run; see *Verification*. The store is complete. |
| 2026-09-22, before 08:09 | 1 | The operator removed the two stale A records with `opnsense_dns` and `dns_delete_unmanaged=true`, the run the session's classifier had blocked. Checked at 08:09:03 against the router's resolver: `dv02tob001v01` and `dv02sob001v01` no longer resolve; `dv02obs001v01` → `10.20.25.22` and `dv02col001v01` → `10.20.99.41` do. **Step 1 is complete.** |
| 2026-09-22 08:09 | — | The operator ran `make vault`. Every `vault.yml` was checked to begin with `$ANSIBLE_VAULT`, and the 17 re-encrypted files were committed (inventory #48). **Change complete.** ADR-0022 stays **Proposed** until a shipping change completes, by the operator's decision. |
### Departures from the plan

- **The VMs were destroyed before the new inventory was merged.** The plan said to wait, so that a
  `site.yml` run couldn't rebuild `tob` and `sob` from the old inventory. The operator chose to go
  first, as the only person running playbooks.
- **The VMIDs were reused, which removed a hazard.** The plan expected new VMIDs and warned that
  `col` would carry a new MAC onto a DHCP-reserved address. With the old VMs gone first, the
  allocator gave out 206 and 207 again, in the same order. The MAC is a function of the VMID, so
  `col` has `sob`'s MAC, and the existing reservation for `10.20.99.41` already matches. The old
  names' DNS A records still need removing.
- **Step 3 ran before Step 2.** The tokens don't depend on the images.
- **The new vault files were created `664` despite `umask 077`.** They were set to `600` before any
  content was committed. They were plaintext on the Builder only until `make vault`.
- **Step 2 ran the builder collection's whole `site.yml`, not only its artifacts play.** It was
  limited to `artifact_servers`, which contains the Builder `dv00bld001p01` **and** the test builder
  `dv02bld001v01`. So every play matching either host ran:
  - **`dv00bld001p01`**: 14 changes. They include `enp4s0` re-applied three times, each a reconnect of
    under a second, and libvirtd enabled.
  - **`dv02bld001v01`**: 31 changes. It was built out as an artifact server, with nginx, firewall and
    SELinux changes and downloads, and its hostname was set. The run failed there with ENOSPC on a temp
    file.

  The operator confirmed that `dv02bld001v01` is a test builder to be removed. A builder play is to be
  limited to `dv00bld001p01` and run by tag.
- **The same mistake, smaller, in the Step 5 trial.** `--limit dv02nms001v01` also ran the Omada
  controller play on `nms`. It changed nothing. The log store and shipping plays now carry the tags
  `log-store` and `log-shipping`, so they run on their own.
- **Step 4 was interrupted by INC-0004** and completed on the re-run. The half-deployed state it left
  was safe: vmauth absent, and the syslog port not yet opened.
- **Steps 5 and 6 were withdrawn** (see *Scope change*). **Step 5 was trialled on one host before
  that**, and the trial found three things the later change needs:
  - **SELinux denies the connection.** `systemd_journal_upload_t` may not connect to an unlabelled
    port (`unreserved_port_t`). Labelling 8427 as `journal_remote_port_t` on the shipping host fixes it,
    and SELinux stays enforcing. The AVC is logged under `comm="systemd-journal"`, which is truncated,
    so a grep for `journal-upload` misses it.
  - **It demands a client certificate** unless `ServerKeyFile=-` and `ServerCertificateFile=-` are set,
    per systemd-journal-upload(8).
  - **The token has to be readable by the service.** The Fedora 44 unit is `DynamicUser=yes`, so a
    root-only drop-in can't be read. journal-upload cannot take `Header=` from a credential. The drop-in
    is therefore `0640 root:systemd-journal`, a group with no human members on these hosts.
- **Verification ran from the Builder, not from a tenant workload** (items 1 and 2). A tenant-side run
  belongs with the tenant-token change, when tenants first hold a credential for the store.

## Follow-ups

- [ ] **Tenant log tokens.** A new CHG:
  - the API issues each tenant an ingest and a read token at creation and on resupply
  - a forced-SSH writer on `obs` maintains vmauth's config (the CHG-0016 pattern:
    `roles/vernemq/tasks/writer.yml`, `internal/backend/brokerwriter/`)
  - provider fields for the two tokens
  - `max_concurrent_requests` on each tenant ingest user (ADR-0022 §6)
- [ ] **API tenant events.** The API writes each tenant event to `(0, 0)` and to `(index, 1)`.
- [ ] **Grafana**, under ADR-0024, with the `victoriametrics-logs-datasource` plugin.
- [x] **Remove the two stale A records** (`dv02tob001v01`, `dv02sob001v01`). Done by the operator on
  2026-09-22 and verified; see *Outcome*.
- [ ] **Journal shipping from the domain VMs**, a new change, from branch `journal-upload-wip`:
  - decide how to handle the first run's full-journal backfill, which is heavy traffic across the
    router's `re0`
  - roll out one host at a time
  - never put a secret on an **ad-hoc** Ansible command line: `Invoked with` is journaled verbatim
    and would reach the store. The roles use `no_log`.
- [ ] **Syslog from the hypervisors, switch and AP**, a new change: rsyslog with a disk-assisted queue
  on the hypervisors, and each device's options quoted from its current manual.
- [ ] **Syslog from the core router**, only after INC-0004's NIC fault is resolved. That includes the
  move to Realtek's vendor driver, which is INC-0004's follow-up.
- [ ] `proxmox_vm`: the hardware task reports changed on every run (`proxmox_kvm` `update: true`).
- [ ] Remove the test builders `dv02bld001v01` and `dv02bld002v01` (the operator's follow-up).
- [x] **ADR-0022 acceptance.** Decided on 2026-09-22: it stays **Proposed until a shipping change is
  complete**. A store that nothing writes to has not yet shown the design works.
