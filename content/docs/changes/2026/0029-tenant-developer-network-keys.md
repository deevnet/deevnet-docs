---
title: "CHG-0029: One Key per Tenant on DVNTM-TD"
weight: -29
---

# CHG-0029: One Key per Tenant on DVNTM-TD

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Disruptive |
| **Status** | Planned |
| **Window** | Unscheduled |
| **Site** | mobile |
| **Systems** | `dv02nms001v01` (Omada controller: the `DVNTM-TD` SSID, a new PPSK profile, two IP groups, two EAP ACLs), `dv02wap001p01` (the AP it provisions), `dv02prv001v01` (the API, migration 0008) |
| **Automation** | `deevnet.net` `playbooks/omada-wireless.yml`; `deevnet-provisioning-api` `make stage`; `terraform-provider-deevnet` `make stage`; `deevnet.mgmt` `site.yml --tags deevnet-api` and `--tags tenant-downloads`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium — the first key in a fresh profile is the CHG-0013 dead-on-arrival case, and this change is the first test of its fix |
| **Related changes** | [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/), [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/), [CHG-0028](/docs/changes/2026/0028-tenant-workload-login/) |
| **Related incidents** | None |
| **Related runbooks** | [Tenant Admission](/docs/runbook/substrate/tenant-admission/), [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) |

---

## Summary

Implements [ADR-0029](/docs/architecture/decisions/tenant-networking/0029-tenant-developer-network-keys/).

`DVNTM-TD` has one WPA2-Personal key shared by every tenant, and laptops on it can reach each other.
A tenant holding that key can decrypt another's traffic, and that traffic includes the other tenant's
Terraform state, which crosses the segment over plain HTTP. After this change each tenant has its
own key:

- The **first** key comes with its admission.
- A tenant can **issue itself more**, one per laptop, optionally bound to the laptop's MAC.
- A deleted tenant's keys **stop working**.
- Laptops on the segment are **isolated** from each other.

The playbook's PPSK profile creation changes as well. A new profile now starts with a placeholder
key instead of empty, which is CHG-0013's proposed fix for its first-key-dead-on-arrival defect. The
new `DVNTM-TD` profile is the first test of that fix.

## Goal

- `DVNTM-TD` is security 4 (PPSK), bound to profile `DVNTM-TD`, VLAN 45. The shared key no longer
  associates.
- `POST /v1/admissions` returns `wifi.ssid = "DVNTM-TD"` and a key, and a laptop joins with that key
  **the first time**, taking a `10.20.45.x` address.
- A key bound to a MAC joins from that laptop and is refused from another.
- Two laptops joined with two tenants' keys cannot reach each other (ping, TCP), and both still
  reach the API, broker, log store, Grafana and downloads.
- Revoking an unused admission, or deleting a tenant, stops its key from associating.
- A tenant issues itself a `tenant_dev` key with `deevnet_iot_wifi_key`, and it works.
- eds, tdemo and mabell each hold a `tenant_dev` key.

## Scope

**In scope:**
- The SSID's conversion to PPSK, the profile, isolation and the vault key's removal.
- API `v0.10.0` and provider `0.6.0`.
- Keys for the three existing tenants.
- The tenant-facing pages.

**Out of scope:**
- TLS on the state store (the next change, and the reason isolation is not the whole answer).
- A per-session expiry for keys.
- WPA3.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The first key in the new profile does not authenticate (CHG-0013's defect) | AP | Step 3 creates the profile with the placeholder before the SSID exists. If a key still fails, force-provision the AP from the controller, and record that the fix did not hold |
| The isolation drop also blocks the gateway | AP | The allow rule is created first and the play refuses a half-built pair. Step 5 checks DHCP, DNS and the API from a joined laptop |
| The wrong protocol value makes the ACL match nothing, or everything | controller | Step 1 reads the value off a rule the controller itself built. Step 5 tests isolation *and* reachability |
| Everyone on `DVNTM-TD` is disconnected | AP | Intended. Only the operator is on it today |
| The API serves `tenant_dev` before the profile exists | API | Step 4 (API) runs after Step 3 (controller) |

## Prerequisites

- [ ] PRs merged: `deevnet-provisioning-api` `chg-0029-tenant-dev-keys`, `terraform-provider-deevnet`
      `chg-0029-wifi-key-mac`, `ansible-collection-deevnet.net` `chg-0029-tenant-dev-ppsk`,
      `ansible-collection-deevnet.mgmt` `chg-0029-admission-wifi`, `ansible-inventory-deevnet`
      `chg-0029-tenant-dev-ppsk`
- [ ] Vault decrypted, collections built (`make deps install-dev`)
- [ ] Two laptops. One must be off `DVNTM-TD` (on trusted) to run the API calls in step 4
- [ ] INC-0004: `re0` quiet for the window

## Procedure

### Step 1: Take the shared key out of the vault

**Run:** remove `deevnet_wifi_psk.tenant_dev` from `mobile/group_vars/all/vault.yml`, then
`make vault`, commit and push.

**Verify:** `make wireless` plans without refusing `tenant_dev`. The play refuses a PPSK segment that still has a shared key, so this step comes first.

**Undo:** restore the key from git history.

### Step 2: Read the "all protocols" value off the controller

The spec defers ACL protocol values to an access guide it does not publish, so the value is read
back, not assumed.

**Run:** in the controller UI, create one EAP ACL with protocol **All** (any source, any
destination, **disabled**). Then plan the wireless play, which reports every EAP ACL with its
protocols:

```bash
make wireless          # plan: read eap_acls_on_controller
```

Put the value it shows into `mobile/group_vars/network_controllers/vars.yml` as
`omada_acl_protocols_all: [<value>]`, commit it, and delete the UI rule.

**Verify:** the plan shows the rule's `protocols`, and after the delete it no longer lists it.

**Undo:** delete the UI rule.

### Step 3: Convert the SSID, and isolate it

**Run** (in `ansible-collection-deevnet.net`):

```bash
make wireless                                            # plan
ansible-playbook playbooks/omada-wireless.yml -e omada_apply=true \
  -e '{"omada_recreate_ssids":["DVNTM-TD"]}'
```

**Verify:**

1. The plan shows exactly these changes and nothing else:
   - `ppsk_profiles_to_create: [DVNTM-TD]`
   - `ssids_that_would_be_recreated: [DVNTM-TD]`
   - two `isolation_acls_to_create`
2. After the apply, the controller shows:
   - `DVNTM-TD` as PPSK, bound to profile `DVNTM-TD`, which holds only `DEEVNET-PLACEHOLDER-DO-NOT-USE`;
   - the two IP groups;
   - `DVNTM-TD isolation: allow gateway` ahead of `DVNTM-TD isolation: drop clients`.
3. The old shared key no longer associates.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Deploy the API and provider

**Run:**

```bash
cd deevnet-provisioning-api && git tag v0.10.0 && git push origin v0.10.0 && make stage
cd ../terraform-provider-deevnet && git tag v0.6.0 && git push origin v0.6.0 && make stage
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags deevnet-api --limit dv02prv001v01
ansible-playbook playbooks/site.yml --tags tenant-downloads --limit dv02obs001v01
```

**Verify:** the API reports `v0.10.0`, migration 0008 applied, and its environment has
`DEEVNET_ADMISSION_WIFI_CLASS=tenant_dev`. Its trust classes include `tenant_dev=DVNTM-TD:45`.

**Undo:** redeploy `v0.8.1` (or `v0.9.0` if CHG-0028 has run). Migration 0008 only adds, so the older
API ignores it.

### Step 5: Prove it with real laptops

**Run**, from the trusted laptop, with the operator token:

1. `POST /v1/admissions {"name":"tprobe","mac":"<laptop A's DVNTM-TD MAC>"}`.
2. Join laptop A to `DVNTM-TD` with the returned key.

**Verify:**

1. Laptop A associates **first time** and takes a `10.20.45.x` address. This is the CHG-0013 proof:
   a fresh profile, placeholder first, then a real key. The placeholder is now gone from the profile.
2. Laptop B, with the same key, is refused, because the key is bound to A's MAC.
3. From laptop A, `tenant-check.sh` passes, and `segment-check.sh` shows the same reach as before the change.
4. Admit `tprobe2` with no MAC and join laptop B with its key. A and B cannot ping each other, and
   `nc -zv <other laptop> 22` times out, while both still reach the API.
5. `DELETE /v1/admissions/tprobe2`, and B drops off within a reconnect.
6. On laptop A, create `tprobe` with its enrollment token. `GET /v1/tenants/tprobe/wifi-keys` lists
   `admission`. Destroy `tprobe`, and A can no longer associate.

**Undo:** nothing to undo; the probes delete themselves.

### Step 6: Keys for the existing tenants

**Run:** for eds, tdemo and mabell, with the operator token:
`POST /v1/tenants/<t>/wifi-keys {"name":"laptop","trust_class":"tenant_dev"}`. Hand each owner their
key.

**Verify:** each owner's laptop joins, and `terraform plan` runs from it. This closes CHG-0022's
never-run follow-up.

**Undo:** `DELETE` the keys.

### Step 7: The tenant-facing pages

**Run:** merge the tenant-guide PR: Before You Start, Tenant Admission §3, the Wi-Fi keys service
page and CARPE's laptop setup.

## Verification

The Goal, as a whole, from two laptops that have never held the old shared key.

## Undo

### Undo Step 3

Delete the two EAP ACLs, and delete the `DVNTM-TD` SSID in the controller. Then take
`wifi_security`, `wifi_ppsk_profile` and `wifi_client_isolation` out of `tenant_dev`, restore the
vault key, and apply the play. It recreates the SSID with the shared key. The profile can be left in
place.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] TLS on the state store: ADR-0029 §4 depends on it.
- [ ] If step 5.1 passed, record CHG-0013's defect as fixed, by creating profiles non-empty.
- [ ] A per-session key expiry for meetups (ADR-0029 open question 1).
