---
title: "CHG-0015: The VerneMQ Broker"
weight: 15
---

# CHG-0015: The VerneMQ Broker

| | |
|---|---|
| **Date** | 2026-09-20 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-09-20.** VerneMQ 2.2.0 serves TLS on `dv02msg001v01`. It took three runs: the first two failed on the role's own preflight, both times because inventory had not been given something the role asserts on. |
| **Window** | 2026-09-20 |
| **Site** | mobile |
| **Systems** | `dv02msg001v01` (VerneMQ and its PostgreSQL auth database); `dv02mqt001v01` and the `mosquitto` role are superseded |
| **Automation** | `deevnet.mgmt` `playbooks/site.yml --limit mqtt_brokers`, new role `vernemq`; image from the new `deevnet-container-image-factory` |
| **Risk** | Low — a new service on a VM that is built and empty. Nothing existing is rewritten. The broker has never served a client, so there is nothing to interrupt. |
| **Related changes** | [CHG-0014](/docs/changes/2026/0014-tenant-device-registry/) (the device registry a broker account references), [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) (built the messaging VM), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (the zone policy this runs under) |
| **Related incidents** | [INC-0003](/docs/policies/incident-management/) — its lesson is built into the certificate logic |
| **Related runbooks** | None yet |

---

## Summary

There is no broker. [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §8 chose VerneMQ
in review on 2026-09-14 and nothing has been built since: `mqtt_brokers` holds no host, the
`mosquitto` role it supersedes serves nothing, and every IoT resource that depends on a broker is
blocked behind it. This builds it.

It is also what actually blocks the EdS vertical. The application's path is
`cover image → lightd → palette → lightd → mqtt01 → LP stand`, which is publish/subscribe, and
ADR-0020 §1 keeps MQTT preferred wherever pub/sub fits.

## Goal

| | |
|---|---|
| `dv02msg001v01` | runs VerneMQ and a PostgreSQL auth database, as containers |
| The broker | serves **MQTT over TLS only**, from a site-CA certificate |
| Accounts | come from the database; the broker's credential on it is read-only |
| A tenant | is confined to its own topic prefix, `<tenant>/…` |
| `mosquitto` | is retired from the play |

## What this is not

**It does not provision accounts.** The API writing `deevnet_iot_broker_account` into this database
is CHG-0016, and so is the narrow `platform -> iot_backend` rule it needs — which ADR-0012 §7
promised would be declared when the API was built and never was.

**It is not a cluster.** ADR-0012 §8 requires the broker be *able* to cluster later, and this does
not foreclose it, but a second node is a change record of its own. See the node-name note below.

**It does not retire the inventory ACLs.** `lightd` and `lp-stand-01` stay in
`group_vars/mqtt_brokers.yml` as ADR-0010 debt until the API can issue their accounts.

## Why the image is built from source

VerneMQ's 2.2.0 release notes state: *"VerneMQ binary software distribution packages and Docker
images are covered by the VerneMQ EULA."* `LICENSE.txt` at the tag is Apache-2.0, so the source is
ours to use and the binaries are not. That is why `deevnet-container-image-factory` exists — a
third case the estate had not met, where the build recipe is the artifact and needs a commit
history of its own.

Confirmed on the built image, which is what ADR-0012's *To confirm when building* asks for: the
release carries `vmq_diversity 2.2.0`, `epgsql 4.7.1`, `bcrypt 1.2.2` and `vmq_swc 2.2.0`.

## Procedure

1. **Stage the image.** In `deevnet-container-image-factory`: `make stage IMAGE=vernemq`.
2. **Vault the secrets** — `vault_vernemq_cookie` and the three database passwords. The cookie is
   the only thing authenticating Erlang distribution, so the stock `vmq` is not acceptable even on
   one node.
3. **Add `dv02msg001v01` to `mqtt_brokers`**, and publish the `mqtt` name. This is the deploy step:
   the group is held empty until the secrets exist, for the reason `openbao`'s was.
4. `ansible-playbook playbooks/site.yml --limit mqtt_brokers`
5. **Verify**, below.
6. **Swap the reachability target.** `firewall.yml` currently probes port 22 on this host as a
   stand-in for 1883 "until the broker exists". It exists now, and the port is **8883**, not 1883.

## Verification

Run `images/vernemq/smoke-test.sh` from the image factory for the behavioral half; it stands the
broker up against a throwaway database and checks all of this. On the real host:

| Check | Expect |
|---|---|
| `vmq-admin listener show` | one `mqtts` listener, `running`. **Not** `vernemq ping` — see below |
| A client with an account | connects over TLS and publishes in its own prefix |
| A wrong password | `Connection Refused: bad user name or password` |
| A right password from a different client id | refused — the account key is `(mountpoint, client_id, username)` |
| Subscribe to `#` or another tenant's prefix | denied |
| A cross-tenant publish | never reaches a subscriber on the other side |
| The broker's database role | refused a `DELETE` on `vmq_auth_acl` |

## What testing this changed

Everything here was found by running the real broker, and each one cost time.

**Readiness is the listener, not the node.** `vernemq ping` answers `pong` well before the `mqtts`
acceptor binds. Worse, a listener that ranch *refused* leaves a node that pings happily and serves
nothing — and the refusal is written only to `log/error.log` while the console stays clean. The
role waits on `vmq-admin listener show`, and its failure message points at that file.

**An SSL listener requires `cafile`** even when it asks for no client certificate. Without it ranch
refuses the listener with `Invalid TLS option: {cacertfile,undefined}` and the port never opens.

**The node name is not the VM's address**, though that is the obvious choice for a node that must
cluster one day. The broker runs in a container on a private network where that address does not
exist, so it yields a broker that serves MQTT perfectly while every `vmq-admin` call answers *"not
responding to pings"*. `vmq-admin cluster` exposes only `show`, `join` and `leave` — there is no
rename — so the name a clustered node will carry is a decision for the record that adds the second
node, not a guess made here.

**A private SELinux label will take the broker's key away from it.** Mounting the TLS directory
into another container with `:ro,Z` relabels it, the broker loses read access to its own key, and
every TLS handshake then fails with nothing in any log while the listener still reports running.
This one produced a full day of wrong diagnoses — first a release regression, then a network path
problem, then an interaction between TLS and the auth plugin — and very nearly an upstream bug
report for a defect that did not exist. The TLS directory is mounted into the broker and nothing
else.

## Undo

Remove `dv02msg001v01` from `mqtt_brokers` and stop the two units. Nothing else in the estate
depends on the broker yet, which is the one advantage of being first. The auth database is on the
VM's own disk and has no copy — it holds only what the API can reissue (ADR-0012 §5), so losing it
costs a round of tenant applies, not a device visit.

## Outcome

**Deployed 2026-09-20.** `ok=87 changed=29 failed=0`, and the role's closing report read:

> VerneMQ 2.2.0 serving TLS on dv02msg001v01.mobile.deevnet.net:8883; 0 account(s) in the registry.

Zero accounts is correct: the API provisions them and that is CHG-0016.

### It took three runs, and both failures were preflight

Neither failure created anything. The role asserts before it builds, so the first two runs stopped
with no database, no container and no certificate — which is the behavior those asserts exist for.

**Run 1** failed on *"Fail early if OpenBao is not configured"*. The role reads
`vernemq_openbao_addr` and `vernemq_openbao_ca_local` from inventory and nothing supplied them.
That was a genuine gap in the change: the role was tested against a hand-written config, which
never exercised the inventory wiring.

**Run 2** failed on the same assert, now for the AppRole credentials. `vault_openbao_ansible_role_id`
lives in the `openbao` group's vault, so it is visible only to members of that group — and the
messaging VM is not one, nor should it be. `deevnet_api` solves this by reaching through `hostvars`
to the host that holds the credential; inventory now does the same.

**The assert was not diagnosable, and that is fixed.** It carries `no_log`, because an AppRole id is
half a credential, so a failure said *"assertion failed"* and nothing more with four candidate
causes. A task now reports which settings are empty **by name**, touching no value, and on run 2 it
printed the answer directly. A guard that refuses to proceed is only half the job; one that refuses
without saying why turns a one-minute fix into a bisection.

### What passed, against the live broker over the real network

| | |
|---|---|
| `vmq-admin listener show` | one `mqtts` listener, `running`, `0.0.0.0:8883` |
| Certificate issuer | `CN=Deevnet mobile internal CA` — the site CA, not self-signed |
| Certificate SANs | `dv02msg001v01.mobile.deevnet.net`, `mqtt.mobile.deevnet.net`, `10.20.35.20` |
| Device publishes in its own prefix over TLS | published |
| Wrong password | refused |
| Right password, **wrong client id** | refused — the account key is `(mountpoint, client_id, username)` |
| Anonymous | refused |
| Subscribe `#`, and another tenant's prefix | denied — **ADR-0012 §10, now confirmed over TLS** |
| Subscribe own prefix | allowed |
| Port 1883 | nothing listening; there is no plaintext listener |
| The **API's** database role | provisioned an account |
| The **broker's** database role | `permission denied for table vmq_auth_acl` |

That last pair is ADR-0012 open question 5 — *"only the API writes it, and the broker's credential is
read-only"* — enforced in production rather than intended.

Both retry loops fired once before succeeding, including the TLS listener wait. That is the readiness
check earning its place: `vernemq ping` would have answered `pong` before the acceptor was bound.

### The `mqtt` name

Published by the DNS play, one change on the router. It then appeared not to resolve — which was a
negative cache entry in the Builder's own `systemd-resolved`, created by checking the name *before*
publishing it. Querying the router directly showed the record was correct all along. Worth the
reminder that a resolver's answer is not the same as the zone's contents.

With the name in place, TLS hostname verification against `mqtt.mobile.deevnet.net` passes and a
client publishes over it — which is the path a flashed device actually takes.

### The reachability probe was swapped, and checked

`firewall_reachability_targets` probed port 22 on this host as a stand-in *"until the broker
exists"*. It exists, so the target is now **8883** — the application itself, not something that only
proves the zone boundary.

That change was verified before being trusted. Reachability runs only under `firewall_apply`, so a
plan run never exercises it, and a target that fails to answer **rolls back a correct policy**. All
six targets were probed from the control host the way the role probes them, and all six answer. A
plan run alongside it reported 0 adds, 0 updates and 0 deletes over 56 rules.

## Follow-ups

- **CHG-0016: the API writes broker accounts**, and with it the narrow
  `platform -> iot_backend` rule. The database credential it needs already exists —
  `vault_vernemq_db_writer_password`, created by this change and proven able to provision an account
  that the broker then authenticated.
- **The role was tested against a hand-written config, not against inventory**, which is why both
  deploy failures were inventory wiring. A role that reads settings from inventory has not been
  tested until inventory has supplied them. That rule is **not declared** today, and adding it means
  `firewall_apply` against a live enforcing router.
- **Where the auth database is exposed.** The API must reach it from Platform, but `iot -> iot_backend`
  is a zone-level pass, so publishing the database port on this host's address would also reach
  every device on VLAN 30. How that port is confined is CHG-0016's to settle, and it should not be
  settled by opening it.
- **CHG-0017: retire the inventory ACLs** into tenant Terraform.
- **The Builder's container storage is on the wrong volume.** Rootless podman's graphroot is under
  `/home`, a 20G filesystem, and building this image filled it. `/srv` has 791G free and
  `vg_builder` has no free extents, so the fix is a `graphroot` in `storage.conf` declared in
  `deevnet.builder`.
