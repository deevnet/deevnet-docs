---
title: "Tenant Admission"
weight: 5
---

# Tenant Admission

The operator's half of creating a tenant. The operator **admits a name**; the tenant then declares
everything else itself, through the Deevnet API
([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)). The tenant's half
is [Tenant Operations](/docs/runbook/tenant/).

Admission is the only substrate act a new tenant needs. The operator never edits an inventory file
to make a tenant, and the tenant never holds a Proxmox credential, a vault password or an index.
The older procedure that did those things is
[Legacy Provisioning](/docs/runbook/tenant/legacy-provisioning/), kept only as history.

---

## Before you start

| | |
|---|---|
| The API | `https://api.mobile.deevnet.net:8080`, reachable from the Builder |
| The operator token | `vault_deevnet_api_token`, in the inventory's `deevnet_api` group vault |
| The site CA | `ansible-collection-deevnet.mgmt/.openbao/site-ca.pem` on the control node |
| The provider | the tenant will need `deevnet/deevnet` at the current tag (0.3.x) in the filesystem mirror of whatever seat it applies from. The workstation role installs it; `make mirror` in `terraform-provider-deevnet` does it by hand |

---

## 1. Admit the name

```bash
curl -sS --cacert site-ca.pem \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"mabell"}' \
  https://api.mobile.deevnet.net:8080/v1/admissions
```

```json
{ "name": "mabell", "enrollment_token": "s.…", "expires_at": "2026-09-26T…Z" }
```

| | |
|---|---|
| The name | `^[a-z][a-z0-9]{0,7}$` — it becomes a PVE SDN zone ID, a DNS label and a state-store user |
| The token | single-use, expires after `DEEVNET_ENROLLMENT_TTL` (72h by default) |
| A name already registered | answers `409`. Admission creates nothing; it only authorises |

## 2. Hand over three things

The tenant needs exactly these, and nothing else from the substrate:

1. the **enrollment token**
2. the **API endpoint**, `https://api.mobile.deevnet.net:8080`
3. the **site CA**, `site-ca.pem`

The token is bound to the name. Presenting it for a different name **spends** it and answers `401`,
so a mistyped name costs a new admission.

{{< hint warning >}}
**Delivery is by hand today.** ADR-0012 §9 says the token is delivered age-encrypted to the
tenant's own key; that tooling is not built. Until it is, hand the token over on a channel you would
trust with a password, and admit close to when the tenant will apply — an unspent token is a
credential for 72 hours.
{{< /hint >}}

## 3. Where the tenant applies from

A tenant's first apply has to reach the API. Today that means a **trusted seat** — the Builder, or a
laptop on the trusted network — because the guest network is internet-only and the IoT network
cannot reach the API. See
[Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) for how the tenant side
reads this.

---

## What the substrate does on the first apply

| | |
|---|---|
| Network | an EVPN zone and VRF on the tenant hypervisor, one VNet, a `/24` from `10.20.128.0/18`, anycast `.1`, SNAT at the exit node |
| DNS | `<tenant>.<site>.deevnet.net` and its reverse, delegated, with a TSIG key the tenant writes records with |
| State | a bucket prefix and keys in the state store |
| Logs | partitions `(index, 0..2)`, an ingest and a read token, and the vmauth routes that separate them from every other tenant ([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/)) |
| Devices, if declared | a PPSK per trust class, registry entries, and MQTT accounts confined to the tenant's own topic prefix |

The index is the tenant's number in all of it — subnet, VXLAN VNI, log account — so it is allocated
once, against both the registry **and** the live fabric, and never by hand.

To confirm the fabric side, `pvesh get /cluster/sdn/zones` on the tenant hypervisor shows
`vrf_<tenant>` with its own VNI.

---

## Operator-only calls

| Call | Use |
|---|---|
| `GET /v1/tenants` | every tenant, by index, without secrets. The list is lean — ask `GET /v1/tenants/{name}` before concluding something is missing |
| `POST /v1/tenants/{name}/reconcile` | re-ensure every backend with the secrets the registry holds. The repair after a backend is rebuilt, and how a tenant created before a service existed is handed that service's credentials |

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| `409` on admission | the name is already registered. The tenant uses its own token, not a new admission |
| `401` on the tenant's first apply | the enrollment token was issued for a different name, and is now spent. Admit again |
| `501` on every tenant route | the API has no site configured, or no OpenBao |
| A tenant lists with no log store | the list endpoint returns lean records. Ask the detail endpoint |
