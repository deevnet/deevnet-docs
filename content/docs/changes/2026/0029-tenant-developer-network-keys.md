---
title: "CHG-0029: One Key per Tenant on DVNTM-TD"
weight: -29
---

# CHG-0029: One Key per Tenant on DVNTM-TD

| | |
|---|---|
| **Date** | 2026-09-27 |
| **Change type** | Configuration |
| **Classification** | Disruptive |
| **Status** | **Complete, 2026-09-27.** `DVNTM-TD` has one key per tenant, issued at admission and adopted by the tenant; its computers are isolated from each other. The first key in the fresh profile worked on the first join. |
| **Window** | 2026-09-27, 15:04 to ~17:15 |
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
- API `v0.9.0` and provider `0.5.0`, shared with CHG-0028 and CHG-0030.
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

**One release carries all three changes.** The API and provider on `main` hold the code for
CHG-0028, CHG-0029 and CHG-0030 together, and each behavior is off until that change's own role or
inventory switch turns it on. So the first of the three to run tags and stages API `v0.9.0` and
provider `0.5.0`, and the others deploy that same release. If it is already staged, skip the tag.

```bash
cd deevnet-provisioning-api && git tag v0.9.0 && git push origin v0.9.0 && make stage   # unless staged
cd ../terraform-provider-deevnet && git tag v0.5.0 && git push origin v0.5.0 && make stage   # unless staged
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags deevnet-api --limit dv02prv001v01
ansible-playbook playbooks/site.yml --tags tenant-downloads --limit dv02obs001v01
```

**Verify:** the API reports `v0.9.0` or later, migration 0008 applied, and its environment has
`DEEVNET_ADMISSION_WIFI_CLASS=tenant_dev`. Its trust classes include `tenant_dev=DVNTM-TD:45`.

**Undo:** unset the switch: take `wifi_security` off `tenant_dev` in inventory and redeploy the
API role, so the API serves no `tenant_dev` class and admissions issue no key. Migration 0008 only
adds, so nothing needs reverting in the database.

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
page.

## Verification

The Goal, as a whole, from two laptops that have never held the old shared key.

## Undo

### Undo Step 3

Delete the two EAP ACLs, and delete the `DVNTM-TD` SSID in the controller. Then take
`wifi_security`, `wifi_ppsk_profile` and `wifi_client_isolation` out of `tenant_dev`, restore the
vault key, and apply the play. It recreates the SSID with the shared key. The profile can be left in
place.

## Outcome

Run from the Builder; the client tests from the operator's own computer and a phone. Times are
approximate.

| When | Steps | What happened |
|---|---|---|
| ~15:30 | 1 | A read-only check first: every decrypted vault file matched its committed plaintext (11 of 11 `SAME`). `deevnet_wifi_psk.tenant_dev` removed, the file re-encrypted, committed with inventory #61 |
| ~15:45 | 2 | A disabled UI rule with protocols "All" read back as **`protocols: [256]`**; recorded as `omada_acl_protocols_all` and the rule deleted |
| ~15:55 | 3 | Plan: profile `DVNTM-TD` to create, `DVNTM-TD` to recreate (security 3 → 4), two isolation ACLs. First apply created the profile with the placeholder, deleted and recreated the SSID, then **stopped** at the isolation check (see departures). After the fix, a second apply created the IP groups and ACLs: `allow gateway` (index 1, policy 1) ahead of `drop clients` (index 2, policy 0), both on the SSID, protocols `[256]`. A fresh plan wanted nothing |
| ~16:00 | 4 | API role: `DEEVNET_ADMISSION_WIFI_CLASS=tenant_dev`, trust classes `iot=DVNTM-IOT:30,tenant_dev=DVNTM-TD:45`, `/readyz` `200` (API `v0.9.1`, already live) |
| ~16:00 | 5 | Tenant **`cdeever`** admitted (no MAC). Its key joined `DVNTM-TD` **on the first try** (`10.20.45.50`): the first key in a freshly created profile works, which CHG-0013 phase 5 had found broken for a profile created empty |
| ~16:10 | 5 | Throwaway `tprobe2` admitted; a phone joined with its key. The Mac **could** reach the phone: the ACLs were on the controller, enabled and correct, but the AP had not applied them. After a force-provision of the AP, the Mac could no longer reach the phone (ping lost, `nc` unreachable), and `segment-check.sh DVNTM-TD` on the tenant's own key: **29 passed, 0 failed** (log below) |
| ~16:20 | 5 | `DELETE /v1/admissions/tprobe2`: `204`, then `404`. The phone could no longer join |
| ~16:50 | 5 | `cdeever` created from tdemo's reworked README on the operator's Mac. `GET …/cdeever/wifi-keys` lists **`admission`** (`tenant_dev`, `DVNTM-TD`) beside `devices` (`iot`): the admission key is the tenant's own. The tenant's backend workload took its key, and `ssh tenant@backend.cdeever…` worked |

{{< details "segment-check.sh DVNTM-TD on the tenant's own key, 2026-09-27" >}}
```text
Segment check: DVNTM-TD (from 10.20.45.50)
== Address and DNS
  PASS  lease 10.20.45.50
  PASS  api.mobile.deevnet.net -> 10.20.25.20
  PASS  tfstate.mobile.deevnet.net -> 10.20.25.20
  PASS  mqtt.mobile.deevnet.net -> 10.20.35.20
  PASS  downloads.mobile.deevnet.net -> 10.20.25.22
  PASS  REACH https://api.mobile.deevnet.net:8080 - HTTP 404 (TLS verified)
  PASS  REACH https://tfstate.mobile.deevnet.net:9000 - HTTP 403 (TLS verified)
  PASS  mqtt.mobile.deevnet.net:8883 TLS verified
  PASS  dv02obs001v01.mobile.deevnet.net:8427 TLS verified
  PASS  REACH https://dv02obs001v01.mobile.deevnet.net:3000 - HTTP 302 (TLS verified)
  PASS  REACH https://downloads.mobile.deevnet.net:8443 - HTTP 200 (TLS verified)
  PASS  internet (https://example.com 200)
  PASS  BLOCK obs-ssh(platform) 10.20.25.22:22
  PASS  BLOCK Builder-ssh(management) 10.20.99.95:22
  PASS  BLOCK router-GUI(management) 10.20.99.1:443
  PASS  BLOCK hypervisor-PVE(management) 10.20.99.21:8006
  PASS  BLOCK router-GUI-on-own-gateway 10.20.45.1:443
  PASS  BLOCK router-ssh-on-own-gateway 10.20.45.1:22
  PASS  BLOCK router-on-trusted 10.20.10.1:443
  PASS  BLOCK prv-ssh(platform) 10.20.25.20:22
  PASS  BLOCK prv-other-port(platform) 10.20.25.20:8200
  PASS  BLOCK msg-ssh(iot_backend) 10.20.35.20:22
  PASS  BLOCK broker-plaintext(iot_backend) 10.20.35.20:1883
  PASS  REACH tenant-workload-ssh(ADR-0028) 10.20.130.10:22 (open)
  PASS  BLOCK pi(iot,if-on) 10.20.30.11:22
  PASS  BLOCK pi(iot,if-on) 10.20.30.12:22
  PASS  BLOCK pi(iot,if-on) 10.20.30.13:22
  PASS  BLOCK pi(iot,if-on) 10.20.30.14:22
  PASS  BLOCK edge-router-admin(CHG-0023) 192.168.8.1:80

RESULT: DVNTM-TD - 29 passed, 0 failed
```
{{< /details >}}

### Departures from the plan

- **A play default hid inventory.** The wireless play declared `omada_acl_protocols_all: []` in its
  own `vars`, and play vars outrank group vars, so inventory's `[256]` never reached it. Step 3's
  first apply recreated the SSID and then stopped at the isolation check. The controller was
  consistent (profile and SSID made, ACLs not), and after the fix (net #41) a second apply finished.
- **The AP did not apply the isolation rules until it was force-provisioned.** The play now
  force-provisions the AP, through the documented `forceProvisionDevice`, whenever a run creates an
  SSID, a PPSK profile or an isolation rule, and never on a run that changes nothing (net #42).
- **The gateway does not answer ping** from `DVNTM-TD`. That is the router's policy for the segment,
  not the isolation rules; DHCP and DNS on it work.
- **Step 2's value went straight to `main`** (inventory `485b54f`) after a failed attempt left the
  working copy on `main`. The operator chose to keep it.
- **MAC binding was not tried on hardware.** The API, provider and controller support it; no key was
  bound.
- **Step 6 was not needed.** eds, tdemo and mabell have one owner, whose `cdeever` key covers them.
- **Newcomer snags** from the run are fixed in tdemo's README and `install-provider.sh`: the scripts
  were named but never fetched, `ssh_keys` went in as a string, and a silent 28 MB download looked
  like a hang.
- **Tenant `cdeever` is kept** as a live tenant.

## Follow-ups

- [ ] TLS on the state store: ADR-0029 §4 depends on it.
- [x] CHG-0013's defect is fixed by creating profiles non-empty: proven by step 5's first join.
- [ ] A per-session key expiry for meetups (ADR-0029 open question 1).
