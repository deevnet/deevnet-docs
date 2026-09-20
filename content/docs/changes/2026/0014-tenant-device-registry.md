---
title: "CHG-0014: The Tenant Device Registry"
weight: 14
---

# CHG-0014: The Tenant Device Registry

| | |
|---|---|
| **Date** | 2026-09-20 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Planned.** Code, tests and documentation are written and green; nothing is deployed and no image is staged. |
| **Window** | TBD |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (Deevnet API v0.3.1 → v0.4.0, and its database: one new table) |
| **Automation** | `deevnet.mgmt` `playbooks/site.yml --limit deevnet_api`, against `ansible-inventory-deevnet/mobile`; then `terraform apply` in a tenant repo |
| **Risk** | Low — one additive migration, one new route group, no substrate configuration and no firewall change. The API restarts. |
| **Related changes** | [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) (the API this extends), [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) (Wi-Fi keys, the precedent this copies), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (the zone policy that makes this the only sanctioned direction) |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

`ADR-0020` accepted a contract for direct device access to tenant services and fixed the order of
work: **the device registry comes first**, because until devices exist as state, the contract's §2
(a credential the device proves) and §5 (every device-facing service authenticates per device) have
nothing to draw on. Today `/v1/tenants/{name}/devices` falls through to the API's catch-all and
answers `501`.

This builds that registry: `deevnet_iot_device` end to end — API, provider, deployed — so a tenant
records its own devices through `terraform apply`.

### What prompted it

An operator joined `DVNTM-IOT` with eds's PPSK and could no longer reach a service in the eds
tenant. That is [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) working correctly:
before it, the router was allow-all and the client was riding the operator route
[ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/) added for `management` and
`trusted`, which was never declared for `iot`. CHG-0007 phase 3 tested that exact path and recorded
the drops.

The fix that suggests itself is forbidden.
[ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §4: *"`IoT ->
tenant_transit`, or `IoT -> tenant networks`, is not the answer… It must not be added."* The
sanctioned replacement is a device-facing, per-device-authenticating service on IoT Backend that
both sides dial into. This change is its first prerequisite.

## Goal

| | |
|---|---|
| `POST /v1/tenants/{name}/devices` | registers a device; `201` with the entry |
| The registry | holds `name`, `trust_class` and an optional `mac`, scoped to the calling tenant |
| A tenant | declares `deevnet_iot_device` and `terraform apply` converges; a second `plan` is clean |
| Another tenant | gets `404`, not `403`, for a device that is not its own |
| Everything else | unchanged — no firewall rule, no segment, no SSID, no VLAN, no DNS |

## What this is not

**It is not authorization.** A registry entry is identity. Registering a device grants it nothing,
and nothing in this change lets a device reach a tenant service. ADR-0020 §2 puts authorization in a
credential the device proves, and that credential is not built — its mechanism is deliberately still
open.

**It is not a network change.** ADR-0020's Option E is explicit that it needs *"zero new
substrate"*. The registry is a Platform-side provisioning call over the already declared
`tenant_transit -> platform` rule. Run `opnsense_firewall` in its default report mode afterwards to
confirm no drift; **do not** pass `firewall_apply`.

**It does not bind a device to a Wi-Fi key.** The key stays per tenant per trust class
(CHG-0013, amending ADR-0011 Q3), and a device entry does not reference one. Deregistering a device
therefore does not disconnect it — revoking the key it holds would strand every other device the
tenant flashed with the same key.

**The `mac` is recorded, not enforced.** It is a label for the owner's own inventory. A MAC is
trivially spoofed on a shared segment, so it is never an authorization input (ADR-0020 §2), and two
tenants may record the same address — a cross-tenant uniqueness conflict would disclose that another
tenant holds it, which is what the API's 404-rather-than-403 scoping exists to prevent.

## Scope

| In | Out |
|---|---|
| Deevnet API v0.4.0: `devices` routes, `tenant_devices` table (migration `0004`) | Broker accounts — still `501`, because there is no broker |
| Provider resource `deevnet_iot_device` | The per-device credential (ADR-0020 §2; needs its own record, next free ADR is 0021) |
| `deevnet_api_version` bump in `deevnet.mgmt` | The device-facing rendezvous service (ADR-0020 §5; blocked on a real consumer) |
| `docs/api-v1.md` | Any firewall, VLAN, SSID or DNS change |

## Risk and impact

The API restarts, so a tenant `terraform apply` in flight fails and is retried. The migration is
additive — one new table, no existing table altered — so a rollback to v0.3.1 leaves an unused table
behind and nothing else.

`tenant_devices` cascades from `tenants`, matching Wi-Fi keys. A device row holds nothing the
substrate must tear down, unlike a workload, which is a real VM and blocks its tenant's deletion.

## Prerequisites

- A clean, tagged `deevnet-provisioning-api` tree at `v0.4.0`, and `make stage` run, because the
  provisioning VM sits on Platform and has no route back to the artifact server: images are pushed,
  not pulled.
- The provider built and available to the tenant repo used for verification.

## Procedure

1. **Stage the image.** In `deevnet-provisioning-api`: `make test`, `make vet`,
   `make test-integration`, tag `v0.4.0`, `make stage`.
2. **Deploy.** In `ansible-collection-deevnet.mgmt`:
   `ansible-playbook playbooks/site.yml --limit deevnet_api`. The migration runs at startup under
   the advisory lock.
3. **Verify the API** — see below.
4. **Verify through Terraform** in a tenant repo, against `tdemo` rather than `eds`.
5. **Confirm no firewall drift**: `ansible-playbook playbooks/opnsense.yml` in report mode.

## Verification

| Check | Expect |
|---|---|
| `GET /version` | `v0.4.0` |
| `POST /v1/tenants/tdemo/devices {"name":"stand-1","trust_class":"iot"}` as operator | `201`, `status: ready` |
| The same with `"mac":"AA:BB:CC:DD:EE:FF"` | `201`, `mac` echoed as `aa:bb:cc:dd:ee:ff` |
| eds's token against `/v1/tenants/tdemo/devices` | **`404`**, not `403` |
| `"trust_class":"nonesuch"` | `400`, naming the classes the site serves |
| `"trust_class":"iot_vendor"` | `201` — legal; ADR-0012 §3 refuses such a device a *broker account*, not an identity |
| `deevnet_iot_device` in `tdemo`, `apply` then `plan` | no changes |
| **Restore drill:** `DELETE` the row at the API, then `plan` | a diff, not "no changes"; `apply` puts the row back |
| `opnsense_firewall` report mode | 0 adds, 0 updates, 0 would-deletes |

The restore drill is the one worth running carefully. The resource carries no secret today, so
`Read` could drop it from state and let Terraform plan a create. It does not: it sets
`present = false` and `ModifyPlan` turns that into a diff. That shape is built now on purpose,
because ADR-0020 §2 attaches a per-device credential to this same resource later, and retrofitting
the restore path after the first credential has been issued is exactly the sequence that would mint
a second one and cost a visit to the device.

## Undo

Set `deevnet_api_version` back to `v0.3.1` and re-run the play. The `tenant_devices` table stays —
the migration runner only rolls forward — and is simply unused by v0.3.1; the routes return to `501`
through the catch-all. Any `deevnet_iot_device` in a tenant's state then reads `404` and reports
`present = false`, which is the same state a registry loss produces and is recovered the same way.

## Outcome

Not yet run.

## Follow-ups

- **Stage 2 is redirected at the broker.** *Decided 2026-09-20.* The next step was to be the
  per-device credential of ADR-0020 §2, which needs a new ADR because the mechanism is deliberately
  open. It is deferred in favour of the **VerneMQ broker** (ADR-0012 §8), because the first real
  consumer — the eds vertical, `lightd → palette → lightd → mqtt01 → stand` — is publish/subscribe,
  and ADR-0020 §1 keeps MQTT preferred wherever pub/sub fits. The broker needs **no new ADR**:
  ADR-0012 §8 decided the broker, §10 its topic confinement and §3 the `deevnet_iot_broker_account`
  resource. This registry is a prerequisite for that resource, which takes an optional device and
  checks its trust class.
- **ADR-0021 — the device credential — is deferred, not cancelled.** It is still what ADR-0020 §5's
  invariant needs for a non-MQTT device-facing service, and stage 3 cannot start without it.
- **The rendezvous service** (ADR-0020 §5) stays unstarted until a real consumer decides its
  protocol surface, which ADR-0020's implementation notes require.
- **A missing rule, for whoever builds the broker.** ADR-0012 §7 says the API writes the broker's
  auth database over a narrow `platform -> iot_backend` rule. **That rule is not declared** — the
  three `platform`-source rules in `firewall.yml` are two `platform -> management` and one
  `platform -> platform`. It is not this change's to add, but it will fail as a *timeout inside a
  tenant's own `terraform apply`*, which is the failure mode that file already warns about.
- **`make docs` in the provider cannot run** on the current toolchain: `tfplugindocs@latest` needs
  Go ≥ 1.25.8 and the pinned local toolchain is 1.25.5. `docs/` was already empty, so nothing
  regressed, but the new resource's reference page cannot be generated until that is resolved.
