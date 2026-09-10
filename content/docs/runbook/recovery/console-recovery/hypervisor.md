---
title: "Hypervisor"
weight: 2
aliases:
  - /docs/runbook/console-recovery/hypervisor/
---

# Hypervisor

Recovering a Proxmox node — `dv02hyp001p01` or `dv02hyp002p02` — from the physical console
when its management address stops answering.

A node loses its own management path far more easily than it loses its VMs. The guests
usually keep running on a node you cannot log into, which is worth knowing before you rush:
there is normally no data at risk, only access.

## What you need

| | |
|---|---|
| **Adapter** | DisplayPort → HDMI, into your monitor. |
| **Keyboard** | USB. |
| **Access** | Physical, at the node. |
| **Credentials** | The node's root password, from the inventory vault. |

| Node | Address | Role | CNAME |
|---|---|---|---|
| `dv02hyp001p01` | 10.20.99.21 | Management hypervisor | `pve` |
| `dv02hyp002p02` | 10.20.99.22 | Tenant hypervisor | `pve2` |

---

## 1. Confirm it is the node, and that it is awake

```bash
ping -c1 10.20.99.21
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.21/8006'   # PVE web UI
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.21/22'     # ssh
```

Both nodes have `wol: true` in inventory, so if the box is simply powered off the answer is
not a monitor:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/wol.yml
```

If a VM on the node still answers while the node itself does not, the fault is the node's own
management interface rather than the physical link — the bridge is still forwarding.

---

## 2. Get a console

DisplayPort→HDMI adapter to the monitor, USB keyboard, log in as root at the node's console.

---

## 3. Find what changed

Node networking is inventory-driven through `proxmox_node_network`, and the failures that
cost access come from that shape rather than from Proxmox itself:

```sh
ip -br addr                     # does the management address exist at all
ip route                        # is there still a default route, and where does it point
bridge vlan show                # is vmbr0 VLAN-aware, and are the VLANs present
cat /etc/network/interfaces     # the declared state the node booted with
```

| What you see | Likely cause |
|---|---|
| Management address missing from the bridge | Bridge or VLAN sub-interface change applied badly |
| Address present, default route points at transit | The `default-route` tag ran without `mgmt-routing` active |
| Address present, nothing routes off-segment | Upstream — the switch port's native VLAN, not this node |
| Bridge not VLAN-aware but tagged interfaces declared | Partial `interfaces` run |

{{< hint warning >}}
**The `default-route` step is the one that costs access.** `proxmox_node_network` moves the
default route off management onto transit, and its own README rates it *"can cost
access — refuses to run unless `mgmt-routing` is active."* If the node went dark right after
a `proxmox-node-network.yml` run, start here.
{{< /hint >}}

Both nodes carry management **untagged** on their switch port's native VLAN 99, deliberately,
so that `vmbr0` needs no change and the node cannot be lost by a VLAN edit. If management is
untagged in `/etc/network/interfaces` but the switch port is no longer native 99, the fault
is on the switch — see [access switch](/docs/runbook/recovery/console-recovery/access-switch/).

---

## 4. Repair in place

Proxmox uses `ifupdown2`, so interface changes can be reloaded without a reboot:

```sh
# after editing /etc/network/interfaces back to a working state
ifreload -a
ip -br addr
ping -c1 10.20.99.1
```

If a pending configuration was staged but never applied, Proxmox keeps it as
`/etc/network/interfaces.new` — remove it to stop it being applied at the next boot.

To restore a default route by hand, long enough to get back in remotely:

```sh
ip route add default via 10.20.99.1
```

That is deliberately not persistent. Make it permanent through inventory and the playbook,
not by hand-editing the node.

---

## 5. Reconcile

Bring the node back to declared state through the role rather than leaving hand edits in
place. The tags exist so the risky step stays separable:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/proxmox-node-network.yml --limit dv02hyp001p01 \
  --tags packages,interfaces,mgmt-routing
```

Run `default-route` and `tenant-egress` only once `mgmt-routing` is confirmed active, and
only with the console still connected. `interfaces` is additive and safe; `default-route` is
the one that can put you back at this page.

---

## Related

- [Management hypervisor](/docs/platforms/management-plane/management-hypervisor/) and [tenant hypervisors](/docs/platforms/tenant-compute/tenant-hypervisors/) — what these nodes are and what runs on them

## When not to use this page

A node whose disk or hardware has failed is not a console-recovery job — it is a rebuild from
the image factory, with identity (VMID → MAC → reservation) preserved from inventory. See
[Building Infrastructure](/docs/runbook/building-recovery/).
