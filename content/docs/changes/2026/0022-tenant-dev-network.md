---
title: "CHG-0022: The Tenant Dev Network"
weight: 22
---

# CHG-0022: The Tenant Dev Network

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | Planned. Inventory is on branch `chg-0022-tenant-dev-network` in `ansible-inventory-deevnet`; nothing has reached a device. |
| **Window** | Not yet scheduled. About an hour, including the GUI step on the router. |
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
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] When Complete: [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) gets a
      `DVNTM-TD` row and drops its "coming soon" hint; trusted seats become the fallback. Also
      [Tenant Admission §3](/docs/runbook/substrate/tenant-admission/),
      [Coming Soon](/docs/runbook/tenant/services/coming-soon/) (the network half),
      troubleshooting's API-timeout row and the
      [network reference](/docs/runbook/substrate/network/network-reference/).
- [ ] **The internet rule is `!10.20.0.0/16`, not "not RFC 1918".** Guest, and now tenant_dev, can reach
      `192.168.0.0/16` and `172.16.0.0/12`, including the edge router's admin at `192.168.8.1`. This
      predates this change.
- [ ] Client isolation on `DVNTM-TD`, if the segment is ever offered beyond an operator-run session.
