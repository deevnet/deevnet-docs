---
title: "CHG-0016: The API Writes Broker Accounts"
weight: 16
---

# CHG-0016: The API Writes Broker Accounts

| | |
|---|---|
| **Date** | 2026-09-20 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | **Complete 2026-09-20**, on option C, mechanism C1. Option A was selected, implemented, tested and **withdrawn** — its mechanism does not work, for a reason worth keeping. C1 was accepted at design review on 2026-09-20, built, deployed and verified the same day. Two defects were found in deployment and fixed; both are recorded below. |
| **Window** | 2026-09-20 |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02msg001v01` (the broker's auth database), `dv02cor002p01` (one new firewall rule, applied) |
| **Automation** | `deevnet.mgmt` `deevnet_api`; `deevnet.net` `opnsense_firewall` with `firewall_apply`; tenant Terraform through `deevnet/deevnet` |
| **Risk** | Medium — a firewall rule applied to an enforcing router, and a new provisioning path between two VMs. Everything else adds. |
| **Related changes** | [CHG-0015](/docs/changes/2026/0015-vernemq-broker/) (built the broker and the database), [CHG-0014](/docs/changes/2026/0014-tenant-device-registry/) (the registry an account may reference), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (why the rule is not enough on its own) |
| **Related incidents** | None |

---

## Summary

The broker runs and holds **zero accounts**. `deevnet_iot_broker_account` answers `501`, so a tenant
has no way to be issued one, and the broker has nothing to authenticate. This is the last piece of
[ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3's version 1.

Most of the work is already done and proven. The database exists with VerneMQ's own schema, the
Deevnet API's credential on it exists and **has been used** — CHG-0015 provisioned an account with
it, and the broker authenticated a client against that account over TLS. What is missing is the API
resource that does it on a tenant's behalf, and a path for the API to reach the database.

## Goal

| | |
|---|---|
| `deevnet_iot_broker_account` | issues an MQTT account for a tenant's device or workload |
| Topic patterns | declared relative to the tenant's prefix; the API writes the prefix itself |
| A tenant | cannot write outside its prefix, whatever it declares |
| The API | reaches the auth database, and **nothing else on IoT Backend can** |
| `lightd` and `lp-stand-01` | still in inventory — retiring them is CHG-0017 |

## What this is not

**It is not a runtime dependency.** ADR-0012 §1 is explicit that the API provisions and is never in
a device's path. The API writes accounts; the broker reads them at connect. An API outage stops
provisioning, never devices — and CHG-0015 proved the broker authenticates from the database with
the API nowhere in the picture.

**It does not give devices anything new.** A device already reaches the broker over
`iot -> iot_backend`. This gives it an account to present when it gets there.

**It is not the device-facing direct service.** That is
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/)'s Option E,
still unbuilt and still waiting on a real consumer.

---

## The decision this change has to make

**How the auth database port is confined.** This is the only open question, and it should be settled
before code rather than during it.

ADR-0012 §7 says the API writes the database *"over a narrow `platform -> iot_backend` rule: from
the provisioning VM to the database port, and nothing else."* That rule **was never declared**. It
was also written in June, before [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) made
zone policy real, and it assumes something that turns out not to hold.

**A zone rule cannot express "and nothing else" here.** Zone rules grant a whole zone. The site
already declares `iot -> iot_backend` as a zone-level pass, because that is how a device reaches the
broker at all. So the moment PostgreSQL listens on `10.20.35.20:5432`, it is reachable from **every
device on VLAN 30** — not because a rule permits it specifically, but because the rule that lets
devices reach the broker cannot tell the broker's port from the database's.

Nothing is exposed today: the database publishes no port, and the broker reaches it by container
name on a private podman network.

### The options

**A — Publish the port, and confine it on the host.** Publish `5432` on the VM's address, declare
the narrow `platform -> iot_backend` rule §7 describes, and add a host firewall rule on
`dv02msg001v01` accepting `5432` only from `dv02prv001v01`. The zone rule states the intent; the
host enforces the part the zone rule structurally cannot.

- *For:* it is what §7 already describes, the API's write path stays direct and synchronous — which
  matters, because a tenant's `terraform apply` is waiting on it — and the host rule closes the gap
  precisely where it exists.
- *Against:* containment now depends on two mechanisms in different places, and only one of them is
  visible in the zone policy. A reader of `firewall.yml` alone would conclude the database is
  exposed to VLAN 30.

**B — Do not expose the database; give the broker an admin surface instead.** The API talks to
something on the broker that writes accounts on its behalf.

- *Against:* VerneMQ's HTTP API is **off** in this deployment — the config declares one listener,
  `listener.ssl.default`, and the release's `listener.http`/`listener.https` settings are untouched.
  Turning one on means adding a *new* exposed service on a segment that devices can already reach,
  which lands on ADR-0020 §5: it would have to authenticate every caller per caller. That is more
  new surface than the problem needs.

**C — Do not expose the port at all; provision by push.** The API hands the account to something on
the messaging VM — an agent, or Ansible — rather than connecting to the database.

- *Against:* it puts a tenant's provisioning path through a second moving part, and ADR-0012 §1's
  guarantee is about the *runtime* path, not the provisioning one. A tenant's apply would now depend
  on delivery as well as on the API.

### Decided: C. Option A was tried and does not work.

**A was chosen on 2026-09-20, implemented, tested, and withdrawn the same day.** The reasoning that
chose it was sound and is unchanged; the *mechanism* it depended on does not exist. That distinction
matters, so both are kept.

#### What A assumed

That a host firewall could constrain a port the zone rule cannot. The zone rule states intent, the
host enforces it, and the principle above says exactly that is allowed.

#### What is actually true

**A firewalld rich rule does not filter a published podman port.** Publishing is DNAT plus forward:
netavark rewrites the destination in `prerouting` and the packet is *forwarded* to the container at
`10.89.0.x`. It never reaches the INPUT chain a rich rule sits on.

Measured, not reasoned about. With the rule in place and permitting only `10.20.25.20/32`:

| From the Builder (`10.20.99.95`, not a permitted source) | |
|---|---|
| broker `8883` | REACHABLE |
| database `5432` | **REACHABLE** — the rule did nothing |

**A firewalld policy object does not fix it either.** Policy objects are the mechanism that filters
forwarded traffic, and that is the right thing to reach for. Tried twice — `egress-zone trusted`,
then `egress-zone ANY` — and neither filtered anything. Two reasons, both structural:

- netavark's forward chain runs at nftables priority `filter` (0); firewalld's runs at `filter + 10`.
- firewalld's zone membership for the container network is by **source address** (`trusted` has
  `sources: 10.89.0.0/24`), while egress-zone matching is by **outgoing interface**. The policy
  never matched the traffic.

**Hand-ordered nftables would work, and is deliberately not done.** It would put a security control
in a table podman owns and rewrites, where a container recreate is enough to remove it silently. A
control that a routine lifecycle event can delete without a word is worse than no control, because
it is believed.

#### The distinction that decides C

The failure is specific to **published container ports**, not to host firewalls. Proven in both
directions on this host, with a throwaway listener so that sshd — which Ansible needs — was never
at risk:

| Path | firewalld rich rule restricted to one source |
|---|---|
| Host listener (INPUT) | **blocked** the Builder correctly |
| Podman published port (DNAT + forward) | no effect; reachable |

So a mechanism that keeps the traffic on a **host listener** gets the packet filter back. That is
the whole argument for C, and it is why C is not merely "A minus the port".

### C: the database is never published

PostgreSQL keeps no published port. It is reachable only by the broker, over the host's private
container network, exactly as it is today. The API provisions through a mechanism on the messaging
VM rather than by connecting to the database.

**What C costs, said plainly.** ADR-0012 §1's guarantee is about the **runtime** path and survives
untouched: the broker reads accounts at connect with the API absent, which CHG-0015 proved. But a
tenant's `terraform apply` now depends on delivery as well as on the API. That is a real change to
the provisioning path and is the price of not publishing the port.

---

## The provisioning mechanism: proposed, not chosen

C needs a way for `dv02prv001v01` to get an account onto `dv02msg001v01` without publishing the
database. **Nothing below is built.** The requirements it has to meet, all of them non-negotiable:

| | |
|---|---|
| PostgreSQL | stays unpublished |
| The API | gets a **definitive success or failure, synchronously** — a tenant's apply is waiting |
| Retries | safe and idempotent; a retry after an ambiguous failure must not double-issue |
| Surface | **no new general-purpose, device-reachable administrative interface** |

And one that follows from the zone policy: whatever listens must be on the **host**, not a published
container port, or it inherits exactly the problem that killed A. Ansible may **deploy** the
mechanism; it must not be in the request path, because the API answers a tenant synchronously and
Ansible is not a request-response channel.

### C1 — SSH with a forced command

The API holds a key; `authorized_keys` on the messaging VM pins it to one program:

```
command="/usr/local/bin/deevnet-broker-account",restrict <key>
```

The API opens a connection, writes the account as JSON on stdin, and reads the result and exit
status.

**Requirements on the key entry, not description of it.** Each of these MUST hold; a key installed
without them is a general login to the messaging VM:

| | |
|---|---|
| `command="…"` | pins the key to one program. The client's requested command is ignored and available in `SSH_ORIGINAL_COMMAND`, which the program MUST NOT execute or interpret |
| `restrict` | denies pty, agent, port, X11 and user-rc by default. It is a *default-deny*, so later OpenSSH additions stay denied — prefer it to listing `no-*` options, which enumerate what was known at the time of writing |
| `from="<API address>"` | binds the key to the source, so a stolen key is not usable from anywhere else. Belt to the firewalld rich rule's braces, and it survives a firewall mistake |
| A dedicated account | not `root` and not `a_autoprov`. The program escalates to what it needs and nothing more |
| Its own key pair | used for nothing else, so revocation is a single-purpose act |

**The program MUST validate its input against a strict schema and MUST NOT be a shell script.** A
shell script reading JSON from a network peer is where the injection bug will be.

- **No new daemon and no new listening port.** sshd is already there, already hardened, already
  patched by the normal update path. Note the precision: C1 *does* add attack surface — the forced
  command is a program reachable by anyone holding the key — but it adds no process listening on a
  socket that was not listening before.
- **It is a host listener**, so firewalld filters it — proven above — and a rich rule can hold it to
  the API's address. That recovers the packet filter A could not have.
- **Synchronous and definitive by construction**: an exit status and a body, over one connection.
- **Idempotent** if the program does the same `ON CONFLICT` upsert the API would have.
- **Costs:** the API gains an SSH key, a new credential class for it — though it already holds an
  OpenBao AppRole, a Proxmox token and Omada credentials, so not unprecedented. Needs a narrow
  `platform -> iot_backend` rule for port 22. **The forced command must be a real program with
  strict input validation, not a shell script** — a shell script taking JSON on stdin from a network
  peer is where the injection bug will be.

### C2 — A minimal authenticated service

A small purpose-built service on the messaging VM with one endpoint, authenticated with mTLS from
the site CA, which already exists and already issues the broker's certificate.

- **A typed contract** rather than a program reading stdin, and an obvious place for validation.
- **mTLS** avoids giving the API an SSH key, and the CA is already in the picture.
- **Costs:** it is a service to write, deploy, version and patch, for one function. It **must run as
  a host service, not a container with a published port**, or it inherits A's failure. And it is a
  new administrative surface — narrow, but new, on a segment devices can already reach, which is
  precisely what ADR-0020 §5 says must then authenticate every caller.

### Recommendation: C1

It adds **no new listening surface at all**, which is the requirement that most directly limits what
this change can cost. It reuses a daemon that is already hardened and already patched by the normal
update path, and `restrict` plus a forced command makes the key single-purpose rather than a general
login. Where C2 has to earn its safety by being written carefully, C1 starts from a service whose
safety is someone else's ongoing job.

The one place C1 is genuinely weaker is the input boundary: a program invoked by sshd reading a
network peer's stdin. That is answerable by writing a real program with a strict schema, and it is a
smaller thing to get right than a whole service.

**A note on what is already true.** sshd on the messaging VM listens on the segment, and
`iot -> iot_backend` is a zone-level pass, so a device on VLAN 30 can already reach port 22 there
today — independently of this change. C1 gives a reason to put a rich rule on sshd, which would be
an improvement on the status quo rather than a new obligation it creates.

---

## Does this need an ADR? No — and here is what was done instead.

ADR-0012 decides every substantive question this change touches: §3 the resource and its
confinement, §10 how topics are confined and exactly what the API writes, §7 the placement, §1 that
the API is provisioning-only. Nothing here is a new architectural position, and a new record would
restate existing ones.

Two documents changed instead, both narrower than an ADR and both more likely to be read by the
person who needs them:

- **The segmentation standard gained the principle**, because it is general and outlives this
  change. A standard is where a rule belongs when it will apply to every service on a shared
  segment, not just to this one.
- **ADR-0012 §7 is amended in place**, the way §3 was for CHG-0013. Its sentence *"a narrow
  `platform -> iot_backend` rule: from the provisioning VM to the database port, and nothing else"*
  promises something a zone rule cannot deliver. It was written before CHG-0007 made zone policy
  real, which is why it assumed otherwise. Left alone it would be believed.

---

## Scope

| In | Out |
|---|---|
| API: `deevnet_iot_broker_account`, migration `0005_`, an auth-database backend | The device-facing direct service (ADR-0020 Option E) |
| Provider: `deevnet_iot_broker_account` | Retiring `mqtt_acls` — CHG-0017 |
| The provisioning mechanism (C1 or C2), and its Ansible deployment | Any change to the broker itself |
| A narrow `platform -> iot_backend` rule for that mechanism's port, applied | Clustering |
| A firewalld rich rule on `dv02msg001v01` restricting that port to the API | Publishing the database port — C exists to avoid it |
| The API's credential for the mechanism | |

## What is already proven

Verified during and after CHG-0015, so this change does not need to re-establish it:

- **The credential works.** The API's database role provisioned an account; the broker's role was
  refused a `DELETE` on the same table.
- **The broker authenticates from the database**, over TLS, with the API absent.
- **Topic confinement holds**: `#` and another tenant's prefix are both denied.
- **The hash formats agree.** The API will compute a bcrypt hash in Go, while the broker runs
  `password_hash_method = crypt`, which verifies inside PostgreSQL. Those are different mechanisms
  and it was not obvious they would agree. Checked against the live database with an externally
  generated `$2a$` hash: the right password verifies, a wrong one does not.
- **firewalld filters a host listener but not a published container port.** Proven in both
  directions on this host, with a throwaway listener so sshd — which Ansible needs — was never at
  risk. This is what makes C workable and A not.
- **podman preserves the caller's source address** through a published port; it does not
  masquerade. This mattered for reading the failed option-A experiment correctly, and it is what
  would let `pg_hba` distinguish callers *if* a port were ever published. **It is not a dependency
  of C** — see below.
- **`pg_hba` refuses by address**, deployed and proven against the live database.

## A correction CHG-0015 earns

CHG-0015's verification recorded *"right password, wrong client id → refused"*. That is true of the
rows it created, which carried the device's own client id — and it will **not** be true of accounts
this change issues. ADR-0012 §10 has the API write `client_id = '*'` deliberately, so an account is
not tied to a client id and a tenant does not declare one. The plugin's lookup is
`WHERE mountpoint=$1 AND (client_id=$2 OR client_id='*') AND username=$3`; the password still has to
match.

Both behaviours are correct for their rows. The record should not leave a reader expecting the
first from an API-issued account.

## Procedure

1. **Choose the mechanism** — C1 or C2. Everything after this depends on it.
2. **Amend ADR-0012 §7** in place. *(Done — see below.)*
3. **Build the mechanism** and deploy it with Ansible. It listens on the **host**, never as a
   published container port.
4. **Inventory**: the narrow `platform -> iot_backend` rule for its port, a firewalld rich rule on
   the messaging VM restricting that port to the API, and the API's credential for it.
5. **Apply the firewall rule** with `firewall_apply`, against a router that is enforcing. Probe
   every reachability target first — they run only under apply, so a plan run never exercises them,
   and a target that does not answer rolls back a correct policy.
6. **Run the Builder regression test** before going further. If `5432` is reachable, stop.
7. **API**: the resource, migration `0005_`, and a backend that calls the mechanism. Validate and
   prefix patterns per §10; refuse a device whose trust class is not `iot`; refuse `modifiers`.
8. **Provider**: `deevnet_iot_broker_account`, with the `present` + `ModifyPlan` restore path and
   the password as a sensitive computed attribute — the tenant's state holds the authoritative copy.
9. **Deploy** the API, then issue an account through tenant Terraform.

## pg_hba: defence in depth, and a dependency worth watching

The auth database restricts who may authenticate, by source address, in its own `pg_hba.conf`. This
is **deployed and proven** — from the Builder, which is not a permitted source:

```
FATAL: no pg_hba.conf entry for host "10.20.99.95", user "deevnet_api", database "vernemq"
FATAL: no pg_hba.conf entry for host "10.20.99.95", user "vernemq",     database "vernemq"
```

**It is defence in depth and does not satisfy ADR-0012 §7 on its own.** A client refused here has
still reached the port and spoken the PostgreSQL protocol; what it cannot do is authenticate. Under
C the port is unpublished, so nothing off this host reaches it at all — `pg_hba` is the second lock,
not the first, and it stays that way if the port is ever published for some later reason.

### What C's isolation actually rests on

**C's isolation of PostgreSQL is that the port is not published.** Nothing off this host has a route
to it, so there is no address to filter and no authentication to attempt. That property depends on
no podman behaviour at all — only on the port staying unpublished.

This is worth stating because the paragraph below is easy to misread as a dependency of C. It is
not.

### Where podman's source handling *does* matter

Two narrower places:

1. **Reading the failed option-A experiment.** Had podman masqueraded, the Builder would have
   appeared as the gateway address and the rich rule's failure could have been misdiagnosed as a
   source-matching problem rather than a wrong-chain problem. Knowing the real address was
   preserved is what made the DNAT-plus-forward explanation the only one left.
2. **`pg_hba` as defence in depth, in the world where a port is published again.** `pg_hba` can
   only distinguish callers if it sees their real addresses. Measured on this host: a connection
   from the Builder appeared in the database container's own `/proc/net/tcp` as `10.20.99.95`.

So: if a future podman release starts masquerading hostport traffic, every external caller collapses
to the gateway address and `pg_hba` stops distinguishing anyone — **silently**, with no error and no
log. Under C that changes nothing, because nothing reaches the port. It would matter the moment
anyone published it again, which is exactly when nobody would be thinking about podman's NAT
behaviour. The Builder regression test below is what would catch it.

## Verification

Run against the live system on 2026-09-20. **Two rows of the original table were wrong and are
corrected here rather than quietly ticked** — see the notes beneath.

| Check | Expect | Result |
|---|---|---|
| A tenant declares `lightstand/+/scene` | stored as `<tenant>/lightstand/+/scene` | PASS — `eds/lightstand/+/scene` |
| A tenant declares `/x`, `$SYS/#`, `a/#/b`, or a pattern containing `%` | refused | PASS — `400`, each naming the pattern and the rule |
| A tenant declares `#` | **accepted**, and prefixed to `<tenant>/#` | PASS — see correction 1 |
| A tenant declares another tenant's prefix | stored under its own prefix, so harmless | PASS — `eds/tdemo/secrets/#` |
| A tenant declares neither publish nor subscribe | refused | PASS — `400`; one direction alone is fine |
| An account with no device | issued — that is a workload account | PASS |
| An account for an `iot_vendor` device | refused (ADR-0012 §3) | **Not exercised** — this site serves only `iot`, so the served-class check fires first, exactly as CHG-0014 found for the registry. Unit tests only |
| A client using the issued account | connects over TLS and publishes in its prefix | PASS — `CONNACK (0)` then `PUBACK (RC:0)` |
| The same client publishing outside its prefix | denied, and the message does not arrive | PASS — connection dropped, no `PUBACK` |
| A client subscribing wider than its ACL | refused | PASS — see correction 2 |
| Wrong password, and unknown username | refused at authentication | PASS — and this is what makes the two rows above meaningful |
| Revoking an account | removed from the registry **and** the broker | PASS — both reached zero |
| **From a device on VLAN 30**, `10.20.35.20:5432` | **refused** — this is the check the whole decision is about | **PASS** — run from a laptop on `DVNTM-IOT` at `10.20.30.101` |
| From the same device, `10.20.35.20:8883` | reachable | PASS — and this is what makes the row above mean "closed" rather than "no path" |
| From the same device, an issued account | connects over TLS, publishes in its ACL, is denied outside it | PASS |
| From `dv02prv001v01`, `10.20.35.20:5432` | **closed** | PASS — see correction 3 |
| From `dv02prv001v01`, `10.20.35.20:22` | reachable, and only after the rule | PASS — closed before the apply, open after |
| `opnsense_firewall` plan run afterwards | no unexpected drift | PASS — 57 rows, `ADD 0 / UPDATE 0 / DELETE 0` |

**Correction 1 — `#` is accepted, not refused.** The original row grouped `#` with the malformed
patterns. That was wrong, and the distinction matters. Patterns are declared *relative* to the
tenant, so `#` prefixes to `<tenant>/#`: the tenant's own whole tree and nothing beyond it. Refusing
it would be arbitrary, and a tenant cannot express anything wider, because the API writes the prefix
and never accepts an absolute pattern. What the row was reaching for is the *broker-side* question,
which is correction 2.

**Correction 2 — the subscribe question is about the broker, not the API.** ADR-0012 §8 flagged as
untested whether a subscription wider than every ACL pattern is refused; the vendor docs do not say.
**It is refused**, measured directly. For an account whose subscribe ACL is
`eds/lightstand/+/state`:

| Filter | |
|---|---|
| `eds/lightstand/a/state` | granted |
| `eds/lightstand/+/state` | granted |
| `eds/lightstand/a/scene` — its own *publish* topic | **denied** |
| `eds/#` — wider, still inside the tenant | **denied** |
| `#` | **denied** |
| `tdemo/#` | **denied** |

This resolves the ADR's open claim in the safe direction.

**Correction 3 — the API does not reach the database, and must not.** The original row said the API
should reach `5432`, which was true of **option A** and is false under C. Under C the database is
published to `127.0.0.1` only; the API reaches port **22** and speaks to the writer. The row is
inverted above because "the API cannot reach the database either" is the stronger property, not a
gap.

**A note on how the client checks were run.** The test classifies three outcomes separately —
*allowed*, *denied by ACL*, *authentication refused* — because a check that cannot tell a denial
from a broken connection will certify a broken system as a working one. That is not hypothetical:
it produced false passes during CHG-0015. The wrong-password and unknown-user rows exist to prove
the classifier can see an authentication failure, which is what makes the denial rows trustworthy.
A first attempt at the subscribe table reported the opposite result because its predicate could not
see the broker's denial; it was discarded rather than reported.

### The Builder regression test — permanent, not a one-off

Run this whenever the broker host, podman, firewalld or the provisioning mechanism changes. It is
kept because it proves the one property this whole change turns on:

> **Zone-level reachability does not imply service-level reachability.**

The Builder is the right prober precisely because the zone policy *permits* it. `management ->
iot_backend` is a pass, so the Builder can reach the segment; if it is nonetheless refused the
database, then something above the zone rule is doing the work. A prober the zone already blocks
would prove nothing.

| From the Builder | Expect | What a failure means |
|---|---|---|
| `8883` | **reachable** | if not, the zone path is broken and the rest of the test is meaningless |
| `5432` | **closed** | if reachable, the database is exposed to every zone the policy admits to IoT Backend — which includes VLAN 30 |
| `psql` as `deevnet_api` | `no pg_hba.conf entry for host …` | under C this should not even connect; if it *authenticates*, a port has been published **and** podman has started masquerading, and the defence-in-depth layer is gone |

The third row is the early warning for the podman dependency above. The first two are cheap enough
to run on any change to the host.

**The VLAN 30 test was run on 2026-09-20** from a laptop joined to `DVNTM-IOT` at `10.20.30.101`,
and it passes. `8883` is reachable and `5432` is refused, from the segment the decision is actually
about rather than from a proxy.

Both lines matter together. The Builder is a sound proxy for the *mechanism* — firewalld and
`pg_hba` match on source address and know nothing about VLANs — but it is not a substitute for the
real path, and a closed port proves nothing on its own unless something else on the same host
answers. `8883` succeeding is what makes `5432` refused mean "the port is closed" rather than "the
network is broken".

The same client also exercised the broker end to end: an account issued through the API
authenticated over TLS, published inside its ACL and was refused outside it, with the denial
visible in the broker's own log:

```
can't auth publish for client (user "eds-mactest")
  on topic [eds,somewhere,else] due to not_authorized
```

So the device path is proven from where a device really sits, not only from the control node. The
test account was revoked afterwards; the registry and the broker database both returned to zero.

## What was built

| | |
|---|---|
| `internal/brokeracct` | the wire contract both ends share |
| `cmd/deevnet-broker-account` | the writer: fixed config path, never reads `SSH_ORIGINAL_COMMAND`, parameterised SQL only |
| `internal/backend/brokerwriter` | the SSH transport: pinned host key, bounded at connect and session |
| `deevnet_iot_broker_account` | the API resource and the provider resource |
| `deevnet.mgmt` `vernemq` | installs the writer, pins the API's key, restricts sshd |
| `deevnet.mgmt` `deevnet_api` | reads the messaging host's key at deploy time and pins it |
| One firewall rule | `platform -> iot_backend`, TCP 22, host to host |

Deployed as API `v0.5.1`. The writer's key is the API's own and is used for nothing else, so
revoking it revokes exactly this capability.

### The ordering that makes a retry safe

The hash is written to the registry **before** the writer is called. A retry after an ambiguous
failure therefore sends the same hash and converges. The other order mints a new password on every
retry and strands every device already flashed with the old one — the CHG-0013 failure, in a new
place.

This was exercised for real. The three accounts created during the failed first attempt came back
on retry with an empty password, because the re-apply correctly reused the stored hash. The API
keeps only a bcrypt hash and cannot reproduce a plaintext it once issued, so **the only copy of
those passwords was in the `502` bodies**. A caller that discards them strands the account,
recoverable only by delete-and-recreate. The provider keeps them; the ad-hoc probe used here did
not, which is why those three were deleted and reissued.

## Two defects found in deployment

Both were found by running the thing, not by reading it, and both had passed a check beforehand
that turned out to be asking the wrong question.

### 1. A pinned host key needs its algorithm pinned too

Every account failed with:

```
authenticating to the writer: ssh: handshake failed: ssh: host key mismatch
```

against a host that was exactly who it said it was.

The messaging VM offers **ecdsa, ed25519 and rsa** with no `HostKey` directive narrowing them, and
which one the server presents is chosen from the **client's** preference list. `x/crypto`'s default
order is ECDSA, then RSA, with **ed25519 last**. The role pins `ssh_host_ed25519_key.pub`, so the
server answered with its ECDSA key every time and the pin could never match.

Fixed by constraining `HostKeyAlgorithms` to the pinned key's own type. Worth guarding carefully,
because the failure **reads identically to an attack** — which is the worst way for a configuration
error to present.

The regression test took three attempts and **the first two were worthless**: both passed with the
fix reverted. The first offered a second host key but set the field *after* the constructor had
already built the server config, so no second key was ever offered and there was no negotiation to
exercise. The second fixed that but pinned RSA while offering ed25519 — the direction the client
already gets right. The test now pins ed25519 against an rsa-offering host, and fails without the
fix with the same message the deployment produced.

### 2. `SSH_CLIENT` does not survive `become`

The `vernemq` role derives the control node's address from what the host sees Ansible arrive from,
rather than from a value inventory names — because the assert is about *that* address, and
inventory's belief about a route is not the route.

The first implementation read `ansible_env.SSH_CLIENT`. The site play runs with `become`, and
sudo's `env_reset` strips `SSH_CLIENT`, so the fact is absent **exactly where it is needed**. It had
been verified before deploying — but with ad-hoc `ansible` and a playbook that did not `become`, so
the check passed in a context the role never runs in. It now asks the connection user directly,
with `become: false` on that one task.

**The guard worked.** The assert refused on an empty value and stopped before touching sshd, so a
wrong derivation cost a re-run rather than console access. That is the whole reason it is written
as an assert and not a default.

### What both have in common

Each was verified beforehand in a context the production path does not use — a single-host-key test
server, and a play without `become`. A check that does not reproduce the real conditions returns a
green that means nothing, which is the same lesson CHG-0015 recorded about its own test harness.

## Undo

Remove the account rows, set the API version back, and delete the firewall rules. The broker keeps
running throughout: it reads accounts at connect, so removing them stops new connections and leaves
existing sessions alone. Nothing a tenant holds is lost that a re-apply cannot reissue
(ADR-0012 §5).

## Follow-ups

- **CHG-0017: retire mosquitto.** Wider than the inventory ACLs alone, because the pivot to VerneMQ
  left litter in three places and they are one job:
  - `mqtt_acls` and `vault_mqtt_users` in inventory. **Orphaned, not merely debt** — the only thing
    that read them was the `mosquitto` role, and no play has run it since CHG-0015 replaced it.
    They describe accounts that do not exist, on a broker that never sees them.
  - The **`mosquitto` role itself**, still on disk in `deevnet.mgmt` and referenced by no playbook.
  - The **collection README**, which still lists mosquitto as *"to be replaced by VerneMQ in the
    messaging VM"*. It has been. A document describing a future that already happened is worse than
    one that says nothing.

  `dv02mqt001v01` needs nothing: it is already out of inventory, named only in a comment.

  Worth its own window rather than being tacked onto this change, because removing
  `vault_mqtt_users` touches a vault file and wants the same encrypt, commit and **push** ordering
  CHG-0015's secrets used — the discipline INC-0003 exists to enforce. Deleting a role is cheap;
  editing a vault in a hurry is how the last incident started.
- **ADR-0012 §8's subscribe claim can be marked proven.** The verification above answers it: a
  filter wider than every ACL pattern is refused. The ADR still lists it as untested.
- **Stale writer binaries** from pre-release testing are still in the artifact store beside the
  tagged ones. Harmless, and worth sweeping when convenient.
- **ADR-0020's direct service** still has no consumer.
- **The Builder's container storage** is still on a 20G `/home`.
