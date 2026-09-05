---
title: "Phase 13 — Rename a Proxmox Node"
weight: 13
---

# Phase 13 — Rename a Proxmox Node

The last place the estate called a machine something other than its inventory name was the Proxmox
node name. Both hypervisors were installed from the Proxmox ISO, which defaults the hostname to
`pve`, so the nodes were `pve` and `pve2` while inventory called them `dv02hyp001p01` and
`dv02hyp002p02`.

| Host | Node was | Node is |
|------|----------|---------|
| `dv02hyp001p01` | `pve` | `dv02hyp001p01` |
| `dv02hyp002p02` | `pve2` | `dv02hyp002p02` |

{{< hint danger >}}
**A PVE node name is not renamable through any supported path.** There is no `pvecm rename`, no API
call, and no GUI control. The node name is the directory name under `/etc/pve/nodes/`, and every
guest config lives inside it. This procedure moves that directory by hand.

Do it on a **standalone** node only. On a clustered node the name is also a corosync ring identity
and this procedure is wrong — there, the supported answer is to remove the node from the cluster,
reinstall it, and rejoin.
{{< /hint >}}

---

## Prerequisites

- The node is standalone (`pvecm status` reports no cluster, or the file
  `/etc/pve/corosync.conf` does not exist).
- A current backup of `/etc/pve` — `tar czf /root/etc-pve-$(date +%F).tgz /etc/pve`. This is a
  FUSE filesystem; the tarball is the rollback.
- The inventory name is already correct (Phase 6). This phase makes the box agree with inventory,
  not the other way round.
- Console access, not just SSH. The hostname change and the `pve-cluster` restart are both
  survivable over SSH, but a mistake in `/etc/hosts` is not.

---

## Steps

### 1. Set the OS hostname

```bash
hostnamectl set-hostname dv02hyp001p01
```

### 2. Make `/etc/hosts` resolve the new name

PVE resolves its own node name through `/etc/hosts` and will not start `pve-cluster` if the name
does not resolve to a real address on the box.

{{< hint warning >}}
**Do not drive this with `lineinfile` anchored on the node name.** `/etc/hosts` has more than one
line matching a bare name, and the regexp anchors on the very string being changed — the result is
an appended duplicate rather than an edit, and the duplicate is only found later when something
resolves the wrong way.

Anchor on the **management IP**, which the rename does not change, and write the full alias set in
one line. The `proxmox_node_base` role in `deevnet.builder` does exactly this. Where cloud-init
manages the file (`manage_etc_hosts: true`), let cloud-init own it and change the name through
cloud-init instead.
{{< /hint >}}

The line must read:

```
10.20.99.21 dv02hyp001p01.mobile.deevnet.net dv02hyp001p01
```

Verify before going further — if this is wrong, the next step leaves the node without a working
`/etc/pve`:

```bash
hostname -f          # the FQDN
getent hosts "$(hostname)"
```

### 3. Move the node directory

```bash
NEW=$(hostname)
OLD=pve
mkdir -p /etc/pve/nodes/$NEW/qemu-server /etc/pve/nodes/$NEW/lxc
mv /etc/pve/nodes/$OLD/qemu-server/*.conf /etc/pve/nodes/$NEW/qemu-server/
mv /etc/pve/nodes/$OLD/lxc/*.conf         /etc/pve/nodes/$NEW/lxc/ 2>/dev/null
```

{{< hint warning >}}
**`mv`, never `cp`.** pmxcfs enforces VMID uniqueness *across* node directories: a copy leaves the
config present under both names and fails `EEXIST`. The move is atomic within the same filesystem.
{{< /hint >}}

Carry across anything else the old directory holds — `lrm_status`, `ssh_known_hosts` entries, and
any `priv/` content are node-scoped. Leave the old directory in place until verification passes;
removing it is the last step, not the first.

### 4. Restart the cluster filesystem

```bash
systemctl restart pve-cluster pvedaemon pveproxy pvestatd
```

**No reboot is required, and running guests are not restarted.** On `dv02hyp001p01` all five guests
kept their original PIDs across the rename. A reboot is a much larger blast radius for no benefit —
do not take one unless something else demands it.

---

## Verify

```bash
readlink -f /etc/pve/local          # -> /etc/pve/nodes/dv02hyp001p01
ls /etc/pve/nodes/                  # old name gone once cleaned up
qm list                             # every guest still listed
pvesh get /nodes                    # the API agrees
curl -sk -o /dev/null -w '%{http_code}\n' https://localhost:8006/
```

{{< hint info >}}
**`ls /etc/pve/nodes/<new>` is not the check.** pmxcfs does not materialise a node directory in a
listing until something has been written into it, so waiting on the directory to appear — an
`ansible.builtin.wait_for` on the path, for instance — times out on a rename that actually
succeeded. `readlink -f /etc/pve/local` is the authoritative answer to "what does this node think
it is called".
{{< /hint >}}

Then, from the control plane:

```bash
ansible-playbook playbooks/vm-identity.yml       # allocator surveys the node by name
ansible-playbook playbooks/site.yml --limit hypervisors --check   # baseline role: changed=0
```

## Rollback

Reverse the move (`mv` the configs back), `hostnamectl set-hostname` to the old name, restore the
old `/etc/hosts` line, and restart the same services. The `/etc/pve` tarball from Prerequisites is
the backstop if pmxcfs is left inconsistent.

---

## Then update everything that names the node

The node name is a hard reference in three repos, and **none of it is inferred** — `vm_identity`
surveys the `hypervisors` group for VMIDs in use and cannot derive one host's node name from
another host's `mgmt_vm` block.

| Repo | What |
|------|------|
| `ansible-inventory-deevnet` | `proxmox_node` on the hypervisor; `mgmt_vm.node` on every guest it hosts |
| `deevnet-image-factory` | `PVE1_NODE` / `PVE2_NODE` in the `Makefile` |
| `deevnet-tenant-factory` | the fabric's `proxmox_node` default in `variables.tf` |

{{< hint warning >}}
**A stale Terraform node name fails silently.** `TF_VAR_proxmox_node` from the rendered env file
overrides the `variables.tf` default, so when the two disagree the apply reports no changes rather
than an error. It was caught only by checking PVE's own config afterwards. Keep the default correct
so a stale environment shows up as a plan diff.
{{< /hint >}}

Applying the fabric after the rename rewrites the SDN objects that embed the node name — the fabric
node id moves from `tfab/pve2` to `tfab/dv02hyp002p02`.

---

## Do not create this problem again

The Proxmox installer's default hostname is what produced `pve` and `pve2`. Since a node name cannot
be safely renamed afterwards, **a new hypervisor is named at install time**, from its ADR-0008
inventory name:

```bash
make proxmox-pve-iso-http PVE_HOSTNAME=dv02hyp003p01.mobile.deevnet.net
```
