---
title: "Rebuild the Core Router"
weight: 4
---

# Rebuild the Core Router

Bringing `dv02cor002p01` back after a fresh OPNsense install: a failed disk, replaced hardware, or a
configuration beyond [console recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/).
OPNsense is installed by hand from USB, and in normal service it is upgraded in place
([Patching](/docs/runbook/substrate/lifecycle/patching/)), so this is the path for when the box
itself is lost.

Everything the router does is declared in inventory and applied over its API by the `deevnet.net`
collection, from the control host. The one thing automation cannot create is its own way in: an
API key. That is what decides the route below.

| You have | Route |
|---|---|
| A saved `config.xml` from this router | [Restore it](#restore-a-saved-configuration), then reconcile. The API key, interface assignments and everything else come back with it |
| Nothing saved | [Build from nothing](#build-from-nothing): a new API key, then every role in order |

Saved configurations live in two places:

- **On the router**, in `/conf/backup`: one per change. Gone if the disk is.
- **On the control host**, in `/srv/dvnt/migration-logs/`: `dv02cor002p01-pre-firewall-<date>.xml`,
  written by the `opnsense_firewall` role before every apply. It holds the router's secrets, and it
  sits on the Builder, so it goes with a [Builder repave](/docs/runbook/substrate/building-recovery/repave-builder/)
  unless copied off.

---

## Restore a saved configuration

1. **Install OPNsense from USB** on the router
   ([Build Network → Core Router](/docs/runbook/substrate/building-recovery/build-network/#core-router)).
   Use the same hardware or the same NIC names (`re0` LAN, `re1` WAN): the configuration refers to
   interfaces by name.
2. **Reach the web UI** on the installer's default LAN (a laptop cabled to `re0`), and restore the
   saved `config.xml` from the configuration backup page. The router reboots into the restored
   configuration, on `10.20.99.1` and every VLAN.
3. **Reconcile to inventory.** The file is as old as its last save, so bring the router forward to
   declared state, reading each report rather than trusting `changed=0`:

   ```bash
   cd ansible-collection-deevnet.net
   make opnsense                                                  # reports firewall drift, writes the rest
   ansible-playbook playbooks/opnsense.yml -e firewall_apply=true # only if the report shows drift
   ansible-playbook playbooks/wol.yml
   ```

4. **Reconcile each tenant**, so the router's resolver forwards every tenant zone the API holds
   ([Tenant Admission → Operator-only calls](/docs/runbook/substrate/tenant-admission/#operator-only-calls)).

The vault needs no change: the restored configuration carries the API key the vault already holds.

---

## Build from nothing

This path has not been run: the router in service was built in
[CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) and has been carried forward since. What a
fresh router needs, in order:

1. **Install OPNsense from USB**, and at the console assign `re1` as WAN (DHCP from the edge router)
   and a VLAN 99 interface on `re0` as LAN, at `10.20.99.1/24`. The switch trunk's native VLAN is the
   unrouted blackhole VLAN, so an untagged LAN on `re0` would be unreachable.
2. **Create an API key** in the web UI for the automation user. OPNsense generates it; it cannot be
   supplied. Put the key and secret into `group_vars/routers/vault.yml` as `vault_opnsense_api_key`
   and `vault_opnsense_api_secret`, then `make vault`, commit and **push** before going on.
3. **Install the `os-wol` plugin.** No role installs plugins.
4. **Apply every role:** `make opnsense` in `deevnet.net`. It creates the VLAN interfaces and pauses
   while you set their addresses in the GUI (there is no API for it), then configures DNS, DHCP,
   gateways and routes. The firewall role reports only.
5. **Apply the zone policy:** `ansible-playbook playbooks/opnsense.yml -e firewall_apply=true`.
   Then remove, by hand, the stock allow rules a fresh install puts on LAN. They sit outside
   automation, and the policy is not enforced while they remain.
6. **Set the management subnet's `next_server`** to the Builder, `10.20.99.95`, by hand. No role
   manages it ([PXE Role](/docs/platforms/management-plane/bootstrap-node/pxe-role/#subnet-level-settings)).
7. **Register Wake-on-LAN hosts:** `ansible-playbook playbooks/wol.yml`.
8. **Give the Deevnet API the new key:** in `deevnet.mgmt`,
   `ansible-playbook playbooks/site.yml --limit deevnet_api`, then reconcile each tenant.

---

## Verify

- [Segment Check](/docs/runbook/substrate/network/segment-check/) passes from each client segment.
- The **Network** checks in [Verify Site](/docs/runbook/substrate/building-recovery/build-verification/)
  pass, including a tenant zone resolving through `10.20.99.1`.
- `pfctl -sr | grep -c .` at the console shows the managed rule count the last firewall run
  reported.
