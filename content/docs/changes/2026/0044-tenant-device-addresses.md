---
title: "CHG-0044: Fixed Addresses for Tenants' Devices"
weight: -44
---

# CHG-0044: Fixed Addresses for Tenants' Devices

| | |
|---|---|
| **Date** | 2026-10-06 |
| **Change type** | Deployment · Configuration · Migration |
| **Classification** | Structural |
| **Status** | In progress |
| **Window** | Started 2026-10-06. Before [CHG-0034](/docs/changes/2026/0034-device-certificates/), which it doesn't block |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (the core router's DHCP server), `dv02prv001v01` (the Deevnet API), the tenant DNS server; the provider; the `mabell` tenant and its gateway |
| **Automation** | `deevnet-provisioning-api`, `terraform-provider-deevnet`, `deevnet.net` `dhcp.yml` and `dns.yml`, `deevnet.mgmt` `site.yml --limit deevnet_api`, the `mobile` inventory |
| **Risk** | Medium. Most likely to go wrong: moving the IoT network's dynamic pool gives every device on it a new address at its next renewal |
| **Related changes** | [CHG-0014](/docs/changes/2026/0014-tenant-device-registry/) (the registry this builds on), [CHG-0038](/docs/changes/2026/0038-reconcile-restores-everything/) (narrows the router credential this widens the use of), [CHG-0034](/docs/changes/2026/0034-device-certificates/) |
| **Related incidents** | None |
| **Related runbooks** | [Devices and MQTT](/docs/runbook/tenant/services/devices-and-mqtt/), [Connect a Device](/docs/runbook/tenant/connect-a-device/), [Network Reference](/docs/runbook/substrate/network/network-reference/) |

---

## Summary

A tenant's device leases whatever the IoT network's pool gives it, and the one device with a fixed
address, the Ma Bell gateway, has it as a substrate host in inventory.
[ADR-0035](/docs/architecture/decisions/edge-devices/0035-fixed-address-for-a-tenant-device/) makes a
fixed address a tenant service: a tenant asks the Deevnet API for one for a device it registered with
a MAC, the API reserves it on the router's DHCP server and publishes the device's name in the
tenant's zone.

This change builds that, rearranges the IoT network to make room for it, and moves the Ma Bell
gateway out of inventory to its tenant as the first device to use it.

## Goal

- The IoT network is in three parts: substrate hosts below `.25`, tenants' device addresses from
  `.25` to `.200`, the dynamic pool from `.201` to `.254`.
- A tenant's Terraform reserves an address for a registered device and gets back the address and
  the device's name.
- The Ma Bell gateway is not in inventory. It holds an address its tenant reserved, and resolves as
  a name in its tenant's zone.
- The router's DHCP role and the API each leave the other's reservations alone.
- A second apply of the tenant plans nothing, and a re-apply after the API's record is deleted asks
  for the same address.
- ADR-0035 is Accepted.

## Scope

**In scope:** the API route and the provider resource; the DHCP role's pool update and ownership
guard; the inventory's IoT ranges; the Ma Bell gateway's move.
**Out of scope:** any firewall rule (none changes); reverse DNS for a device's address, which is
ADR-0035's open question 1; a tenant range on the vendor-device network; narrowing the API's router
credential, which is CHG-0038.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Devices on the old pool change address | the IoT network | Expected, once, at each device's next renewal. Devices dial the broker by name and reconnect. Done in a window; the Pi lab's reservations don't move |
| The pool update resets other settings of the subnet | the router | The role sends the pool only, reads the subnet back and fails the run if its routers option or subnet changed. Proven against a stand-in that resets them |
| The role takes over a tenant's reservation | the router | The role stops when an inventory MAC is reserved under another description. Proven by removing the guard and watching it happen |
| The API reserves a substrate host's MAC or address | the router | The API refuses a MAC or address any other reservation on the subnet holds; the router's own model rejects a duplicate as well |
| The gateway is unreachable between leaving inventory and its tenant's apply | the gateway | It leases from the pool in between, and its broker connection doesn't depend on its address. Steps 4 and 5 run back to back |
| Something still dials `bellgw` or `mabell` in the substrate zone | operators | Checked before step 4; the new name is handed over with the change |
| An address is handed out while an old lease still holds it | the IoT network | Allocation starts at `.25` and old leases were at `.100` and above; they expire long before allocation gets there |

## Prerequisites

- [x] The pull requests merged: API, provider, `deevnet.net`, `deevnet.mgmt`, and the inventory's
  range change. The inventory's removal of the gateway merged with them, ahead of step 4; nothing
  on the router changes until the pruning runs in that step
- [x] API v0.10.0 and provider v0.6.0 tagged and staged
- [x] Vault decrypted, collections built
- [x] The `mabell` tenant's agreement, and its repository's pull request for the address, merged
- [ ] The items under [To discover](#to-discover) answered

## Procedure

### Step 1: Read the router

Read-only. Confirms what the next steps assume about this build.

**Run:**

```bash
cd deevnet-provisioning-api
DEEVNET_TEST_OPNSENSE_URL=https://<router>/api DEEVNET_TEST_OPNSENSE_SUBNET=10.20.30.0/24 \
  go test ./internal/backend/opnsense/ -run RealRouter -v     # key and secret from the vault, in the environment
cd ../ansible-collection-deevnet.net
ansible-playbook playbooks/dhcp.yml --check
```

**Verify:**

1. The test lists every reservation with a MAC, an address and a description, and resolves the IoT
   subnet.
2. The check run reports one pool that differs, IoT's, and no other change it didn't report before.

**Result, 2026-10-06:** passed.

- The API's client read all 15 reservations, each with a MAC, an address and a description, and
  resolved the IoT subnet. Every row is inventory's.
- The check run reported one change: IoT's pool is `10.20.30.100 - 10.20.30.200` and inventory says
  `10.20.30.201 - 10.20.30.254`. It wrote nothing.
- The role's new ownership check passed: no inventory MAC is reserved under another description.
- The run named the gateway's reservation as no longer declared and left it in place, as expected
  until step 4.

### Step 2: Move the pool

Disruptive to devices on the IoT pool: each takes a new address at its next renewal.

**Run:**

```bash
ansible-playbook playbooks/dhcp.yml
```

**Verify:**

1. The run passes its own read-back of the IoT subnet.
2. The router shows the IoT pool as `.201` to `.254`, and the Pi lab's reservations unchanged.
3. A second run reports no pool change.
4. A device that rejoins gets an address in the new pool.

**Result, 2026-10-06:** passed, except item 4, which was not observed.

- The pool went from `10.20.30.100 - 10.20.30.200` to `10.20.30.201 - 10.20.30.254`.
- The role's read-back passed: the subnet and its routers option were unchanged. This build's
  subnet update leaves alone what it isn't sent.
- The four Pi lab reservations and the gateway's were unchanged, and a second run reported no pool
  change.
- No device was on the pool to rejoin, so item 4 waits for the first one that does.

**Undo:** set the old range in inventory and run the playbook again.

### Step 3: Deploy the API and stage the provider

Not disruptive: nothing a running device depends on.

**Run:**

```bash
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit deevnet_api
```

**Verify:**

1. `/version` answers v0.10.0.
2. As the operator, against a throwaway device in `tdemo`:
   - a device with a MAC is given `10.20.30.25`, and the router shows the reservation described
     `Deevnet API - tdemo/<device>`;
   - its name resolves through the router;
   - an address outside the range is refused with `400`, and a Pi's MAC with `409`;
   - the same MAC from a second tenant is refused with `409`, naming nobody.
3. The address is removed again, and the router no longer shows it.
4. `ansible-playbook playbooks/dhcp.yml` in `deevnet.net`, run while the test reservation exists,
   leaves it alone.

**Result, 2026-10-06:** passed.

- `/version` answers v0.10.0, and the role confirmed the running version is the pinned one.
- A throwaway device in `tdemo` was given `10.20.30.25`; the router showed it as
  `Deevnet API - tdemo/chg44`, hostname `tdemo-chg44`. Asking again returned the same address.
- `chg44.tdemo.mobile.deevnet.net` resolved through the router to `10.20.30.25`, with no PTR.
- Refused as designed: an address in the dynamic pool (`400`); a Pi lab host's MAC (`409`, and no
  record left behind); the same MAC from the `cdeever` tenant (`409`, naming nobody).
- A second name for the address was accepted from `tdemo` and refused from `cdeever`. The address
  could not be given back while that name pointed at it.
- A real run of the DHCP role, with the test reservation present, left it untouched.
- Everything was removed afterwards: the router has no reservation at `.25`, the tenant DNS server
  answers NXDOMAIN for both names, and `tdemo` has no devices. The router's resolver kept the
  answer cached for a few minutes more.
- Provider v0.6.0 is staged on the Builder and installed in the control host's local mirror. The
  tenant downloads site has not been refreshed with it.

**Undo:** redeploy v0.9.1. A reservation left behind is removed in the router's UI by its
description.

### Step 4: The gateway leaves inventory

The gateway's reservation and its names in the substrate's zone are removed.

**Run:** merge the inventory pull request that removes `dv02bgw001e01`, then:

```bash
cd ../ansible-collection-deevnet.net
ansible-playbook playbooks/dhcp.yml -e dhcp_delete_unmanaged=true
ansible-playbook playbooks/dns.yml -e dns_delete_unmanaged=true
```

**Verify:**

1. The router has no reservation for the gateway's MAC.
2. `dv02bgw001e01`, `bellgw` and `mabell` no longer resolve in `mobile.deevnet.net`.

**Result, 2026-10-06:** passed. A check run first showed the prune would remove exactly one
reservation, one host override and two aliases, all the gateway's. After the real run the router
holds no reservation for the gateway's MAC, none of the three names resolves, and the `mabell`
tenant's own zone still does.

**Undo:** revert the inventory commit and run both playbooks.

### Step 5: The tenant reserves the gateway's address

Run by the tenant, from its own repository: the provider pinned to `~> 0.6`, the gateway's MAC on its
device, and one address resource.

**Verify:**

1. The apply reports an address in `.25` to `.200` and the name `ma-bell-gw-01.mabell.mobile.deevnet.net`.
2. The router shows the reservation, described `Deevnet API - mabell/ma-bell-gw-01`.
3. The gateway, after its next renewal or a restart, holds that address and answers at that name
   from an operator network.
4. A second apply plans nothing.

**Undo:** destroy the address resource; the gateway returns to the pool.

### Step 6: Restore drill

**Run:** as the operator, delete the gateway's address through the API, then have the tenant plan and
apply.

**Verify:**

1. The plan shows the address resource changing, with the same address.
2. After the apply the gateway's address is the one it had.

## Verification

Steps 3, 5 and 6 pass; the firewall plan shows no drift; the documentation site builds without
warnings.

## Undo

Each step's own undo, in reverse. Nothing here is destructive of anything a tenant holds: the worst
case is every device back on the pool.

## To discover

- ~~Whether this OPNsense build's subnet update leaves alone the settings it isn't sent.~~
  **Found 2026-10-06:** it does. The role's read-back in step 2 passed.
- ~~The lease lifetime on the IoT subnet.~~ **Found 2026-10-06:** the IoT subnet sets none, so the
  server's general setting applies: 4000 seconds. A device on the old pool keeps its address for a
  little over an hour at most after step 2.
- That a device holding a pool lease moves to its reserved address at renewal, without a restart.
- Whether anything still dials `bellgw` or `mabell` in the substrate's zone.
- Whether the router's reservation search returns every row in one answer once tenants' rows are
  added to inventory's. With 16 rows it does; not yet seen with many.
