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
| **Status** | **Planned.** The open decision is settled — option A, with the principle behind it written into the segmentation standard. Nothing is built. |
| **Window** | TBD |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02msg001v01` (the broker's auth database), `dv02cor002p01` (one new firewall rule, applied) |
| **Automation** | `deevnet.mgmt` `deevnet_api`; `deevnet.net` `opnsense_firewall` with `firewall_apply`; tenant Terraform through `deevnet/deevnet` |
| **Risk** | Medium — the only change here that can break something else is a firewall rule applied to a router that is now enforcing. Everything else adds. |
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

### Decided: A

**Accepted 2026-09-20.** The port is published and confined on the host: the narrow
`platform -> iot_backend` rule states the intent, and a host firewall rule on `dv02msg001v01`
accepts `5432` only from `dv02prv001v01`.

What settled it was not that a host firewall is an acceptable fallback where the zone rule falls
short. That framing treats zone coarseness as a deficiency, and it does not scale: it would have to
be re-argued for every service that lands on a shared segment. The framing that does scale is that
**zone policy and host policy govern different things**, and neither is standing in for the other:

> Network policy controls reachability between security zones; host or service policy may further
> constrain access to individual services where zone-level policy is intentionally coarser.

`iot -> iot_backend` is not a compromise. It is a deliberate statement that the IoT segment may
reach the IoT Backend segment, and it was never a statement about every socket behind it.
**Reachability is not permission.** A zone that made per-service statements would pull every
service's topology into the router's rule table and turn adding a listener into a firewall change.

This is now recorded where a future reader will find it without reading this change:
[Network Segmentation → Reachability and Permission](/docs/standards/network-segmentation/#reachability-and-permission).
It matters more than this change does. IoT Backend has two services today; when it has fifteen,
nobody should have to rediscover why zone reachability is not permission to every socket in the
zone.

The obligation it puts on this change: because the database's real exposure is narrower than
`firewall.yml` implies, the zone policy has to **say so**, or a reader of the rule table concludes
the database is open to VLAN 30.

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
| The narrow `platform -> iot_backend` rule, applied | Any change to the broker itself |
| A host firewall rule on `dv02msg001v01`, if option A | Clustering |
| The API's database credential in its configuration | |

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

1. **Decide the question above.** Everything else follows from it.
2. **Amend ADR-0012 §7** in place.
3. **API**: the resource, migration `0005_`, and a backend that writes `vmq_auth_acl`. Validate and
   prefix patterns per §10; refuse a device whose trust class is not `iot`; refuse `modifiers`.
4. **Provider**: `deevnet_iot_broker_account`, with the `present` + `ModifyPlan` restore path and
   the password as a sensitive computed attribute — the tenant's state holds the authoritative copy.
5. **Inventory**: the narrow zone rule, the host rule if option A, and the API's database credential.
6. **Apply the firewall rule** with `firewall_apply`, against a router that is enforcing. Probe all
   reachability targets first; a target that does not answer rolls back a correct policy.
7. **Deploy** the API, then issue an account through tenant Terraform.

## Verification

| Check | Expect |
|---|---|
| A tenant declares `lightstand/+/scene` | stored as `<tenant>/lightstand/+/scene` |
| A tenant declares `#`, `/x`, `$SYS/#`, or a pattern containing `%` | refused |
| A tenant declares another tenant's prefix | stored under its own prefix, so harmless |
| An account for an `iot_vendor` device | refused (ADR-0012 §3) |
| An account with no device | issued — that is a workload account |
| A client using the issued account | connects over TLS and publishes in its prefix |
| The same client publishing outside its prefix | denied, and the message does not arrive |
| **From a device on VLAN 30**, `10.20.35.20:5432` | **refused** — this is the check the whole decision is about |
| From `dv02prv001v01`, the same port | reachable |
| `opnsense_firewall` plan run afterwards | no unexpected drift |

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
- **ADR-0020's direct service** still has no consumer.
- **The Builder's container storage** is still on a 20G `/home`.
