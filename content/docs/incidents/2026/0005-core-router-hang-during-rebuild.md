---
title: "INC-0005: Core Router Hard Hang During a Provisioning VM Rebuild"
weight: -5
---

# INC-0005: Core Router Hard Hang During a Provisioning VM Rebuild

| | |
|---|---|
| **Date** | 2026-10-07 |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router); by consequence, every routed path at the site. `dv02prv001v01` (provisioning VM), which was being rebuilt. Seen from `dv00bld001p01` (the Builder). |
| **Severity** | Site gateway lost for about 45 minutes: no routing between segments, no site DNS, the operator's normal path to the Builder cut. The Deevnet API and the state store were down for 53 minutes, most of it beyond the outage the rebuild had planned. Recovery needed the router's console. |
| **Status** | Open · {{< inc-status "Mitigated" >}}. Service is restored. The fault is the one [INC-0004](/docs/incidents/2026/0004-core-router-lost/) left unfixed, and it will recur. |
| **Times** | EDT (UTC−4) |

---

## Summary

At about 17:16 the core router stopped forwarding, in the middle of
[CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/) step 3, the restore rehearsal. The
rehearsal had destroyed the provisioning VM and was rebuilding it from its roles. The rebuild had
pushed a 176 MB container image from the Builder to the new VM, and had just started a 461 MB one.
Both go from management to Platform, so both cross the router. The second push never finished.

The operator lost the trusted Wi-Fi network, came back in over the travel router's LAN, and found the
router **hard-hung**: connected to a screen and keyboard, it did not respond. A power cycle brought it
back. The provisioning VM was then restored from a dump taken before the rebuild, and came back
exactly as it had been.

**This is a recurrence of INC-0004's first event.** That was also a hard hang, also in the middle of a
deploy pushing a container image to a Platform VM, and its cause was never established. This record is
a new instance of it, with the same gap: no evidence survived.

**The provisioning VM is not in a runtime path, and the incident shows it.** The VM was gone from
17:14. The network was lost two minutes later, when bulk traffic crossed the router. The one thing that
calls the API at runtime, the tenant egress agent, failed every five minutes for 50 minutes and left
tenants' routes as they were.

## Impact

- No routing between segments from about 17:17 to about 18:02. That includes trusted → management,
  the operator's normal path to the Builder, and Wi-Fi clients' DHCP and DNS.
- No site DNS. The Builder, asking the router for names, could not reach GitHub by name while its
  management link was up and the router was not.
- The Deevnet API and the state store were down from 17:14 to 18:07. About five minutes of that was
  planned. Tenants could not apply. No tenant tried.
- The restore rehearsal was abandoned. Nothing was restored from a backup.
- The Builder was rebooted three times by the operator. Its `/tmp` is memory-backed, so the rebuild's
  log and the before-picture taken for the rehearsal were lost.
- **Not affected:** tenants' workloads, their egress, device Wi-Fi keys, the broker and the log store
  were not changed. Hosts on the management segment reached each other throughout. No tenant data was
  lost: the registry and the state bucket came back from the dump, and three encrypted backups were on
  the drive.

## Detection

The operator lost the trusted network and could not reach the Builder by the usual path, about five
minutes after the router stopped. Nothing alerted: the site has no monitoring
([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) is Proposed).

## Timeline

| Time | Event |
|---|---|
| 17:12:03 | CHG-0039: a fresh backup is written to the drive and read back with the key from the vault. |
| 17:13:29–17:14:06 | A full dump of VM 201 (`dv02prv001v01`), with the VM stopped, to the management hypervisor's local storage. This is the rehearsal's fallback. |
| ~17:14:20 | VM 201 is shut down and destroyed. The API and the state store are down from here, as planned. |
| 17:14:33 | `site.yml --limit dv02prv001v01` clones a new VM 201 from the template. |
| 17:15:10 | The new VM starts and answers on its address. |
| 17:15:50 | The state store's image, 176 MB, is pushed from the Builder to the VM, through the router. It completes, and the store starts. |
| 17:15:55 | The tenant egress agent on `dv02hyp002p02` cannot reach the API and leaves its routes as they are. It does the same every five minutes until 18:05. |
| 17:16:19 | The rebuild logs in to OpenBao on Platform, through the router. It succeeds. |
| **17:16:32** | The rebuild starts pushing the PostgreSQL image, 461 MB, to the VM. This is its last line, and the latest time the router is known to have been forwarding. |
| 17:21:23 | The operator connects to the Builder from `192.168.8.170`, the travel router's LAN. |
| 17:25:58 | The operator reboots the Builder. It is rebooted twice more, and is up for good at 17:37:24. |
| ~17:35 | The operator disconnects the core router, to leave the Builder a working path to the internet. |
| 17:40 | Claude finds the Builder's management link with no carrier and nothing on `10.20.0.0/16` answering. The rebuild had stopped with the Builder's first reboot. |
| ~17:50 | The operator reconnects the router. Hosts on the management segment answer. The router answers neither ARP on its LAN nor ping on its WAN. |
| ~17:58 | The operator connects a screen and keyboard to the router. It does not respond. The operator power-cycles it. |
| ~18:02 | The router is forwarding. Platform, IoT Backend and tenant transit answer. |
| 18:05–18:06 | VM 201 is restored from the dump, on the hypervisor, and started. Nothing crosses the router. |
| 18:07 | The API and the state store answer. The registry holds its 4 tenants and 203 audit entries, the bucket its 3 state files, the store its 5 users. A tenant's plan gives the same result as before the rehearsal. |
| 18:08 | The tenant egress agent, run by hand, reaches the API and succeeds. |

## Symptoms

- The trusted Wi-Fi network stopped working for the operator.
- From the Builder, with its management link up: both hypervisors and the network management VM
  answered; `10.20.99.1` did not answer ARP; `192.168.8.106`, the router's WAN, did not answer; nothing
  on Platform answered.
- At the router's console: no response to the keyboard.

## Investigation

**The Builder's journal gives the order of events.** The rebuild's steps are logged there as they ran:
the clone at 17:14:33, the first image at 17:15:50, an OpenBao login through the router at 17:16:19, the
second image at 17:16:32, and then nothing from the rebuild at all. The operator's session from the
travel router's LAN follows at 17:21:23.

**The half-built VM agrees.** After recovery it was running the state store, started at about 17:16,
and held no PostgreSQL image, no database and no API. The second push had not arrived.

**The provisioning VM's absence did not cause the loss.** It had been gone for two minutes when the
network failed, and it stayed gone for 51 minutes while the router was back and everything else worked.
The tenant egress agent's log shows what a missing API does at runtime: `cannot reach
https://api.mobile.deevnet.net:8080; leaving /etc/frr/frr.conf.local as it is`.

**The image push was not the only bulk traffic.** Proxmox tells every new clone to upgrade all its
packages on first boot. The provisioning VM upgraded 203 packages when it was first built, and the new
clone started the same thing at 17:15:10, downloading through the router while the images were pushed
to it. This was found afterward, and it had been an open item since
[CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/).

**A second rebuild without either flow did not hang the router.** At 19:11 the same VM was rebuilt with
its first-boot upgrade off and its images delivered on an ISO from its own hypervisor. The router
answered every check for the nine minutes it took. One run each way suggests load is the trigger; it
does not establish it.

**Nothing was read from the router.** It was power-cycled from a hard hang, and it keeps no log across
one (INC-0004, Contributing factors).

## Root cause

**Not established.** The router hung hard, with its console dead, while a sustained bulk transfer
crossed it from management to Platform. That has now happened twice, in INC-0004's first event and
here, and both times a deploy was pushing a container image to a Platform VM.

Two things are different from INC-0004's later events, where the LAN NIC `re0` hit watchdog timeouts
and the box stayed alive. Here the box did not stay alive. Whether a hard hang is a worse form of the
`re0` fault or a separate one is still open, as it was in INC-0004.

INC-0004's corrective action 2 proposed reproducing the fault deliberately, by pushing sustained traffic
across VLANs with the console attached and the temperature recorded. This incident did the first half
by accident and none of the second.

## Recovery

The operator power-cycled the router at its console at about 17:58. It was forwarding by about 18:02.

VM 201 was restored from the dump taken at 17:13, with `qmrestore` on the management hypervisor, and
started at 18:06. The restore used no path through the router. The API, the state store, the registry
and the state bucket were checked against what they held before the rehearsal.

The router's configuration was not checked against inventory after the power cycle.

## Contributing factors

- **INC-0004's fix was still open.** The vendor driver for the router's Realtek NIC (INC-0004,
  Follow-up 3) had not been installed, and no change record for it existed.
- **The change did not name the risk.** CHG-0039's risk table covered the restore rehearsal disturbing
  the provisioning VM. It did not cover what a rebuild of that VM does on the way: push several hundred
  megabytes of images through the router. INC-0004 had already recorded that as the circumstance of a
  hang.
- **Every new VM upgrades itself through the router on first boot**, unless told not to. The
  rebuilt VM was doing so when the router hung.
- **Every image for a Platform VM crosses the router.** The Builder is on management and the VMs are
  on Platform, so there is no way to build or rebuild one without a bulk transfer over `re0`.
- **The operator could not log in at the Builder's console.** Every account on the Builder was
  password-locked, so with the network gone the console was no use, and the Builder was rebooted in the
  attempt to get back in.
- **No monitoring**, and **no evidence survives a hard hang**: both as in INC-0004.
- **The rehearsal's working files were in memory.** The Builder's reboot took the rebuild's log and the
  before-picture with it.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Install Realtek's vendor driver on the router, as its own change record (INC-0004, Follow-up 3 and corrective action 4). Two hard hangs now rest on it | new CHG | {{< action-status "Open" >}} |
| 2 | Enable a crash dump device on the router before the next bulk transfer across it, so a third hang leaves evidence (INC-0004, preventive action 2) | `dv02cor002p01` | {{< action-status "Open" >}} |
| 3 | Check the router's firewall rules, reservations and resolver overrides against inventory after the power cycle | `dv02cor002p01` | {{< action-status "Open" >}} |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Until corrective action 1 is done and measured, treat any image push to a Platform or IoT Backend VM as a change that can take the router down: console attached, operator present, and a way back that does not cross the router | change management | {{< action-status "Open" >}} |
| 2 | Add the risk to CHG-0039, and decide how its rehearsal rebuilds the provisioning VM without a bulk transfer across the router, or after the driver change. Done: images on an ISO from the VM's hypervisor, first-boot upgrade off, and the rehearsal passed that way | [CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/) | {{< action-status "Done" >}} 2026-10-07 |
| 3 | Give the Builder's operator account a console password that survives a rebuild | `deevnet.builder`, inventory | {{< action-status "In Progress" >}} |
| 4 | Keep a change's working files on disk, not in memory, when losing them would cost the change its evidence | practice | {{< action-status "Open" >}} |
| 5 | Decide whether every substrate VM is built without a first-boot upgrade, and how images reach Platform and IoT Backend VMs as a matter of course, not only in this rehearsal | CHG-0008's open item; `deevnet.mgmt` | {{< action-status "Open" >}} |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 1 | Restore the provisioning VM and confirm the registry, the state bucket and a tenant's plan are as they were | `dv02prv001v01` | {{< action-status "Done" >}} 2026-10-07 |
| 2 | Set a console password for the operator on the Builder | `dv00bld001p01` | {{< action-status "Done" >}} 2026-10-07 |
| 3 | Remove the dumps of VM 201 from the management hypervisor (one from each rehearsal attempt) once the rehearsal has passed. They held the registry and tenants' state unencrypted | `dv02hyp001p01` | {{< action-status "Done" >}} 2026-10-07 |
| 4 | Rotate the automation's Proxmox API token on the management hypervisor. The rehearsal's new USB pass-through tasks wrote it into the Builder's journal; the tasks are corrected | `dv02hyp001p01`, the inventory vault | {{< action-status "Open" >}} |

## Lessons learned

- **A fault left open is a risk on every later change that touches its trigger.** INC-0004 recorded
  that a hang came during an image push across the router. A change that rebuilds a Platform VM should
  have read that as its own risk.
- **The fallback that did not cross the router is what made recovery quick.** The dump sat on the
  hypervisor that runs the VM. A fallback that needed the Builder to push anything to Platform would
  have needed the path that had just failed.
- **A machine nobody can log in to at its console is not recoverable from its console.**

## Related changes

- [CHG-0039: Backup to an Attached SSD](/docs/changes/2026/0039-backup-to-an-attached-ssd/): its step 3
  was in progress when this happened.
- [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/): in progress during
  INC-0004's first event, the same circumstance.

## Related runbooks

- [Console Recovery: Core Router](/docs/runbook/substrate/recovery/console-recovery/core-router/)
- [Backup and Restore](/docs/runbook/substrate/recovery/backup-and-restore/)
