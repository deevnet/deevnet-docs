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
| **Status** | **In progress**. Done on 2026-09-15: Steps 1–2 and 5–6; Step 7 for `dv02nms001v01` and `dv02sob001v01`, both rebooted after their first-boot upgrade; Step 8 for the Omada controller on `dv02nms001v01`, with its firewall ports corrected at 22:05Z. Step 9's manual floor is done: the wizard, a local Owner, the automation account and the Open API client. Step 10 stopped the Builder's controller at 23:14Z, and Step 3 carried VLAN 25 to the management hypervisor's port at 23:28Z with the operator at the rack. Step 4 made the hv01 bridge VLAN-aware at 23:38Z, and Step 7 finished at 00:07Z with the four Platform and IoT Backend VMs built, verified and rebooted. Step 8 put PowerDNS on `dv02idn001v01` at 00:09Z, and the eds tenant zones answer again. MinIO and the Deevnet API on `dv02prv001v01` are what remain. Steps 3–4 wait for someone at the rack, and the Platform and IoT Backend VMs in Steps 7–8 wait on those. |
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
| 21:13:28–21:15:46 | Step 7 (`nms`, `sob`) | `site.yml --tags vms --limit dv02nms001v01,dv02sob001v01`: both hosts `changed=3`, `failed=0`. Both were cloned from `fedora-server-44-1.7`. `proxmox_vm` confirmed each net0 MAC (`…cc`, `…ce`), start-on-boot, and that each guest came up on its reserved address (10.20.99.40, .41). |
| after 21:16 | Step 7 verify | Both VMs answer SSH by name. Each shows the inventory hostname, the declared MAC and address on `eth0`, and a default route via 10.20.99.1 from DHCP. The resolver's upstream is 10.20.99.1 with search domain `mobile.deevnet.net`, and `artifacts` and `omada` resolve. Each has a 30 GB root, passwordless sudo, and no failed units. |
| 21:20:26 and 21:23:22 | Step 7, first boot | cloud-init finished on `sob` (297 s after boot) and `nms` (473 s) with `errors: []`. It reports `degraded done` only for two deprecation warnings about a string `user` key in the user data Proxmox generates. Its final stage ran `dnf -y upgrade`: 14 packages installed, 203 upgraded, 628 MiB downloaded. Both VMs still run kernel 6.19.10 with 7.2.5 installed, and `dnf needs-restarting -r` says a reboot is required. |
| 21:30:54–21:31:17 | Step 7, reboot | `nms` and `sob` rebooted with the operator's go-ahead and answered SSH again 23 s later. Both now run kernel 7.2.5, and `dnf needs-restarting -r` no longer asks for a reboot. Addresses and MACs are unchanged, no units have failed, and cloud-init reports `done`. |
| 21:33:48–21:35:15 | Step 8 (`nms`) | `site.yml --skip-tags vms --limit dv02nms001v01`: `changed=13`, `failed=0`. `--list-hosts` had confirmed that only the Omada controller play matched. `podman_service` pushed and loaded the 945 MB image, created `omada-controller` on host networking, enabled its unit and opened the declared firewalld ports. Both readiness waits passed with no retries. |
| after 21:35 | Step 8 verify | The unit is active and enabled, and the container reports `healthy` with 0 restarts. From the Builder, `https://omada.mobile.deevnet.net:8043/api/info` returns 6.3.0.45 with `configured: false`, and `:8088` redirects to `:8043`. Memory: 1.8 GiB of 3.9 GiB used, no swap; the container uses 1.36 GB. The 12 error-priority journal lines are stderr noise: a `useradd` UID note, `tail` waiting for `server.log`, and JVM deprecation warnings. MongoDB listens on 127.0.0.1:27217 only. The Builder's controller is untouched (`configured: true`). |
| 22:05:18–22:05:37 | Step 8, firewall fix | Re-ran `site.yml --skip-tags vms --limit dv02nms001v01` with the corrected `omada_controller` (mgmt #15): `failed=0`. It opened 29815–29817/tcp and closed 29814/udp and 27002/tcp, in both the running and the permanent configuration. From the Builder, 29815–29817 answer and 27002 does not. The container wasn't restarted, and `/api/info` still answers. |
| 22:07:30 | Step 8, ownership restored | The same run had reset `/opt/omada-controller/data` and `/logs` to `root:root` (see Departures). A non-recursive `chown` set both back to `508:508`, with no restart. The `omada` account can create files in `logs` again. No permission errors had been logged. |
| 22:22:19–22:22:39 | Step 8, re-run | With the corrected role merged (mgmt #16), `site.yml --skip-tags vms --limit dv02nms001v01` reported `changed=0`: the data-directory task is `ok` for all four directories. The before and after snapshots are identical - `data` and `logs` still `508:508`, `work` still root, the same firewall ports, the container not restarted - and `/api/info` still answers. |
| 22:47:32–22:47:37 | Step 9, automation account | `omada-automation-user.yml` (deevnet.builder) against `dv02nms001v01`: `changed=1`, `failed=0`. It logged in as the Owner from the vault, found no existing automation account, created `a_autoprov`, verified that it authenticates and can read its site (`Omada Network_F2774E`), and then wrote its new password into `group_vars/network_controllers/vault.yml`. |
| after 22:50 | Step 9, Open API client | Created by the operator in the controller's UI and recorded in the same vault. Verified read-only from the Builder: a client-credentials request returned a bearer token valid for 7200 s, and listing sites through the Open API returned the one site. |
| 23:14:10 | Step 10 | `systemctl disable --now omada-controller` on `dv00bld001p01`. The container exited and port 8043 stopped answering there. Its 263 MB of data stays under `/opt/omada-controller`, and the controller on `dv02nms001v01` is unaffected. The Builder had already left `network_controllers` in the inventory change. |
| 23:16:46 | Step 10, tidy-up | The unit was left `failed` because `podman start -a` exits 143 on SIGTERM, which systemd counts as a failure. `systemctl reset-failed omada-controller` cleared it: the unit is now `inactive` and `disabled`, and the Builder reports no failed units. |
| 23:27:46–23:28:20 | Step 3 | `switch-vlans.yml --tags trunk`, with the operator at the rack and reaching the site through the edge router rather than the AP. It rewrote all four trunks as expected: `gi1/0/1` uplink (all VLANs tagged, native 999), `gi1/0/4` AP (10, 30, 31, 40 tagged, native 99), `gi1/0/13` tenant hypervisor (50, 51 tagged, native 99) and `gi1/0/15` management hypervisor (**25, 35 tagged**, native 99). `failed=0`. |
| after 23:28 | Step 3 verify | Read back from the switch: `gi1/0/15` shows `allowed vlan 99 untagged`, `25,35 tagged`, `pvid 99`, and its VLAN membership lists 25 `platform` and 35 `iot_backend` tagged with 99 `management` untagged. The switch, `dv02hyp001p01`, `dv02nms001v01` and the core router all answer, and the controller's API still responds. |
| 23:33:59 | Step 4 preflight | hv01 runs Proxmox 8.4.21, kernel 6.8.12, and `vmbr0` was a plain bridge (`vlan_filtering` 0). A VLAN-aware bridge needs no PVE 9 feature, so the pending hypervisor uplift doesn't block this. A check-mode run passed its assertions, read the node's three interfaces and would create no VLAN sub-interfaces. |
| 23:38:36–23:38:38 | Step 4 | `proxmox-node-network.yml --tags interfaces -e target=dv02hyp001p01`: `changed=1`, `failed=0`. `vmbr0` is VLAN-aware with VIDs 2–4094, `vlan_filtering` is 1, and hv01, `nms`, `sob`, `dv02bld001v01`, the switch, the router and the controller API all answered afterwards, with every guest still running. |
| 23:41:23 | Step 4 correction | The update left the bridge recorded as `method: manual`, because the role's PUT replaces the interface definition and sent no address. The stanza kept its `address` and `gateway` lines and the node never lost its address, but `dv02hyp002p02`'s equivalent bridge reads `static`. A PUT including the address and gateway restored `inet static`, with VLAN awareness unchanged and everything still reachable. The role is fixed in [deevnet.net #19](https://github.com/deevnet/ansible-collection-deevnet.net/pull/19). |
| 23:50:27–23:54:32 | Step 7 (the four remaining VMs) | `site.yml --tags vms --limit dv02idn001v01,dv02prv001v01,dv02tob001v01,dv02msg001v01`: all four `changed=3`, `failed=0`, cloned from `fedora-server-44-1.7`. `proxmox_vm` confirmed each MAC, `onboot`, and that each guest came up on its declared address: `idn` 10.20.25.21, `prv` 10.20.25.20, `tob` 10.20.25.22 and `msg` 10.20.35.20. This is the first traffic to use Steps 3 and 4. |
| after 23:55 | Step 7 verify | From the Proxmox API, `net0` carries `tag=25` for `idn`, `prv` and `tob` and `tag=35` for `msg`, with `nms` and `sob` untagged on management as intended. Inside each guest: the inventory hostname, the declared MAC and address, its segment's gateway as route and resolver, working name resolution, a 30 GB root and no failed units. Their first-boot upgrades ran long enough that two of them were briefly too busy to answer a shell. |
| 00:06:09–00:06:44 | Step 7 reboot | All four rebooted with the operator's go-ahead and answered SSH again about 35 s later, on kernel 7.2.5, with no reboot pending, unchanged addresses and MACs, no failed units and cloud-init `done`. |
| 00:08:19–00:09:32 | Step 8, PowerDNS on `idn` | `site.yml --skip-tags vms --limit dv02idn001v01`: `changed=32`, `failed=0`. It freed port 53 from the resolved stub, set the SELinux contexts, wrote `pdns.conf`, pushed and loaded the image from the Builder, seeded the SQLite schema out of that image, started the container under systemd, then created the eds zones, imported and bound its TSIG key, restricted dynamic update to the management subnet and reconciled the apex. |
| after 00:10 | Step 8 verify, DNS | On `idn`: the service is active and enabled, the container is up with no restarts on host networking, 53/tcp and 53/udp listen and are open in firewalld, both eds zones exist with the `eds` key bound to each, and no units have failed. Resolution: `eds.mobile.deevnet.net` and `129.20.10.in-addr.arpa` answer authoritatively at 10.20.25.21 and resolve `NOERROR` through the core router, with the apex SOA and NS pointing at `dv02idn001v01` rather than PowerDNS's placeholder. `tdns`, `artifacts` and `omada` still resolve. |

### Departures from the plan

- **Step 2 also did work planned for Steps 6 and 8.** The DNS run applies the whole role, not only the prune. So it also:
  - added host overrides for the six new VMs
  - added the `omada` and `api` aliases
  - moved `tdns` and `tfstate` to the new hosts
  - added the core router's forwarding rows for the eds tenant zones (`eds.mobile.deevnet.net`,
    `129.20.10.in-addr.arpa`), pointing at `dv02idn001v01` (10.20.25.21)

  Queries for those zones through the router timed out until the identity VM existed. **Resolved at
  00:10Z**, once PowerDNS came up on `dv02idn001v01`: both zones now answer through the router. eds
  had never applied its Terraform, so nothing depended on them in the meantime.
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
- **Step 7 ran for the two management-segment VMs only.** `dv02prv001v01`, `dv02idn001v01` and
  `dv02tob001v01` (Platform) and `dv02msg001v01` (IoT Backend) need VLANs 25 and 35 on the hv01
  trunk and a VLAN-aware bridge first, which are Steps 3 and 4.
- **`dv02bld001v01` and `dv02bld002v01` were stopped by the operator during the window**, along with the two VMs that are not in inventory. Nothing in this change needs them: images are pushed from `dv00bld001p01`, which is untouched.
- **Every new VM upgrades itself on first boot.** Proxmox's `ciupgrade` option defaults to on:
  *"cloud-init: do an automatic package upgrade after the first boot."* (`qm` manual,
  `default = 1`). `proxmox_vm` doesn't set it. From the Fedora 44 1.7 template, that meant:
  - a 628 MiB download from the internet
  - several extra minutes on every build
  - a VM that needs a reboot
  - a failure on a site without internet access

  The VMs weren't rebooted as part of Step 7.
- **The controller role's firewall port list doesn't match 6.3.0.45.** The list was carried over
  from the Builder's role. Omada's port reference, *"Which Ports do Omada SDN Controller and Omada
  Discovery Utility Use (above Controller 5.0.15)"* (updated 08-28-2026), is the source for what
  follows.
  - **Listening but blocked.** The controller listens on TCP 29815, 29816, 29817 and 8044, and on
    UDP 19810. firewalld opens none of them. The reference lists the first three as TCP:
    - 29815: *"Starting from v5.9, Omada Controller receives Device Info, Packet Capture Files."*
    - 29816: *"Starting from v5.9, Omada Controller establishes the remote control terminal
      session."*
    - 29817: *"To ensure proper communication between devices and the Controller."*

    8044 isn't in the reference; the controller's `omada.properties` names it
    `upgrade.es.https.port`. UDP 19810 is OLT discovery, and this site has no OLT.
  - **Open but unused.** firewalld opens UDP 29814, which the reference lists as TCP only, and TCP
    27002, which isn't in the reference and nothing binds.

  Nothing is adopted yet, so nothing is affected today. It matters before CHG-0005 adopts the AP.
- **Making the bridge VLAN-aware dropped its address from Proxmox's record.** `proxmox_node_network`
  PUTs only the bridge fields, and a PUT replaces the interface definition, so PVE rewrote
  `vmbr0`'s method from `static` to `manual`.
  - **Effect:** none observed. The `address` and `gateway` lines stayed in
    `/etc/network/interfaces`, ifupdown2 read them, and hv01 kept its address, its route and its
    guests.
  - **Why it still mattered:** hv01 has one NIC, and a method that no longer claims its address is
    not a state to leave a node in.
  - **Repair:** a PUT carrying the address and gateway restored `inet static` at 23:41:23, with
    VLAN awareness unchanged. The role now carries `cidr` and `gateway` through
    ([deevnet.net #19](https://github.com/deevnet/ansible-collection-deevnet.net/pull/19)).
- **Re-running Step 8 took two data directories away from the controller.**
  - **Cause:** `omada_controller` forced `root:root 0755` on its data directories on every run.
    The image's entrypoint (`fix_permissions`) gives `data` and `logs` to its `omada` account
    (UID 508) at each start, so the firewall-fix run reset both to root.
  - **Effect:** only the top-level directories changed, and nothing was logged. But until a
    restart, the controller couldn't create new files directly in either directory.
  - **Repair:** ownership was restored at 22:07:30 without a restart. The role now creates missing
    directories and leaves existing ones alone (mgmt #16, builder #17).

## Follow-ups

- [x] Reboot `dv02nms001v01` and `dv02sob001v01` onto the upgraded kernel before Step 8 (found in Step 7; done 21:31Z)
- [x] `omada_controller`, in both `deevnet.mgmt` and `deevnet.builder`: align the firewalld port lists with Omada's port reference for the running version (found in Step 8). Done in mgmt #15 and builder #16, applied to `dv02nms001v01` at 22:05Z; 8044 left closed.
- [x] After mgmt #16 merges, re-run Step 8 on `dv02nms001v01` and confirm the data-directory task reports no change (found in Step 8; done 22:22Z, `changed=0`)
- [ ] The vault holds one controller's credentials - Owner, automation account and Open API client. The Builder fallback controller's own credentials are now only in the vault file's git history. Decide whether that is acceptable for a fallback whose database is derived state (found in Step 9).
- [ ] `proxmox_vm`: decide on first-boot upgrades. Either set `ciupgrade` off and keep the template current through image-factory rebuilds, or keep it on and reboot the guest when `dnf needs-restarting -r` asks (found in Step 7)
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
