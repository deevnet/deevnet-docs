---
title: "CHG-0022: The Tenant Dev Network"
weight: 22
---

# CHG-0022: The Tenant Dev Network

| | |
|---|---|
| **Date** | 2026-09-23 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **Complete, 2026-09-23.** A laptop on `DVNTM-TD` took `10.20.45.50`, reached the API, the state store and the broker over TLS against the site CA, and was refused at all 12 internal targets it should not reach (21/21). `terraform plan` and an MQTT login from the segment were not run; see [Outcome](#outcome). |
| **Window** | 2026-09-23 18:02 to 18:17 (switch to SSID); verification from a laptop afterwards |
| **Site** | mobile |
| **Systems** | `dv02acc001p01` (switch), `dv02cor002p01` (core router), `dv02nms001v01` (wireless controller) and `dv02wap001p01` (AP). Reached, not changed: `dv02prv001v01` (API, state store) and `dv02msg001v01` (broker). |
| **Automation** | `deevnet.net`: `make switch`, `make opnsense`, `make migration-opnsense-firewall`, `make wireless`, run against `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. A new segment adds only pass rules for its own traffic. What is most likely to go wrong is the firewall apply: it rewrites the managed ruleset, and a bad apply rolls back when the post-apply reachability checks fail ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)). |
| **Related changes** | [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (zone policy), [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) (SSIDs from inventory) |
| **Related incidents** | [INC-0004](/docs/incidents/) is open against the core router's `re0`. Don't schedule this in a window where that NIC is misbehaving. |
| **Related runbooks** | [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/), [Tenant Admission §3](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

A tenant's Terraform talks to the Deevnet API on every run, and after the first apply it talks to the
state store as well. Today only a **trusted seat** reaches either: a shell on the Builder, or a laptop
on the trusted network. Guest is internet-only and IoT can't reach the API.

Both seats give a visitor far more than the API. The trusted zone passes to management (a declared
lab exception), storage, IoT, IoT backend and tenant transit. A Builder shell is the automation host
itself.

This change adds a **tenant dev** segment, `tenant_dev`: VLAN 45, `10.20.45.0/24`, SSID `DVNTM-TD`.
Inside the site it reaches three services and nothing else:

| Service | Name | Address | Port |
|---|---|---|---|
| Deevnet API | `api.mobile.deevnet.net` | `dv02prv001v01`, 10.20.25.20 | 8080 (HTTPS) |
| Terraform state store | `tfstate.mobile.deevnet.net` | `dv02prv001v01`, 10.20.25.20 | 9000 (HTTP) |
| MQTT broker | `mqtt.mobile.deevnet.net` | `dv02msg001v01`, 10.20.35.20 | 8883 (TLS) |

It also gets the gateway's DNS, DHCP and NTP (generated for every zone) and the internet.

## Goal

- A laptop on `DVNTM-TD` gets a `10.20.45.x` lease and resolves the three names through `10.20.45.1`.
- From that laptop, `terraform plan` in an existing tenant repository completes (the API and the state
  store), and an MQTT client connects on 8883 with a tenant's broker account.
- From that laptop, everything else inside the site is refused (listed under [Verification](#verification)).
- The router's managed ruleset has five new rules and no other drift. Every existing SSID still works.

## Scope

**In scope:** the VLAN on the switch and the AP trunk, the router interface, its DHCP scope and the
zone's rules, the SSID, and the docs that tell a tenant where to apply from.

**Out of scope:**
- Client isolation between laptops on `DVNTM-TD` (see [Risk and impact](#risk-and-impact)).
- The downloadable provider, the other half of the same "coming soon" item.
- The internet rule's gap (see [Follow-ups](#follow-ups)).

## Design notes

- **A shared key, not PPSK.** A segment with `wifi_security: ppsk` becomes a trust class in the API,
  and the API then issues per-tenant keys on it. This segment carries laptops, not devices, and
  isn't a trust class. The key is `deevnet_wifi_psk.tenant_dev` in `group_vars/all/vault.yml`.
- **Omada guest mode is off.** The playbook sets the guest flag only on the `guest` key. Guest mode would
  also block the private addresses this segment exists to reach.
- **No role code changes.** A zone is a `deevnet_vlans` key. The router's rules, DHCP scope and
  gateway services all derive from it.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Firewall apply breaks an existing path | core router | The post-apply reachability checks roll the apply back. Read the plan output before applying: +5 policy rules, the new zone's generated gateway and internet rules, and nothing else |
| The SSID is created with the wrong settings | controller | The playbook never rewrites an existing SSID. Read the plan output before `APPLY=1`. The undo is to delete the SSID and run again |
| Laptops on the SSID can reach each other | AP | Not guarded. Accepted: this segment is for tenant developers at a session the operator is running, not for the public |
| The state store is plain HTTP on this segment | `dv02prv001v01` | Not guarded. Its keys are per tenant. A known gap, which ADR-0016 says should be TLS |
| No NAT or DNS for the new interface | core router | Step 3 verifies both on the router before the SSID exists |

## Prerequisites

- [ ] `ansible-inventory-deevnet` branch `chg-0022-tenant-dev-network` merged, **including the
      encrypted `group_vars/all/vault.yml` holding `deevnet_wifi_psk.tenant_dev`**
- [ ] Vault decrypted, collections built (`make deps install-dev`)
- [ ] GUI access to the core router (for the interface assignment)
- [ ] INC-0004: `re0` quiet for the window

## Procedure

### Step 1: The switch

Creates VLAN 45 and adds it to the AP trunk `gi1/0/4`. The uplink `gi1/0/1` carries every VLAN
already. Not disruptive.

**Run:**

```bash
make switch
```

**Verify:**

1. On the switch, `show vlan` lists 45, and `show interface switchport gigabitEthernet 1/0/4` has 45 tagged.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: The router interface

`make opnsense` creates the VLAN device on `re0`, then **pauses** for the interface assignment. This
has to be done in the GUI because OPNsense has no API for it: assign `vlan0.45`, enable it, set
`10.20.45.1/24`, and continue. It then creates the Kea subnet and DNS. The firewall step only plans
in this run.

**Run:**

```bash
make opnsense
```

**Verify:**

1. The interface is up with `10.20.45.1/24`. Kea has a subnet `10.20.45.0/24` with pool `.50-.250`,
   DNS `10.20.45.1`.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: The firewall rules

**Run:**

```bash
make migration-opnsense-firewall                                  # plan
make migration-opnsense-firewall EXTRA_ARGS="-e firewall_apply=true"
```

**Verify:**

1. The plan output adds the three `tenant_dev ->` service rules, `management -> tenant_dev`, the zone's
   gateway DNS/DHCP/NTP rules and its internet rule, with **no other changes**.
2. After apply, the post-apply reachability checks pass.
3. On the router: automatic outbound NAT covers `10.20.45.0/24`, and Unbound answers queries from it.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: The SSID

**Run:**

```bash
make wireless            # plan
make wireless APPLY=1
```

**Verify:**

1. The plan output shows one new LAN network (VLAN 45) and one new SSID `DVNTM-TD` with WPA2
   personal and guest mode off. Nothing else changes.
2. `DVNTM-TD` is broadcasting after apply.

**Undo:** [Undo Step 4](#undo-step-4)

## Verification

From a real laptop on `DVNTM-TD`, not from the Builder:

| Check | Expect |
|---|---|
| DHCP lease | `10.20.45.50-250`, DNS `10.20.45.1` |
| `dig api.mobile.deevnet.net`, `tfstate…`, `mqtt…` | answers from `10.20.45.1` |
| `curl --cacert site-ca.pem https://api.mobile.deevnet.net:8080/` | an HTTP response |
| `terraform plan` in `deevnet-tenant-tdemo` | completes (API and state store) |
| MQTT connect on 8883 with a tenant's account | connects |
| An internet host | reachable |
| **Must fail:** ssh to the Builder (management) | times out |
| **Must fail:** `10.20.25.20:22`, and any other port on 10.20.25.x | times out |
| **Must fail:** `10.20.35.20:22` | times out |
| **Must fail:** a tenant workload in `10.20.128.0/18` | times out |
| **Must fail:** a trusted host (10.20.10.x) | times out |

Regression: the trusted, IoT and guest SSIDs still associate, and guest is still internet-only.

## Undo

In reverse order. Nothing in this change is a point of no return.

### Undo Step 4

Delete `DVNTM-TD` and its LAN network in the controller. Remove `wifi_ssid` from the `tenant_dev`
entry so the playbook doesn't recreate them.

### Undo Step 3

Remove the `tenant_dev` entries from `firewall.yml` and apply with `firewall_delete_unmanaged=true`
(read the plan: only the tenant_dev rules may be candidates).

### Undo Step 2

Disable and unassign the interface in the GUI, delete `vlan0.45`, and delete the Kea subnet.

### Undo Step 1

Remove 45 from `gi1/0/4` and delete the VLAN on the switch. Revert the inventory branch.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 18:02 | 1 | `make switch`. VLAN 45 `tenant_dev` tagged on `gi1/0/1` and `gi1/0/4`; the VLAN table otherwise identical before and after |
| 18:05 | 2 | VLAN device `vlan013` created on `re0`. Interface assigned in the GUI as `opt11` (`tenant_dev`), `10.20.45.1/24`; the role then reported all 10 VLAN interfaces correct |
| 18:12 | 2 | `make dhcp`. Kea subnet `10.20.45.0/24`, pool `.50-.250`, DNS and router `10.20.45.1`. On the router: automatic outbound NAT already listed `opt11`; Unbound listens on all interfaces, default ACL allow |
| 18:15 | 3 | Plan: ADD 8, UPDATE 0 of 57, DELETE 0. Applied; all 6 required paths still answered, no rollback. Re-plan: 0 / 0 of 65 / 0 |
| 18:17 | 4 | Plan: one network (45), one SSID `DVNTM-TD`, no other SSID or key drift. Applied; a re-plan has nothing to create |
| after | Verification | From a MacBook on `DVNTM-TD`: 21 passed, 0 failed (below) |

**Verification, from a real client:**

| Check | Result |
|---|---|
| Lease, DNS | `10.20.45.50`, DNS `10.20.45.1`; `api`, `tfstate`, `mqtt` resolve to `10.20.25.20`, `10.20.25.20`, `10.20.35.20` |
| API | HTTPS on 8080 verified against the site CA, HTTP 404 on `/` |
| State store | HTTP 403 on 9000 (no credentials) |
| Broker | TLS on 8883 verified against the site CA |
| Internet | `https://example.com` 200 |
| Blocked (timeout, not refused) | Builder :22, router :443 on management, hypervisor :8006, **the router's own `10.20.45.1` on :443 and :22**, router on trusted :443, `dv02prv001v01` :22 and :8200, `dv02msg001v01` :22 and :1883, a Pi on IoT :22, eds's workload `10.20.130.10` :22 |
| Edge router `192.168.8.1:80` | **open** - the known `!10.20.0.0/16` gap, see Follow-ups |

A refused connection would have meant the packet reached the host, so the blocked checks count
only a timeout as a pass.

### Departures from the plan

- Step 2 was split. `make opnsense` would have carried on into the firewall role; instead
  `make migration-opnsense-vlans` created the VLAN device, the interface was assigned, and
  `make dhcp` ran on its own. `make dns` was not run: the segment adds no names.
- The DHCP run also rewrote all 15 existing reservations with the values they already had. This is
  the role's known idempotency defect (CHG-0008 follow-up), not this change.
- Kea now listens on every interface but WAN; it had been listening on 11 of 13. Only interfaces
  with a subnet and pool can lease, and those are unchanged apart from `10.20.45.0/24`.
- **Not tested:** `terraform plan` from the segment (the API and state store were proven at HTTP
  and TLS, not through Terraform), an MQTT *login* with a tenant account (the TLS handshake was
  proven), and association to the other SSIDs afterwards (their controller config shows no drift).

## Follow-ups

- [x] Tenant-facing pages: [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/),
      [Tenant Admission §3](/docs/runbook/substrate/tenant-admission/),
      [Coming Soon](/docs/runbook/tenant/services/coming-soon/), troubleshooting and the
      [network reference](/docs/runbook/substrate/network/network-reference/) - updated with this record.
- [ ] Run `terraform plan` and an MQTT login from `DVNTM-TD` the first time a tenant uses it.
- [x] **The internet rule is `!10.20.0.0/16`, not "not RFC 1918"** — fixed by [CHG-0023](/docs/changes/2026/0023-internet-means-internet/); `192.168.8.1` now times out from `DVNTM-TD`. Guest, and now tenant_dev, can reach
      `192.168.0.0/16` and `172.16.0.0/12`, including the edge router's admin at `192.168.8.1`. This
      predates this change.
- [ ] Client isolation on `DVNTM-TD`, if the segment is ever offered beyond an operator-run session.
