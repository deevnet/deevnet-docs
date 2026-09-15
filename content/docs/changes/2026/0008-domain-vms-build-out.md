---
title: "CHG-0008: Management Domain VMs, First Build"
weight: 8
---

# CHG-0008: Management Domain VMs, First Build

| | |
|---|---|
| **Date** | 2026-09-15 |
| **Change type** | Deployment · Decommission |
| **Classification** | Structural. It replaces every VM on the management hypervisor except the provisioners, and re-applies the access switch's trunks. |
| **Status** | **In progress**. Steps 1–2 and 5–6 done on 2026-09-15. Steps 3–4 (switch trunk, hv01 bridge) wait for someone at the rack; Step 7 can start with the two management-segment VMs. |
| **Window** | Started 2026-09-15 about 04:10Z, vault decrypted for each working window. Steps 3 and 4 need hands at the hardware. The SG2218 has no console port, so recovery is a laptop on `gi1/0/2` or the reset button; `dv02hyp001p01` needs its monitor and keyboard. |
| **Site** | mobile |
| **Systems** | Management hypervisor `dv02hyp001p01`; six new VMs: `dv02nms001v01`, `dv02sob001v01`, `dv02prv001v01`, `dv02idn001v01`, `dv02tob001v01`, `dv02msg001v01`; retired: `dv02tdn001v01`, `dv02tst001v01`, `dv02mqt001v01`; core router `dv02cor002p01` (Unbound, Kea); access switch `dv02acc001p01`; control host `dv00bld001p01` |
| **Automation** | `ansible-collection-deevnet.mgmt` (`podman_service`, `powerdns`, `minio`, `deevnet_api`, `omada_controller`, `proxmox_vm`, `vm_identity`); `ansible-collection-deevnet.net` (`dns.yml`, `dhcp.yml`, `switch-vlans.yml`, `proxmox-node-network.yml`); `ansible-collection-deevnet.builder` (`artifacts`); the new [`deevnet-provisioning-api`](https://github.com/deevnet/deevnet-provisioning-api) repository; all against `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. The step most likely to go wrong is the switch trunk re-apply, which rewrites every trunk on the switch, including the ports the control host and the management hypervisor sit behind. |
| **Related decisions** | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) — the domain VMs this builds, and §6's fold-in of tenant DNS and state, which this record carries out; [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) — the API whose shell is deployed; [ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/) — the controller's manual floor |
| **Related changes** | [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) — waits for the network management VM this builds; [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) — the zone policy these VMs are placed to survive |
| **Related incidents** | [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) — why the router record prune is previewed and gated |
| **Related runbooks** | [VM Identity](/docs/runbook/building-recovery/vm-identity/); [Console Recovery → Access Switch](/docs/runbook/recovery/console-recovery/access-switch/) |

---

## Summary

[ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) groups the
management hypervisor's services into domain VMs, each on exactly one segment, with every function
a container. Today the hypervisor still runs the earlier one-service VMs: tenant DNS
(`dv02tdn001v01`), the tenant state store (`dv02tst001v01`) and an MQTT broker that never
answered (`dv02mqt001v01`). The Omada controller runs on the Builder.

Nothing depends on those three VMs yet:
- The only registered tenant, eds, has never applied its Terraform
  ([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)).
- tdemo was destroyed on 2026-09-05.
- The broker was never reachable.

So the VMs are rebuilt from the current design rather than migrated. The operator deletes the old
VMs by hand. This record covers everything else.

**After this change:**

| VM | Segment | Runs |
|---|---|---|
| `dv02idn001v01` identity | Platform (25), 10.20.25.21 | PowerDNS (tenant DNS), `tdns` |
| `dv02prv001v01` provisioning | Platform (25), 10.20.25.20 | MinIO (`tfstate`), the Deevnet API shell and its PostgreSQL (`api`) |
| `dv02nms001v01` network management | management (99), 10.20.99.40 | the Omada controller (`omada`) |
| `dv02msg001v01` device messaging | IoT Backend (35), 10.20.35.20 | nothing yet; the broker comes in a later change |
| `dv02sob001v01` substrate observability | management (99), 10.20.99.41 | nothing yet |
| `dv02tob001v01` tenant observability | Platform (25), 10.20.25.22 | nothing yet |

**Container images are pushed, not pulled.** The shared `podman_service` role copies each image
tarball from the control host over SSH (`management -> platform` and
`management -> iot_backend` are both declared), so no VM needs a path back to the artifact server.
That keeps the build working once [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)
enforces the policy.

**The Builder's controller becomes a cold fallback.** Its role stays in `deevnet.builder`, and its
play now excludes management-plane hosts. The Builder leaves `network_controllers` in the inventory
change itself, not after verification: it keeps running untouched until Step 10 stops it.

## Goal

- The six VMs exist on `dv02hyp001p01` with VMID-derived MACs, each on its declared VLAN and
  address, and answer SSH by name.
- The core router holds no record or reservation for `dv02tdn001v01` or `dv02tst001v01`.
  `dv02mqt001v01` never had one.
- `tdns`, `tfstate`, `api` and `omada` resolve to the new hosts.
- The eds tenant zones answer authoritatively from `dv02idn001v01` and, through the core router,
  from any segment that resolves there.
- `http://api.mobile.deevnet.net:8080/readyz` returns 200, and `/version` reports `v0.1.0`.
- The controller on `dv02nms001v01` has completed its manual floor. The Builder's controller is
  stopped and disabled, with its data kept.

## Scope

**In scope:**
- inventory and router records for the three retired hosts
- VLAN 25 on the management hypervisor's trunk
- making the management hypervisor's bridge VLAN-aware
- staging the PostgreSQL and API images
- identity, addressing and DNS for the six VMs
- creating them
- PowerDNS, MinIO, the API shell and the Omada controller on their VMs
- the controller's manual floor
- stopping the Builder's controller

**Out of scope:**
- deleting the old VMs (done by the operator, before Step 1)
- the VerneMQ broker and its auth database
- observability tooling
- any API functionality
- the `platform -> management` rule the API will need to reach the controller
- adopting devices ([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/))
- enforcing the zone policy ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/))

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The trunk re-apply cuts the control host's or the hypervisor's path | `dv02acc001p01`, all four trunks | Only one tagged VLAN is added; native 99 is unchanged. Console at the rack. Baseline captured first. |
| The router prune deletes more than the retired records | Core router Unbound and Kea | Both roles report what they would remove without removing it. The apply runs only when that report lists exactly the retired records (Step 2). |
| A reused VMID lands on a stale reservation | Kea | The allocator gives the lowest free VMID, so 200, 201 and 204 come back. Their reservations are pruned in Step 2, before identity is allocated in Step 6. |
| Making the bridge VLAN-aware cuts the hypervisor's management | `vmbr0` on `dv02hyp001p01`, its only NIC | Management stays untagged on native VLAN 99; the role changes the bridge only, with no sub-interfaces and no routing. Console at the node. |
| The hypervisor runs out of memory | `dv02hyp001p01` (32 GB) | The six VMs declare 16 GB. Headroom is checked in Step 1, including the two VMs not in inventory. |
| eds loses its DNS key or state credential | PowerDNS, MinIO | Both are imported from the vault, not generated, so a rebuild restores them. |

## Prerequisites

- [ ] The old VMs (VMIDs 200, 201, 204) are deleted from `dv02hyp001p01`
- [ ] The branches for this change are merged, or checked out on the control host: inventory,
      `deevnet.mgmt`, `deevnet.builder`, `deevnet-tenant-factory`, `deevnet-provisioning-api`
- [ ] Vault decrypted, including `mobile/group_vars/deevnet_api/vault.yml`
- [ ] Console access to `dv02acc001p01`, for Step 3, and to `dv02hyp001p01`, for Step 4
- [ ] Each collection installed: `make install-dev` in each. The commands below run from the
      collection's directory with
      `export ANSIBLE_COLLECTIONS_PATH=./.ansible/collections:$HOME/.ansible/collections`.

## Procedure

### Step 1: Preflight

Read-only.

**Run:**

```bash
ssh a_autoprov@dv02hyp001p01 'sudo qm list; free -g; sudo pvesm status; grep -A8 "iface vmbr0" /etc/network/interfaces'
cd ansible-collection-deevnet.mgmt && make vm-identity
```

**Verify:**

1. VMIDs 200, 201 and 204 are gone, and a `fedora-server-*` template is listed.
2. At least 16 GB of memory is free.
3. `vmbr0`'s stanza in `/etc/network/interfaces` has no `bridge-vlan-aware` line. Read on
   2026-09-14: `bridge-ports enp0s31f6`, `bridge-stp off`, `bridge-fd 0`, nothing else. Step 4
   changes that.
4. `make vm-identity` reports the six new hosts as unallocated, and no collision.

**Undo:** Nothing to undo.

### Step 2: Remove the retired hosts' router records

This deletes records on the core router, and nothing else. The inventory no longer declares the
three hosts, so the roles list them as undeclared.

**Run** the preview first:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml --check --diff
ansible-playbook playbooks/dhcp.yml --check --diff
```

**Gate:** both "LEFT IN PLACE" reports list exactly what the preview showed on 2026-09-14, and
nothing else:
- **DNS:** host overrides `dv02tdn001v01` (10.20.99.30) and `dv02tst001v01` (10.20.99.31);
  aliases none
- **DHCP:** reservations `dv02tdn001v01` (`02:DE:20:00:00:C8`) and `dv02tst001v01`
  (`02:DE:20:00:00:C9`)

`dv02mqt001v01` has nothing to remove:
- It never had a reservation, because it declared `dhcp_reservation: false`.
- The router holds no override and no `mqtt` alias for it, which fits the broker never resolving
  in [ADR-0011's validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#validation-2026-09-14).

`tdns` and `tfstate` are still declared, now by the new hosts, so the role moves them rather than
deleting them. Anything else in either list stops the step.

**Then run:**

```bash
ansible-playbook playbooks/dns.yml -e dns_delete_unmanaged=true
ansible-playbook playbooks/dhcp.yml -e dhcp_delete_unmanaged=true
```

**Verify:**

1. The preview, run again, has no "LEFT IN PLACE" report.
2. `dig +short @10.20.99.1 dv02tdn001v01.mobile.deevnet.net` and
   `dv02tst001v01.mobile.deevnet.net` return nothing.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Carry VLAN 25 to the management hypervisor

This re-applies every trunk on the switch and writes flash. The `--check` flag cannot preview this
role, so the change is reviewed as the inventory diff: `gigabitEthernet 1/0/15` goes from
`allowed_vlans: [35, 99]` to `[25, 35, 99]`, and native 99 is unchanged.

**Run:**

```bash
# Baseline, from the switch CLI:  show running-config interface gigabitEthernet 1/0/15
cd ansible-collection-deevnet.net
ansible-playbook playbooks/switch-vlans.yml --tags trunk
```

**Verify:**

1. The switch's running config for `gigabitEthernet 1/0/15` carries 25 tagged, and 99 untagged.
2. `dv02hyp001p01` (10.20.99.21) and the control host's session stay up.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Make the management hypervisor's bridge VLAN-aware

`vmbr0` on `dv02hyp001p01` is a plain bridge, so the tagged NICs of the Platform and IoT Backend
VMs have no VLAN-aware bridge to join. This step sets it to the configuration Proxmox documents
and `dv02hyp002p02` already runs: `bridge-vlan-aware yes`, `bridge-vids 2-4094`. It is declared
in `host_vars/dv02hyp001p01/vars.yml` as `proxmox_node_network`, bridge only. There are no VLAN
sub-interfaces, and management keeps its untagged address and default route.

This touches the node's only NIC, so run it with the console available. Proxmox's documentation
does not say whether the change takes effect live.

**Run:**

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/proxmox-node-network.yml --tags interfaces -e target=dv02hyp001p01 --check
ansible-playbook playbooks/proxmox-node-network.yml --tags interfaces -e target=dv02hyp001p01
```

**Verify:**

1. `dv02hyp001p01` (10.20.99.21) still answers, and so does `dv02bld001v01` on it.
2. On the node, `cat /sys/class/net/vmbr0/bridge/vlan_filtering` prints `1`, and
   `/etc/network/interfaces` shows `bridge-vlan-aware yes` and `bridge-vids 2-4094` under `vmbr0`.

**Undo:** [Undo Step 4](#undo-step-4)

### Step 5: Stage the images

These writes are local to the control host.

**Run:**

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv00bld001p01 --tags container-images
cd ../deevnet-provisioning-api && make stage   # tag v0.1.0 checked out
```

**Verify:**

1. `/srv/deevnet-http/container-images/postgres/postgres-17.11.tar` exists.
2. `/srv/deevnet-http/container-images/deevnet-api/deevnet-api-v0.1.0.tar` exists.

**Undo:** Nothing to undo; the tarballs are inert.

### Step 6: Allocate identity, then publish addresses and names

**Run:**

```bash
cd ansible-collection-deevnet.mgmt && make vm-identity-assign
# Commit the six generated host_vars/<host>/identity.yml files in the inventory.
cd ../ansible-collection-deevnet.net
ansible-playbook playbooks/dhcp.yml --check --diff && ansible-playbook playbooks/dhcp.yml
ansible-playbook playbooks/dns.yml --check --diff && ansible-playbook playbooks/dns.yml
```

**Verify:**

1. `make vm-identity` reports no drift.
2. Kea holds reservations for 10.20.99.40 and 10.20.99.41 on their derived MACs.
3. `dig @10.20.99.1` resolves all six host names, plus `omada`, `tdns`, `tfstate` and `api`.

**Undo:** Remove the `identity.yml` files, then rerun Step 2's apply.

### Step 7: Create the VMs

**Run:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags vms --limit 'management_plane:!dv02bld001v01:!dv02bld002v01'
```

**Verify:**

1. `proxmox_vm` passes its MAC and address assertions for all six.
2. `qm config <vmid>` shows `net0` tagged 25, 35 or none, as declared.
3. Each VM answers `ssh a_autoprov@<host>.mobile.deevnet.net`.
4. `ip route` on each VM shows its segment's gateway.

**Undo:** [Undo Step 7](#undo-step-7)

### Step 8: Configure the services

**Run:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02idn001v01
( cd ../ansible-collection-deevnet.net && ansible-playbook playbooks/dns.yml --tags tenant-dns )
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02prv001v01
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02nms001v01
```

The `tenant-dns` run moves the core router's eds forwarding rows from 10.20.99.30 to 10.20.25.21.

**Verify:**

1. `dig @10.20.25.21 eds.mobile.deevnet.net SOA` answers authoritatively, and
   `dig @10.20.99.1 eds.mobile.deevnet.net SOA` gives the same answer.
2. `curl -s http://api.mobile.deevnet.net:8080/readyz` returns 200, and `/version` reports
   `v0.1.0`.
3. `/v1/anything` returns 401 without the token.
4. From the control host, the `mc` alias for `http://tfstate.mobile.deevnet.net:9000` lists
   `tf-state`.
5. `https://omada.mobile.deevnet.net:8043` loads the controller's setup wizard.

**Undo:** Stop and disable the service units on the VM (`pdns-auth`, `minio`, `deevnet-api`,
`deevnet-api-db`, `omada-controller`). The VMs themselves are undone by Step 7's undo.

### Step 9: The controller's manual floor

This is manual, per [ADR-0009 §5](/docs/architecture/decisions/0009-network-device-config-ownership/).

1. In the setup wizard, create the Owner account, and decide whether to cloud-register it
   (ADR-0013's open question 2). Make the vault's `vault_omada_owner_*` match the account.
2. Create the automation account:

   ```bash
   cd ansible-collection-deevnet.builder && ansible-playbook playbooks/omada-automation-user.yml
   ```

3. As the Owner, create the Open API client, and record its id and secret in the vault.

**Verify:** A client-credentials token request from the control host succeeds. The request only
reads.

**Undo:** Reset the controller: stop `omada-controller`, clear `/opt/omada-controller/data`, and
rerun Step 8 for `dv02nms001v01`.

### Step 10: Stop the Builder's controller

**Run** on `dv00bld001p01`:

```bash
sudo systemctl disable --now omada-controller
```

**Verify:**

1. `systemctl is-enabled omada-controller` reports `disabled`.
2. `/opt/omada-controller` is intact.

**Undo:** `sudo systemctl enable --now omada-controller`

## Verification

- Every point under [Goal](#goal) holds.
- Two reboot checks:
  - `qm reboot` for `dv02idn001v01` and `dv02prv001v01`; every service comes back without a manual
    step.
  - `systemctl restart deevnet-api-db` on `dv02prv001v01` makes `/readyz` return 503, and it
    recovers by itself.
- The empty VMs (`sob`, `tob`, `msg`) answer SSH, and nothing but sshd is listening on them.

## Undo

Steps are backed out in reverse order.

**No practical undo point:** the old VMs are deleted, so there's nothing to return to. Undo restores
the router and the switch to their pre-change state, and removes the new VMs.

### Undo Step 2

Revert the inventory change, then rerun `dns.yml` and `dhcp.yml` without the delete flags. This
recreates the records and reservations. They point at VMs that no longer exist.

### Undo Step 3

Set `allowed_vlans` back to `[35, 99]`, and rerun `switch-vlans.yml --tags trunk`. If the run cuts
the path, restore the baseline from the console.

### Undo Step 4

Remove the `proxmox_node_network` block, and set the bridge back through the API or the node's
network page: VLAN aware off. If management was lost, restore the stanza read in Step 1 from
the console, then run `ifreload -a`.

### Undo Step 7

`qm stop <vmid> && qm destroy <vmid>` for each new VM. Then remove its `identity.yml` and rerun
Step 2's apply.

## Outcome

| When (UTC) | Steps | What happened |
|---|---|---|
| 2026-09-14 | Step 1 (part) | The operator read `dv02hyp001p01`: 24 GB of memory available. `vmbr0` is **not** VLAN-aware, so Step 4 was added before any device change. |
| 2026-09-15, before 04:13 | Step 1 | `make vm-identity`: both hypervisors answered. VMIDs 200, 201 and 204 are free, and the template `fedora-server-44-1.7` (115) is present. The six new VMs are awaiting allocation, and no collision was reported. The next free VMID is 200 (`02:de:20:00:00:c8`). |
| 04:12 | Step 2 preview | Gate met exactly. DNS: overrides `dv02tdn001v01` and `dv02tst001v01`, no aliases. DHCP: `dv02tdn001v01` (`02:DE:20:00:00:C8`) and `dv02tst001v01` (`02:DE:20:00:00:C9`). |
| 04:13:17 | Step 2, DNS | `dns.yml -e dns_delete_unmanaged=true`: `changed=6`, `failed=0`. |
| 04:13:37 | Step 2, DHCP | `dhcp.yml -e dhcp_delete_unmanaged=true`: `changed=2`, `failed=0`. |
| 04:14 | Step 2 verify | Both re-previews show no undeclared records. `dv02tdn001v01` and `dv02tst001v01` no longer resolve. `tdns` resolves to 10.20.25.21, `tfstate` and `api` to 10.20.25.20, `omada` to 10.20.99.40. The core router, `dv02hyp001p01` and `artifacts` still resolve. A read of the router's reservations through its API shows 13 entries, each matching inventory, and neither `…C8` nor `…C9`. |

| 21:03–21:05 | Step 5 | Builder `site.yml --limit dv00bld001p01 --tags container-images`: `changed=3`, `failed=0`. Staged `postgres/postgres-17.11.tar` (461 MB). `deevnet-api/deevnet-api-v0.1.0.tar` was already staged on 2026-09-14. |
| 21:05 | Step 6, identity | `make vm-identity-assign` allocated idn 200 (`…c8`), prv 201 (`…c9`), nms 204 (`…cc`), msg 205 (`…cd`), sob 206 (`…ce`) and tob 207 (`…cf`). The `make vm-identity` audit afterwards shows eight declared VMIDs, all unique, every MAC matching its VMID, and 208 next free. |
| 21:06 | Step 6, previews | DHCP: add 2 (`dv02nms001v01` `…CC` → 10.20.99.40, `dv02sob001v01` `…CE` → 10.20.99.41). The four static-address VMs' MACs are on the remove list, but none holds a reservation, so nothing would be deleted. No undeclared records. DNS: nothing to add, and `dig` shows all six hosts and the `omada`, `tdns`, `tfstate` and `api` aliases already correct. |
| 21:07:42 | Step 6, DHCP | `dhcp.yml`: `changed=2`, `failed=0`. A read of the router's reservations through its API shows 15 entries: the 13 existing ones unchanged, plus `…CC` → 10.20.99.40 and `…CE` → 10.20.99.41. The re-preview has nothing to add and no undeclared records. |

### Departures from the plan

- **Step 2 also did work planned for Steps 6 and 8.** The DNS run applies the whole role, not only the prune. So it also:
  - added host overrides for the six new VMs
  - added the `omada` and `api` aliases
  - moved `tdns` and `tfstate` to the new hosts
  - added the core router's forwarding rows for the eds tenant zones (`eds.mobile.deevnet.net`,
    `129.20.10.in-addr.arpa`), pointing at `dv02idn001v01` (10.20.25.21)

  Queries for those zones through the router time out until the identity VM is built in Step 7.
  eds has never applied its Terraform, so nothing depends on them.
- **The DHCP run rewrote all 13 existing reservations with the values they already had.** This is
  a defect in `opnsense_dhcp`, not a change:
  - its update set is every declared reservation whose MAC already exists, with no field
    comparison
  - the task is `changed_when: true`

  The API read above confirms nothing moved.
- **Steps 5 and 6 ran before Steps 3 and 4.** The operator was remote, reaching the Builder through
  its WAN port. Steps 3 and 4 can cut the Builder's management path and need hands at the hardware,
  while Steps 5 and 6 touch only the Builder and the router's API. Neither depends on VLAN 25 or the
  bridge.
- **Step 6's DNS run was skipped.** Step 2's DNS run had already published every record Step 6
  would write. The check-mode preview had nothing to add, the override update only fires on an
  address change, and `dig` through the router confirmed every name.
- **The Step 6 DHCP run again rewrote the 13 existing reservations** with unchanged values: the same
  `opnsense_dhcp` defect as in Step 2, already a follow-up.

## Follow-ups

- [ ] `opnsense_dhcp`: compare IP, hostname and description before updating a reservation, so a run with no drift reports no change (found in Step 2)
- [ ] The VerneMQ broker and its auth database in `dv02msg001v01`, with the `mqtt` name and
      `mqtt_brokers` membership ([ADR-0012 §8](/docs/architecture/decisions/0012-iot-platform-api/))
- [ ] Observability tooling for `dv02sob001v01` and `dv02tob001v01`
- [ ] API functionality, and the `platform -> management` rule to the controller's Open API port
      ([ADR-0013 §10](/docs/architecture/decisions/0013-management-services-domain-vms/))
- [ ] Review `powerdns_dnsupdate_from`, which still admits only the management subnet, now that
      the server sits on Platform
- [ ] `deevnet-tenant-tdemo` still names `tfstate.mobile.deevnet.net` and 10.20.99.30. The tenant
      is destroyed; update or archive the repository.
- [ ] `deevnet-tenant-factory` `TENANTS.md` shows index 1 as free, but the inventory gives it to
      eds
- [ ] Update the pages that describe current state: tenant DNS platform page, management
      hypervisor page, Important URLs, the VM identity and MAC naming worked examples, and the
      Omada recovery and upgrade runbooks
- [ ] ADR-0013: status Accepted; record the answer to open question 1 (the Builder's controller
      is a cold fallback) and open question 2 (as decided in Step 9)
