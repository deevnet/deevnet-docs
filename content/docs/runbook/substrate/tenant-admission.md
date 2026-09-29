---
title: "Tenant Admission"
weight: 7
aliases:
  - /docs/runbook/tenant-provisioning/
  - /docs/runbook/tenant/legacy-provisioning/
---

# Tenant Admission

The operator's half of creating a tenant. The operator **admits a name**; the tenant then declares
everything else itself, through the Deevnet API
([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)). The tenant's half
is [Tenant Operations](/docs/runbook/tenant/).

Admission is the only substrate act a new tenant needs. The operator never edits an inventory file
to make a tenant, and the tenant never holds a Proxmox credential, a vault password or an index.

---

## Before you start

| | |
|---|---|
| The API | `https://api.mobile.deevnet.net:8080`, reachable from the Builder |
| The operator token | nothing to fetch: `make admit` reads it from the running API container over SSH, and never prints it. It is also `vault_deevnet_api_token`, in the inventory's `deevnet_api` group vault, for calling the API by hand |
| The site CA | `ansible-collection-deevnet.mgmt/.openbao/site-ca.pem` on the control node |
| The provider | the tenant installs `deevnet/deevnet` 0.5.x itself with `install-provider.sh` from the tenant downloads ([Before You Start](/docs/runbook/tenant/getting-started/before-you-start/#getting-the-provider)). No role installs it. Before tenants will be downloading from the site, check the downloads tree is current: the provider repo's `make stage`, the image factory's `make pi-backend-publish`, then `deevnet.mgmt site.yml --tags tenant-downloads` |

---

## 1. Admit the name

From `ansible-collection-deevnet.mgmt` on the Builder:

```bash
make admit NAME=mabell                          # or bind the Wi-Fi key to one laptop:
make admit NAME=mabell MAC=AA-BB-CC-00-11-22
```

```
admitted mabell: expires 2026-09-26T…Z, Wi-Fi DVNTM-TD
handover details: /home/<you>/mabell-admission.txt (mode 0600)
```

The terminal shows nothing secret. `~/<name>-admission.txt` holds everything the tenant is handed:
the enrollment token and its expiry, the API endpoint, the `DVNTM-TD` Wi-Fi key, the site CA's URL
and fingerprint, and the tenant's first three steps. It is written to be read and passed on by a
person.

The Wi-Fi key is the tenant's own `DVNTM-TD` key
([ADR-0029](/docs/architecture/decisions/tenant-networking/0029-tenant-developer-network-keys/)): a
tenant needs that network to reach the API at all, so its first key comes with the admission. `MAC=`
binds it to one laptop. When the tenant creates itself, the key becomes its own Wi-Fi key
`admission`.

| | |
|---|---|
| The name | `^[a-z][a-z0-9]{0,7}$` — it becomes a PVE SDN zone ID, a DNS label and a state-store user |
| The token | single-use, expires after `DEEVNET_ENROLLMENT_TTL` (72h by default) |
| A name already registered | answers `409`. Admission creates nothing but that key; it only authorizes |
| Admitting the name again | issues a new key; the one handed over before stops working. `make admit` refuses while `~/<name>-admission.txt` exists; `FORCE=1` admits anyway |
| An admission never used | `make unadmit NAME=<name>` revokes its key (`DELETE /v1/admissions/<name>`) and deletes the handover file. The token itself just expires |

## 2. Hand over four things

The tenant needs exactly these, and nothing else from the substrate. All four are in
`~/<name>-admission.txt`:

1. the **enrollment token**
2. the **API endpoint**, `https://api.mobile.deevnet.net:8080`
3. the **`DVNTM-TD` Wi-Fi key** ([§3](#3-where-the-tenant-applies-from))
4. the **site CA**, `site-ca.pem`

The token is bound to the name. Presenting it for a different name **spends** it and answers `401`,
so a mistyped name costs a new admission.

{{< hint warning >}}
**Delivery is by hand today.** ADR-0012 §9 says the token is delivered age-encrypted to the
tenant's own key; that tooling is not built. Until it is, hand the token over on a channel you would
trust with a password, and admit close to when the tenant will apply — an unspent token is a
credential for 72 hours. Delete `~/<name>-admission.txt` once it is handed over: after the first
apply the Wi-Fi key in it is the tenant's to keep, not yours.
{{< /hint >}}

## 3. Where the tenant applies from

Every apply has to reach the API, and after the first one the state store too. Give the tenant the
**`DVNTM-TD`** key, the one in the admission's `wifi`, not a shared one: that segment reaches the API, the state store,
the broker, the log store, Grafana and SSH on tenant workloads, and nothing else
([CHG-0022](/docs/changes/2026/0022-tenant-dev-network/), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)). Guest is
internet-only and IoT cannot reach the API. A trusted seat still works, but it reaches the
management plane, so don't offer it to a visitor. See
[Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) for how the tenant side
reads this.

**You have no standing access to a tenant's workloads**
([ADR-0028](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/)). They clone the
`fedora-tenant-*` template, which carries no `a_autoprov`, and trust only the keys in the tenant's
`ssh_keys`. To help on one, the tenant adds your public key and replaces the workload.

---

## Rotating a tenant's Wi-Fi key

A tenant's `DVNTM-TD` password is handed over once: the API never returns a key's password again,
so a lost one is replaced, not recovered. Rotate the key to give it a new password — after a loss, a
possible leak, or on a schedule:

```bash
make rotate-wifi-key NAME=<tenant>                 # the admission key
make rotate-wifi-key NAME=<tenant> KEY=<key>       # any other key
```

It shows the key's trust class, SSID and MAC binding, asks for the tenant's name, then deletes the key
and creates it again under the same name and settings. The new password goes to
`~/<tenant>-wifi-<key>.txt` (mode 0600), to hand over like an admission. The old password stops
working on every device that used it; each one forgets the network and joins again.

Only the `admission` key is the operator's to rotate. It came with the admission and the tenant's
Terraform does not declare it. A key the tenant declares, such as its devices' key, lives in the
tenant's state, and rotating it here would leave that state holding the old password: the tenant
rotates its own with `terraform apply -replace=<the key's resource>`.

---

## What the substrate does on the first apply

| | |
|---|---|
| Network | an EVPN zone and VRF on the tenant hypervisor, one VNet, a `/24` from `10.20.128.0/18`, anycast `.1`, SNAT at the exit node |
| DNS | `<tenant>.<site>.deevnet.net` and its reverse, delegated, with a TSIG key the tenant writes records with |
| State | a bucket prefix and keys in the state store |
| Logs | partitions `(index, 0..2)`, an ingest and a read token, and the vmauth routes that separate them from every other tenant ([ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/)) |
| Dashboards | a Grafana organization named for the tenant, one Editor login, and three log data sources carrying its read token, with fixed UIDs ([ADR-0024](/docs/architecture/decisions/platform-services/0024-dashboards/)). A delete renames the emptied organization `deleted-<tenant>-<id>`, because Grafana 13 cannot delete one |
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
| `DELETE /v1/tenants/{name}` | take a tenant out of service, after its workloads (the tenant can call it too, with its own token). Use `make remove-tenant`, which also removes what the call leaves behind: [Tenant Removal](/docs/runbook/substrate/tenant-removal/) |
| `POST /v1/tenants/{name}/reconcile` | re-ensure every backend with the secrets the registry holds. The repair after a backend is rebuilt, and how a tenant created before a service existed is handed that service's credentials |

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| `409` on admission | the name is already registered. The tenant uses its own token, not a new admission |
| `401` on the tenant's first apply | the enrollment token was issued for a different name, and is now spent. Admit again |
| `501` on every tenant route | the API has no site configured, or no OpenBao |
| A tenant lists with no log store | the list endpoint returns lean records. Ask the detail endpoint |
