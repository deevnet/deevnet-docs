---
title: "CHG-0013: Tenant Wi-Fi PPSK Keys"
weight: 13
bookCollapseSection: true
---

# CHG-0013: Tenant Wi-Fi PPSK Keys

| | |
|---|---|
| **Date** | 2026-09-18 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **In progress.** Phases 1–4 and 6 done and verified: `DVNTM-IOT` is on air, the API issues and revokes keys on v0.3.1, and `eds` holds its own key from `terraform apply`. **Only phase 5 is outstanding** — a client joining with that key, which needs someone at the site. |
| **Window** | 2026-09-18 onward |
| **Site** | mobile |
| **Systems** | `dv02nms001v01` (Omada controller: new SSID and PPSK profile), `dv02wap001p01` (AP: new SSID on air), `dv02prv001v01` (Deevnet API v0.3.1), `ansible-inventory-deevnet` |
| **Automation** | `deevnet.net` `playbooks/omada-wireless.yml` via `make wireless`; `deevnet.mgmt` role `deevnet_api`; tenant Terraform through `deevnet/deevnet` |
| **Risk** | Medium — creating an SSID re-applies the WLAN group to a live AP, which can drop associations on `DVNTM` for a few seconds. Nothing existing is rewritten or deleted. |
| **Related changes** | [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) (proved PPSK, left the follow-up), [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) (the API this extends), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (must not break the API's path to the controller) |
| **Related incidents** | [INC-0002](/docs/runbook/incident-management/) (the controller hang; it is now in a tenant's apply path) |
| **Related runbooks** | [Wireless AP recovery](/docs/runbook/recovery/console-recovery/wireless-ap/) |

---

## Summary

No tenant device can join the network. `DVNTM-IOT` does not exist: CHG-0005 held the `iot` segment
out of `omada-wireless.yml` because its security model was undecided, and the PPSK test it ran was
torn down afterwards. The first real consumer, eds's LP stand, is already built to join
`DVNTM-IOT` — there is nothing there.

This creates that SSID as **PPSK**, and puts key issuance behind the Deevnet API so a tenant gets
its own Wi-Fi credential from `terraform apply`, with no operator touching the controller and no
tenant secret in the inventory vault.

## Goal

| | |
|---|---|
| `DVNTM-IOT` | exists, `security: 4`, VLAN 30, bound to a PPSK profile inventory declares |
| The profile | holds one key per tenant, written only by the Deevnet API |
| A tenant | runs `terraform apply`, gets back `ssid` and a sensitive `psk` |
| A device | flashed with those lands on `10.20.30.x` |
| `DVNTM`, `DVNTM-IOTV`, `DVNTM-GUEST` | unchanged, and still serving |

## What this is not

**It is not a migration.** `DVNTM-IOT` never existed and no device was ever on a shared key for it,
so there is no coexistence window and nothing to re-flash. ADR-0012's Consequences used to assume
otherwise; that entry is corrected. `DVNTM-IOTV` *does* have that problem and is deliberately out of
scope.

**It does not isolate tenants from each other.** Every IoT device shares VLAN 30 whatever tenant
owns it. The key decides which VLAN a device lands on, not which tenants it can reach. That is
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) question 4's accepted
position — isolation is best effort, credentials first — and until the broker's topic scoping exists,
two tenants' devices can reach each other at Layer 3.

**It does not register devices.** A key is per tenant per trust class, not per device; see
[ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3, amended for this change.

## Scope

- **In:** the `iot` segment, `DVNTM-IOT`, its PPSK profile, the API's `wifi-keys` routes, the
  `deevnet_iot_wifi_key` provider resource, and the `platform -> management` zone rule (declared,
  not applied).
- **Out:** `DVNTM-IOTV`; the device registry; broker accounts; client isolation; applying the zone
  policy.

## Risk and impact

1. **Adding an SSID re-applies the WLAN group to the AP.** This is the real exposure: it can drop
   associations across every SSID on that radio for a few seconds, including `DVNTM`, which carries
   household clients. Run it in a window and warn the household.
2. **The play still PATCHes the live AP** (name, static address) whenever it is adopted, and then
   waits on port 443. Idempotent, and it runs today, but it is a write to a live AP.
3. **Nothing existing can be rewritten or deleted.** The play matches SSIDs by name, creates only
   what is missing, and never deletes. `DVNTM`, `DVNTM-IOTV` and `DVNTM-GUEST` cannot be touched by
   it. This is a structural guarantee, which is why risk 1 is about radio reconfiguration rather
   than configuration loss.
4. **A wrong endpoint path fails before any write.** The play asserts every endpoint against the
   spec the running controller publishes and refuses to start otherwise.
5. **The controller is now in a tenant's apply path.** INC-0002 was a controller hang. A tenant's
   `terraform apply` will now fail on it — recoverably, since the row is kept and a retry resumes.

## Prerequisites

- [x] PPSK with per-key VLAN binding proven on this AP (CHG-0005 phase 6).
- [x] The Deevnet API deployed and serving tenants (CHG-0010).
- [ ] **The Owner creates a second Open API client** in the controller UI (Global View → Settings →
      Platform Integration → Open API), vaulted as `vault_omada_api_client_id` /
      `vault_omada_api_client_secret`. The API gets its own, separate from Ansible's: the permission
      is identical, but the blast radius, the rotation and the audit trail are not.
- [ ] A maintenance window for the AP, and the household warned.

## Procedure

Each phase has its own page, with Run, Verify and Undo. The undo is written before the change runs.

| Phase | What | Needs |
|---|---|---|
| [1. Recon](01-recon/) | Read the controller's spec; settle what the automation may call | Nothing — read-only |
| [2. Substrate](02-substrate/) | Create the profile and `DVNTM-IOT` | Maintenance window |
| [3. API](03-api/) | Deploy v0.3.0 with the controller credential | The Owner's Open API client |
| [4. Tenant](04-tenant/) | A tenant issues a key through Terraform | Phases 2 and 3 |
| [5. A client joins](05-device/) | Any wireless client joins with a tenant's key and lands on VLAN 30 | Someone at the site with a client |
| [6. Close-out](06-close-out/) | Correct the stale pages, retire the superseded playbook | Phase 5 |

[Undo](undo/) collects the reversal for every phase.

## Verification

Taken from the network, not from Ansible.

- A scan shows **four** SSIDs, and a real client on `DVNTM` keeps its association and address —
  checked on the client, not on the controller.
- The controller shows `DVNTM-IOT` at `security: 4`, bound to the `DVNTM-IOT` profile.
- `make wireless` run again reports nothing to create.
- A tenant's `terraform apply` returns `ssid` and a `psk`; a second apply is a no-op.
- **The key is deleted from the controller by hand and the next apply restores the identical
  `psk`** — the restore-not-recreate proof, and it needs no hardware.
- A client joining `DVNTM-IOT` with a tenant's key takes a lease in `10.20.30.0/24` and appears on
  the AP's client list. Any client will do — what is proven is that the key authenticates and that
  the key, not the SSID, decides the VLAN.

## Outcome

**Everything but phase 5 is done, 2026-09-18.** A tenant asks for a Wi-Fi key in its own Terraform
and gets back an SSID and a password; no operator touches the controller, and no tenant Wi-Fi key
exists in the substrate vault any more.

- `DVNTM-IOT` is on air: VLAN 30, `security: 4`, bound to a profile inventory created **empty**. The
  three shared-key SSIDs were untouched and the AP stayed connected.
- The API issues, re-applies, restores and revokes keys — v0.3.1 on `dv02prv001v01`, with its own
  Open API client, separate from Ansible's.
- `eds` holds `eds-devices` on VLAN 30, issued by its own `terraform apply`, with the key in its own
  state. `1 to add, 0 to change, 0 to destroy`, and the second plan is clean.
- `deevnet_wifi_psk.iot` is deleted, not migrated away from.

**One defect found and fixed.** Revoking a tenant's only key failed: the controller refuses to let
`delete-psk` empty a PPSK profile (`errorCode -34044`) even though it will happily *create* one
empty. Fixed in v0.3.1 with a placeholder entry and verified round-trip on the real controller.
Phase 3 has the detail, including why the alternative fix was rejected on concurrency grounds and
the second bug that writing the tests uncovered in the first version of it.

**Departures from the plan**, both recorded where they happened:

1. The preferred fix for that defect (`modifyPPSKProfile` with the remaining keys) was **never
   tested**. Settling it needed a write to a shared device that the operator and I chose not to
   spend, because the alternative was structurally safer under concurrency anyway. Phase 3.
2. Phase 6 did **not** put the SSID names on the architecture page as planned. That page is
   implementation-agnostic by convention, so it gained the model and the names went to the access
   point page. Phase 6.

**Phase 5 remains**, and it is deliberately narrow: any wireless client joining with a tenant's key
and landing on `10.20.30.0/24`.

## Follow-ups

**Client isolation on `DVNTM-IOT` — deferred by the operator, 2026-09-18.** Every IoT device shares
VLAN 30 whatever tenant owns it, so a tenant's key decides where its devices land, not who they can
reach. Two tenants' devices can talk to each other at Layer 3 today.

- This is [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) question 4's
  accepted position — best effort, credentials first — but "best effort" is currently **no effort**:
  the isolation half of CHG-0005 phase 6 was never run.
- The documented route is Guest Network plus an EAP ACL permit, and it is awkward: Omada's
  per-SSID isolation is its Guest Network setting, which also blocks all of RFC 1918 — including the
  broker a device has to reach. There is no plain client-isolation switch in the SSID schema.
- The thing actually meant to keep owners apart is above Layer 3: per-tenant credentials, which this
  change delivers, and the broker's per-tenant topic scoping, which does not exist yet. So this
  follow-up is worth doing **after** the broker, not before.
- It needs its own change record: it touches an SSID that by then has devices on it.

**The eds application vertical is a separate effort, not a follow-up to this change.** A joined
device has nothing to talk to: VerneMQ on `dv02msg001v01` is built and empty, and no eds service is
packaged — there is no Containerfile. Standing up the broker, packaging the services and flashing the
LP stand against them is its own piece of work, and it is what
[ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3's device registry and broker
accounts are for. This change deliberately stops at the network credential.

**The `DVNTM-IOTV` conversion still needs its own change record.** It has a shared key and devices on
it, so unlike `DVNTM-IOT` it is a migration rather than a creation. The `security` drift check added
here will report the mismatch if someone declares it `ppsk` without converting it.

**Client isolation is deferred** — see the entry above; it belongs after the broker.

**Two `deevnet_iot_wifi_key` guards are covered by unit test only**, because this site serves one
trust class: that a key cannot change trust class, and that an unserved class is refused with the
served ones named. Both become live-testable when `iot_vendor` is served.
