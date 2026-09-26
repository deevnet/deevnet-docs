---
title: "Tenant Admission"
weight: 5
aliases:
  - /docs/runbook/tenant-provisioning/
  - /docs/runbook/tenant/legacy-provisioning/
---

# Tenant Admission

The operator's half of creating a tenant. The operator **admits a name**; the tenant then declares
everything else itself, through the Deevnet API
([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)). The tenant's half
is [Tenant Operations](/docs/runbook/tenant/).

Admission is the only substrate act a new tenant needs. The operator never edits an inventory file
to make a tenant, and the tenant never holds a Proxmox credential, a vault password or an index.

---

## Before you start

| | |
|---|---|
| The API | `https://api.mobile.deevnet.net:8080`, reachable from the Builder |
| The operator token | `vault_deevnet_api_token`, in the inventory's `deevnet_api` group vault |
| The site CA | `ansible-collection-deevnet.mgmt/.openbao/site-ca.pem` on the control node |
| The provider | the tenant installs `deevnet/deevnet` 0.4.x itself with `install-provider.sh` from the tenant downloads ([Before You Start](/docs/runbook/tenant/getting-started/before-you-start/#getting-the-provider)). No role installs it. Before a meetup, check the downloads tree is current: the provider repo's `make stage`, the image factory's `make pi-backend-publish`, then `deevnet.mgmt site.yml --tags tenant-downloads` |

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
| A name already registered | answers `409`. Admission creates nothing; it only authorizes |

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

Every apply has to reach the API, and after the first one the state store too. Give the tenant the
**`DVNTM-TD`** key (`deevnet_wifi_psk.tenant_dev`): that segment reaches the API, the state store,
the broker, the log store and Grafana, and nothing else
([CHG-0022](/docs/changes/2026/0022-tenant-dev-network/), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)). Guest is
internet-only and IoT cannot reach the API. A trusted seat still works, but it reaches the
management plane, so don't offer it to a visitor. See
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
| Dashboards | a Grafana organization named for the tenant, one Editor login, and three log data sources carrying its read token, with fixed UIDs ([ADR-0024](/docs/architecture/decisions/0024-dashboards/)). A delete renames the emptied organization `deleted-<tenant>-<id>`, because Grafana 13 cannot delete one |
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
