---
title: "INC-0002: Controller VM Silent — Running but Off the Network"
weight: 2
---

# INC-0002: Controller VM Silent — Running but Off the Network

| | |
|---|---|
| **Date** | 2026-09-15 |
| **Site** | mobile (`dvntm`) |
| **Systems** | Network-management VM `dv02nms001v01` (VMID 204 on `dv02hyp001p01`), running the Omada controller container |
| **Severity** | Management-plane only. The controller was unreachable, which **blocked [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)**. No client-facing outage: the AP was still standalone on its old firmware, so wireless kept serving. |
| **Status** | **Open · Mitigated.** **Service restored by a guest reboot; root cause not established.** The controller and its Omada data (local Owner, Open API client) came back intact. Action 2 is done — `qm agent` is now a trustworthy probe — and actions 1, 3 and 4 are open. |
| **Times** | Local (EDT, UTC−4), as observed from the builder during the CHG-0005 window |

---

## Summary

At the start of the [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)
window, the controller VM `dv02nms001v01` reported `status: running` to Proxmox but had no
presence on the network at all — no ARP reply, no QEMU guest-agent response, and nothing
answering on `10.20.99.40:8043`. The guest was wedged in a way that Proxmox's own "running"
status did not reflect.

The VM had been **destroyed and re-created by the Terraform provisioning token within the
preceding 24 hours** (destroyed 2026-09-14 22:26, re-created 2026-09-15 17:15), and had been up
about 2 h 20 m before it went silent. A guest reboot restored it fully. Why the freshly
provisioned guest lost its network stack after that time was not determined — the guest was
rebooted before a console capture, so the evidence that would have shown the cause was not
collected.

## Impact

- The Omada controller was unreachable by name and IP for roughly the length of the outage.
- **CHG-0005 could not start** — the AP cannot be adopted without the controller. Phase 0 of that
  change became the diagnosis of this incident.
- **No client-facing impact.** The AP had not yet been adopted; it served its hand-set SSIDs
  standalone throughout. Other domain VMs on `dv02hyp001p01` were unaffected.

## Detection

Found by the operator's assistant during CHG-0005 Phase 0 reconnaissance, not by any monitor.
A routine reachability sweep of the management segment showed `10.20.99.40` (the controller)
failing while every other management host answered. Nothing was watching the controller itself,
so the outage had been silent since roughly 19:36 and would have stayed silent until someone
tried to use it.

## Timeline

| Time (EDT) | Event |
|---|---|
| 2026-09-14 22:26 | VMID 204 **destroyed** (`qmdestroy`, `root@pam`) — from the Proxmox task log |
| 2026-09-15 17:15 | VMID 204 **re-created and started** by `terraform-prov@pve!tf-prov-token` |
| 2026-09-15 ~19:36 | Last Kea DHCP renewal for the VM's MAC (`02:de:20:00:00:cc` → `10.20.99.40`). Networking healthy up to here. |
| 2026-09-15 ~20:43 | That DHCP lease expired **unrenewed** — the guest had stopped talking to the network |
| 2026-09-15 ~20:50 | Outage found during CHG-0005 Phase 0: running, no ARP, no guest agent, API dead |
| 2026-09-15 (shortly after) | Operator rebooted the guest; agent came up, `10.20.99.40` restored, `/api/info` healthy, Omada data intact |

## Symptoms

- Proxmox `qm status 204` → `running`; the KVM process was up at ~35% CPU.
- `ping 10.20.99.40` failed; `ip neigh` on the host showed the VM's address `INCOMPLETE`.
- `qm agent 204 ping` → `QEMU guest agent is not running`, though the VM config has
  `agent: enabled=1`.
- `curl https://10.20.99.40:8043/api/info` → connection failure.
- The VM's Kea lease had expired without renewal (last renew ~19:36).

## Investigation

The question was whether the fault was in the host/hypervisor networking or inside the guest.
Host-side checks came back clean:

- Host storage healthy — `bigthin` pool 3.6% data, `pve-root` 51%, no thin-pool pressure.
- No block or I/O errors in `dmesg`.
- `tap204i0` present, `UP`, and in the `forwarding` state on `vmbr0` — the guest's virtual NIC
  was attached and the bridge was carrying it.
- Other guests on the same bridge were reachable, so `vmbr0` itself was fine.

That isolated the fault to **inside the guest**: the virtual NIC was attached and the bridge
healthy, but the guest was not answering ARP, not renewing DHCP, and not running its guest
agent — the picture of a wedged guest OS or its network stack, not a hypervisor problem.

**The evidence that would have named the cause was not collected.** The next step in the plan
was to open the noVNC console (the VM has no serial port) and read whatever was on screen — a
panic trace, an emergency shell, or a healthy login. The guest was rebooted before that capture,
which restored service but discarded the state. The root cause is therefore **unproven**, and
this record does not guess one.

## Root cause

**Not established.** The fault was inside the guest — a freshly Terraform-provisioned VM lost its
network stack (no ARP, no DHCP renewal, no guest agent) after about 2 h 20 m of uptime, while the
host, its virtual NIC and the bridge stayed healthy. Whether this was a guest kernel hang, a
NetworkManager failure, an artifact of the Terraform re-create, or something else was not
determined, because the guest was rebooted before the console was read.

## Recovery

The operator rebooted the guest (VMID 204). It came back with the guest agent running, leased
`10.20.99.40` again, and `/api/info` reported `6.3.0.45`, `configured: true`. The Omada data
survived: the local Owner and the Open API client both still worked, verified by a plan-mode run
of `omada-wireless.yml`. CHG-0005 then proceeded on the recovered controller.

## Contributing factors

- **Nothing monitors the controller.** A silent controller is indistinguishable from a quiet one;
  the outage was found only because someone went to use it. This is the same shape as
  [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/)'s detection gap.
- **The controller VM is under Terraform lifecycle and was destroyed and re-created within 24 h.**
  The Omada data survived this time, but a re-create that did not preserve the data disk would
  wipe the controller — which is exactly what the 2026-09-11 reset did. The controller being a
  Terraform-managed, rebuildable object is a standing risk to its stateful data.
- **`status: running` is not a health signal.** Proxmox reported the VM up throughout; only the
  guest agent and the network told the truth.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Determine why the freshly provisioned guest lost its network stack — next occurrence, capture the noVNC console **before** rebooting (panic trace / emergency shell / journal since boot) | `dv02nms001v01` | {{< action-status "Open" >}} |
| 2 | Confirm `qemu-guest-agent` is enabled and started on the Fedora VM template, so `qm agent` is a reliable probe rather than another thing that is "not running" | image factory / template | {{< action-status "Done" >}} 2026-09-21 — installed and enabled by the template kickstart (`kickstart.cfg.pkrtpl`, package and `%post`), agent flag set by Packer (`qemu_agent = true`) and by `proxmox_vm` (`agent: enabled=1`). On the live site `qm agent <id> ping` answers for `dv02nms001v01` and every other running domain VM |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 3 | Monitor the controller's health (`/api/info` reachable and `configured: true`) on a schedule, so a silent controller raises an alert instead of waiting for the next change window | management plane | {{< action-status "Open" >}} |
| 4 | Establish whether a Terraform re-create of the domain VMs preserves the Omada data disk, and if not, protect the controller's state (out-of-band backup, or a lifecycle guard) so a rebuild cannot wipe it | tenant/mgmt Terraform; [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) | {{< action-status "Open" >}} |

## Lessons learned

- **A "running" VM is not a reachable service.** Health has to be measured from the service's own
  response, not the hypervisor's process state — the same lesson INC-0001 drew about a router
  answering on its own interfaces.
- **Recover, but capture first.** A reboot that fixes a silent guest also destroys the evidence.
  When a hang is not actively hurting anything client-facing, one console read before the reboot
  is the difference between a root cause and an open question. This incident chose speed and is
  left without a cause.

## Related changes

- [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) — blocked by this outage;
  its Phase 0 was the diagnosis and recovery.
- [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) — built `dv02nms001v01` and moved the
  controller onto it.

## Related runbooks

- [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/) — for the
  controller container; this incident was one layer below it, in the guest itself.
