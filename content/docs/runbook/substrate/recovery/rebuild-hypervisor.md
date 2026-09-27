---
title: "Rebuild a Hypervisor"
weight: 5
---

# Rebuild a Hypervisor

Bringing a Proxmox node back after a fresh install: a failed OS disk, replaced hardware, or a node
beyond repair. Proxmox is installed by hand from the ISO, and in normal service a node is upgraded
in place along Proxmox's upgrade path ([Patching](/docs/runbook/substrate/lifecycle/patching/)),
so this is the path for when the node itself is lost.

The install and the node's own configuration are the same for both hypervisors:
[Build Management Plane](/docs/runbook/substrate/building-recovery/build-management-plane/),
Steps 1 to 8. Start at its **Step 1**, which decides what survives on which disk. What differs is
what runs on the node afterwards.

---

## Management hypervisor (`dv02hyp001p01`)

Continue with Build Management Plane's **Step 9**: the Fedora template, then every management-plane
VM from code, each keeping its allocated VMID, MAC and address.

The VMs come back empty unless their data disks survived. Before rebuilding one, check what its
service keeps and where:

- **OpenBao** (`dv02idn001v01`) holds the site's secrets. A fresh instance generates new
  once-only credentials: encrypt, commit and push them before going further
  ([INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/)). Restoring its data from a
  snapshot is still unproven
  ([OpenBao Drills → Snapshot restore](/docs/runbook/substrate/recovery/substrate-secrets-drills/#snapshot-restore)).
- **The Deevnet API** registry and the **tenant state store** (`dv02prv001v01`) sit on the VM's own
  disks with no copy ([ADR-0014](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/)).
- **The Omada controller** (`dv02nms001v01`) has no snapshot
  ([Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/)).

---

## Tenant hypervisor (`dv02hyp002p02`)

After Build Management Plane's Steps 1 to 8, running **every** Step 8 tag on this node, in order:

1. **Recreate the Deevnet API's Proxmox token.** The API has its own token on this node,
   `deevnet-api@pve!tenants` under the role `DeevnetTenantBuilder`
   ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)). Like every Proxmox token its secret
   is shown once. Issue it again, put it in `group_vars/deevnet_api/vault.yml`, `make vault`,
   commit and push, then `ansible-playbook playbooks/site.yml --limit deevnet_api` in
   `deevnet.mgmt`. The role's privilege list is not recorded anywhere: read it with
   `pveum role list` before a planned rebuild.
2. **The template:** `make proxmox-fedora-pve2` in `deevnet-image-factory`.
3. **The fabric:** `make fabric-apply` in `deevnet-tenant-fabric`. It rebuilds the underlay, the VTEP
   identity and the EVPN controller from code.
4. **The egress agent:** `ansible-playbook playbooks/tenant-egress-agent.yml` in `deevnet.net`.
5. **Each tenant's network:** reconcile every tenant through the API
   ([Tenant Admission → Operator-only calls](/docs/runbook/substrate/tenant-admission/#operator-only-calls)).
   A reconcile rebuilds the tenant's zone, VNet and subnet on the fabric, with the same index.
6. **Tell each tenant.** A reconcile does **not** rebuild workloads, and a tenant's plain apply does
   not either. What a tenant does is
   [After a Site Rebuild](/docs/runbook/tenant/recovery/after-a-site-rebuild/) in the tenant guide.

---

## Verify

- Build Management Plane's **Verify** section passes on the node.
- On the tenant hypervisor, `pvesh get /cluster/sdn/zones` lists every tenant's zone, and a tenant
  workload reaches the internet through the perimeter.
