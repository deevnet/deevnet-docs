---
title: "CHG-0018: The Central Log Store"
weight: 18
bookCollapseSection: true
---

# CHG-0018: The Central Log Store

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Not yet scheduled |
| **Site** | mobile |
| **Systems** | `dv02tob001v01` (resized; runs the store), `dv02hyp001p01` (hosts `tob`), every Fedora domain VM (`nms`, `sob`, `idn`, `prv`, `tob`, `msg`), `dv02hyp001p01` and `dv02hyp002p02` (ship logs), `dv02cor002p01`, `dv02acc001p01`, `dv02wap001p01` (send syslog) |
| **Automation** | `deevnet.mgmt` `site.yml`: `proxmox_vm` and `data_disk` (`--tags vms`), a new `victorialogs` role, and a new shipping role; `deevnet.builder` `artifacts` for the images. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. The riskiest thing is a vmauth user entry without both tenant headers: VictoriaLogs defaults to `(0, 0)`, so that entry fails open into substrate logs. No tenant token is issued in this change, which keeps that exposure theoretical until the follow-up. |
| **Related changes** | [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) (built `tob` empty), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) (why the containers use host networking; the forced-SSH pattern the follow-up reuses) |
| **Related incidents** | None |
| **Related runbooks** | [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/) |

---

## Summary

Every host keeps its own journal, and the core router's log buffer holds about fifty seconds.
[ADR-0022](/docs/architecture/decisions/0022-central-logging/) decides one log store on Platform:
VictoriaLogs behind vmauth on `dv02tob001v01`, partitioned by tenant index. This change builds the
store and ships the **substrate's** logs into partition `(0, 0)`.

Tenants get nothing from this change directly. Their tokens, the API issuing them, and the API
publishing tenant events into `(index, 1)` are the follow-up record. The store is built so that
follow-up adds vmauth users and nothing else.

## Goal

| | |
|---|---|
| `dv02tob001v01` | has the memory it needs and a data disk at `/srv`, and runs VictoriaLogs and vmauth as containers with host networking |
| VictoriaLogs HTTP | listens on `127.0.0.1` only; unreachable from any other host |
| vmauth | listens on HTTPS with a certificate from the site CA, and refuses any request without a known bearer token |
| Every Fedora domain VM | ships its journal to `(0, 0)` through vmauth with the substrate ingest token |
| Both hypervisors | ship to the syslog listener, which stores into `(0, 0)` |
| Core router, switch, AP | send syslog to the same listener |
| Syslog listener | reachable only from the addresses above, **measured** from one that is not |
| The operator | reads `(0, 0)` with the operator read token, from the Builder |
| The Builder | ships nothing (ADR-0022 §5) |

## Scope

**In scope:** resizing `tob`; the two images; the `victorialogs` role; the substrate ingest token
and operator read token in the inventory vault; journal shipping from the domain VMs; syslog from the
hypervisors and network devices; host firewall rules on `tob`.

**Out of scope:**
- tenant ingest and read tokens, and the API writing vmauth's configuration
- the API publishing tenant events
- Grafana (ADR-0024)
- a collector for third-party services' tenant events (ADR-0022 Q3, deferred)
- metrics (ADR-0023)

## What this is not

**It is not a new zone rule.** Every source already reaches Platform: `management -> platform`,
`trusted -> platform`, and the domain VMs on Platform itself. The only new filtering is firewalld on
`tob`.

**It is not authoritative data.** Losing the store loses history, not state (ADR-0022 §6). The
data disk gets no off-host copy.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A vmauth user without both headers reads or writes `(0, 0)` | vmauth config | every user entry sets `AccountID` and `ProjectID`; there is no `unauthorized_user` and no `default_url`; negative tests in Verification |
| The syslog port is reachable from a tenant | `tob` | host networking, so firewalld filters it (CHG-0016 showed a published port is not filtered); measured from a non-allowed source |
| A secret is written into a log | every shipping host | ADR-0022's rule: a secret never goes into a log. Spot-check the first day of `(0, 0)` for tokens and passwords |
| The store fills `/srv` | `tob` | `-retention.maxDiskUsagePercent` drops the oldest data first |
| Memory pressure on `tob` | `tob` | resized first; measured under the real ingest rate before Complete |
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

### Step 1: Resize `tob`

`tob` was built with 2 GB and a 32G OS disk before logging had requirements. Resizing it is approved.

In `host_vars/dv02tob001v01/vars.yml`, under `mgmt_vm`:

```yaml
  memory: 4096
  data_disk: { device: scsi1, size: 100, storage: local-lvm-big-thin, mount: /srv }
```

**Run:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags vms --limit dv02tob001v01
```

`proxmox_vm` attaches the disk with `create: regular` and `data_disk` formats and mounts it. **The
memory change stays pending on a running VM**: the role starts a stopped VM but never restarts a
running one. Restart `tob` once through the hypervisor's API. It runs nothing yet, so this is
harmless.

**Verify:**

1. `free -m` on `tob` shows about 4 GB.
2. `findmnt /srv` shows the `deevnet-data` XFS filesystem.
3. A rerun of the same command is `changed=0` for the VM.

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

### Step 3: Put the two tokens in the vault

The same pattern as the broker's `vault_vernemq_*` credentials (CHG-0015):

| Variable | File | Read by |
|---|---|---|
| `vault_victorialogs_substrate_ingest_token` | `group_vars/all/vault.yml` | `tob` (vmauth) and every shipping host |
| `vault_victorialogs_operator_read_token` | `group_vars/tenant_observability/vault.yml` (new) | `tob` (vmauth) |

1. Generate each token with `openssl rand -hex 32`, and write them into the decrypted files.
2. **Stop.** The operator runs `make vault && git add -u && git commit && git push`, then
   `make unvault` to continue. A new `vault.yml` needs `git add` by path, not `-u`.
3. Confirm the commit is on origin before Step 4 reads the tokens.

A token that exists only in a decrypted working tree is one `git restore` away from gone
(INC-0003).

**Verify:**
- `git log origin/main -- <both files>` shows the commit.
- `head -1` of each file is `$ANSIBLE_VAULT`.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Deploy the store

A new `victorialogs` role in `deevnet.mgmt`, and a play for `hosts: tenant_observability` in
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
- writes vmauth's `-auth.config` with exactly two users, each setting **both** headers:
  - substrate ingest: `/insert/.*` only, `AccountID: 0`, `ProjectID: 0`
  - operator read: `/select/.*` only, with one `url_map` entry per partition to read. In this
    change that is `(0, 0)` alone
- has no `unauthorized_user`
- reads both tokens from the inventory vault and **asserts they are present**. It never generates
  them, as the `vernemq` role doesn't generate its credentials (see Step 3)
- adds firewalld rules on `tob`:
  - vmauth's port from Management and Platform
  - the syslog port only from `10.20.99.1` (router), `10.20.99.10` (switch), `10.20.99.9` (AP),
    `10.20.99.21` and `10.20.99.22` (hypervisors)

**Run:**

```bash
ansible-playbook playbooks/site.yml --limit tenant_observability
```

**Verify:**

1. From the Builder, `curl` to `10.20.25.22:9428` fails. VictoriaLogs' HTTP port is not reachable.
2. A request to vmauth with no token gets `401`. A request with an unknown token gets `401`.
3. With the ingest token, write one JSON line. With the read token, read it back from `(0, 0)`.
4. The ingest token on `/select/` is refused. The read token on `/insert/` is refused.

**Undo:** [Undo Step 4](#undo-step-4)

### Step 5: Ship the Fedora domain VMs

A new shipping role on `management_plane` (not the Builder):
- installs `systemd-journal-remote`
- writes `/etc/systemd/journal-upload.conf` with `URL=https://<tob>/insert/journald` and
  `Header=Authorization: Bearer <substrate ingest token>`, taken from the vault. The file is root-only
- trusts the site CA
- enables `systemd-journal-upload`

The domain VMs run systemd 259, and `Header=` needs 258 or later. Assert the version rather than
assume it.

**Verify:** each host's `_HOSTNAME` appears in `(0, 0)`, and `systemctl status
systemd-journal-upload` is active with no retry loop.

**Undo:** disable the unit and remove the config.

### Step 6: Ship the hypervisors and network devices

- **Hypervisors:** Debian 12 has systemd 252, so there is no `Header=`. They use rsyslog forwarding
  over TLS to the syslog listener.
- **Core router:** the syslog target is set through the OPNsense API, with a readback, because
  rejected writes return HTTP 200.
- **Switch and AP:** the syslog server setting. The AP's is through the Omada controller.

Quote each device's options from its current manual here before the window. Don't write them from
memory.

**Verify:** a known event from each device appears in `(0, 0)` within a minute. For example, make a
config read on the router, or bounce a port that isn't in use on the switch.

**Undo:** restore each device's prior syslog setting, recorded before the change.

## Verification

The change is Complete only when all of these pass, measured from the network, not from Ansible:

1. **The syslog port is filtered.** From a source that is not on the allowed list (a tenant
   workload, and the Builder), connecting to the syslog port **fails**. From the router it succeeds.
   Before trusting that failure, remove the firewalld rule and watch the same test **succeed**
   (feedback: verify in the production context).
2. **Headers are overwritten.** From a tenant workload, send an ingest request with the substrate
   token absent and `AccountID: 0` / `ProjectID: 0` headers set. It is refused. With the substrate
   ingest token and forged `AccountID: 5`, the line lands in `(0, 0)`, not `(5, 0)`.
3. **An unmatched route is refused.** The read token on a path outside its `url_map` gets an error,
   not `(0, 0)` data.
4. **Every source is present.** Each domain VM, both hypervisors, the router, the switch and the AP
   have at least one line in `(0, 0)`. The Builder has none.
5. **Memory holds.** `tob`'s memory after 24 hours of real ingest is recorded here, with headroom.
6. **No secrets.** Spot-check the first day of `(0, 0)` for tokens, PSKs and passwords.

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

Remove the two variables, then vault, commit and push again. Do this only after Step 4 is undone.

### Undo Step 2

Remove the two `artifacts_podman_images` entries and the tarballs.

### Undo Step 1

Leave the data disk and memory in place: they cost nothing, and ADR-0023 wants `tob` too. To take
the disk back, remove `data_disk` from inventory, unmount it, and detach it by hand. This is a
deliberate one-off, because the role never removes a disk.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] **Tenant log tokens.** A new CHG:
  - the API issues each tenant an ingest and a read token at creation and on resupply
  - a forced-SSH writer on `tob` maintains vmauth's config (the CHG-0016 pattern:
    `roles/vernemq/tasks/writer.yml`, `internal/backend/brokerwriter/`)
  - provider fields for the two tokens
  - `max_concurrent_requests` on each tenant ingest user (ADR-0022 §6)
- [ ] **API tenant events.** The API writes each tenant event to `(0, 0)` and to `(index, 1)`.
- [ ] **Grafana**, under ADR-0024, with the `victoriametrics-logs-datasource` plugin.
- [ ] ADR-0022 moves to **Accepted** when this record is Complete.
