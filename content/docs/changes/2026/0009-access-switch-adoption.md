---
title: "CHG-0009: Access Switch Omada Adoption"
weight: 9
---

# CHG-0009: Access Switch Omada Adoption

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Migration — the switch moves from standalone to controller-managed |
| **Classification** | Disruptive — adoption rewrites port VLANs, and the uplink is expected to drop until they are re-applied |
| **Status** | **Planned, on hold since 2026-09-16.** Deprioritized behind the Deevnet API and the first working tenant; it is not on that path. The research below settles the route, so the work resumes from here without repeating it. |
| **Window** | To be scheduled, with the operator on site and connected through the travel router ([Operator Access](/docs/runbook/substrate/network/operator-access/)) |
| **Site** | mobile |
| **Systems** | Access switch `dv02acc001p01` (SG2218 hardware 1.20, firmware 1.20.24); the Omada controller (6.3.0.45) in `dv02nms001v01` |
| **Automation** | To be written: `ansible-collection-deevnet.net` `playbooks/omada-switch.yml`, modeled on `playbooks/omada-wireless.yml`. `switch_vlans` becomes break-glass once the switch declares `switch_management: omada`. |
| **Risk** | High. Every path to the controller crosses this switch; if adoption does not keep the management VLAN, the controller loses the switch mid-provision and the way back is a factory reset. |
| **Related changes** | [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) — the AP, adopted the same way; [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) — the firmware this relies on |
| **Related incidents** | None |
| **Related runbooks** | [Access Switch](/docs/runbook/substrate/recovery/console-recovery/access-switch/) (the reset path, and the rollback); [Operator Access](/docs/runbook/substrate/network/operator-access/); [Important URLs](/docs/runbook/substrate/network/important-urls/) |

---

## Summary

The access switch is standalone. Its configuration is declared in inventory and applied over its
CLI by `switch_vlans`.
[ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/) decides that the
controller applies that inventory through its documented Open API instead, as it already does for
the AP since CHG-0005. This change adopts the switch and moves its port configuration to the
controller.

## Goal

- The controller lists `dv02acc001p01` as Connected, with management VLAN 99 and static
  `10.20.99.10`.
- Every declared port's native and tagged VLANs, read back from the controller, match
  `switch_ports` in inventory.
- The site's reachability checks pass, and a `DVNTM` client leases a `10.20.10.x` address.
- `host_vars/dv02acc001p01.yml` declares `switch_management: omada`, and `switch-vlans.yml`
  refuses to run without break-glass.

## Scope

**In scope:** creating the switch's networks on the controller, adopting the switch, applying its
port VLANs from inventory, and the ADR-0009 amendment for the route.
**Out of scope:** changing any VLAN or port assignment; STP, which stays off; the AP, which is
already adopted.

---

## Route: Inform URL, no reset

Chosen with the operator on 2026-09-16.

ADR-0009 §6 plans adoption of an in-service switch as a **planned rebuild**: factory reset, adopt,
provision. That takes every VLAN on site down from the reset until provisioning finishes, and a
reset switch needs DHCP on VLAN 1, which only the builder's bootstrap mode answers.

Instead, the switch keeps its working configuration and is pointed at the controller:
**Controller Inform URL = `10.20.99.40`**, with **Cloud-Based Controller Management left
disabled**. The switch's own UI notes say cloud-based management is for the Omada *Cloud-Based*
Controller (*"add the device to the controller via its serial number"*), while the Inform URL
tells *"the device where to discover the controller"*. The reset route stays as the rollback.

**ADR-0009 §6 needs amending** to allow in-place adoption through the Inform URL before this runs.

---

## Findings on 2026-09-16

All read-only.

| Check | Result |
|---|---|
| Controller device list (Open API `getSiteDeviceList`) | Only the AP. The switch does not appear, not even as pending. |
| Same subnet | Yes. The switch is `10.20.99.10/24` on VLAN 99; the controller is `10.20.99.40` on VLAN 99; they reach each other. |
| `show controller` | `Cloud-Based Controller Management: Disabled`, `Connection Status: Disabled`, `Inform URL/IP Address:` empty. The running config has `no controller cloud-based`. |
| Discovery traffic (tcpdump on the builder, VLAN 99) | Nothing on UDP 29810–29817. In two minutes the switch sent only ARP and LLDP, which shows the capture did see its traffic. The switch is not announcing itself. |
| Controller networks | `Default` (VLAN 1), `trusted` (10), `iot_vendor` (31), `guest` (40). **No VLAN 99**, and none of the other switch VLANs. |
| `gi1/0/5` | Link up, not declared in inventory. One MAC, `dc:a6:32:c5:a1:a6` (a Raspberry Pi prefix), in VLAN 1. The declared Pi ports `gi1/0/3` and `gi1/0/14` have no link, so a Pi is probably in the wrong port. |

---

## Research: what adoption does to a configured switch

Quotes are verbatim. Anything not quoted is inference, and is labeled as such.

**Configuration kept on adoption.** TP-Link, [How to Maintain Management VLAN and Port Settings
When Adopting Switches on Omada Network V6](https://support.omadanetworks.com/en/document/110873/)
(updated 2026-08-18). Applies to *"Omada Controller V6 and above"* and *"Omada Switches (Excluding
Omada Agile Switches) with the latest firmware"*.

- *"the following pre-configuration will be kept after adoption"*: Management VLAN and Interface;
  Static IP of the Interface; Static routes; Native VLAN on the port; Port speed; Link Aggregation
  Group (LAG) settings.
- *"To maintain a port related settings after adopted, the management VLAN must set as the native
  VLAN on this port, which means that to set the management VLAN ID as PVID for this port and set
  the management VLAN as untagged on this port."*
- *"VLAN 200 itself must be created on the controller first."* (VLAN 200 is the page's example
  management VLAN.)
- *"For the port not meeting the requirements above, its settings will not be maintained after
  adoption."*
- **Not on the page:** tagged VLANs, trunks, or what a port that does not qualify gets instead.

**Port VLANs are per port on 6.3.** TP-Link, [Manage Switches via the Omada Controller,
6.3.0](https://static.tp-link.com/upload/manual/2026/202608/20260814/1900004466_Manage%20Switches%20via%20the%20Omada%20Controller_6.3.0.pdf)
(August 2026), §9.1: *"The port network configurations previously included in the Switch Port
Profile have been removed."* Native Network and Network Tags Setting (*Allow All*, *Block All*,
*Custom* tagged and untagged) are set per port, under Port Settings. The Open API's
`batchModifySwitchPort` carries `nativeNetworkId`, `networkTagsSetting` and `tagNetworkIds`.
**So the ADR-0009 proof of concept's model, VLANs inside a `lan-profile`, is out of date for this
controller.**

**Order of operations.** TP-Link, [Management VLAN configuration guide, business
scenario](https://support.omadanetworks.com/us/document/13219/) (updated 2026-08-25, controller
v6.2 and above): create the networks, adopt the switch, then set the management VLAN under the
switch's Config > VLAN Interface. *"The switch may be reprovisioned during this process."*

**Pre-configuring the switch on the controller is not an option.** TP-Link staff on the
[community forum](https://community.tp-link.com/en/business/forum/topic/662184) (2024, controller
5.x): *"For the configuration on the devices themselves such as the port setting on switch, we are
not able to pre-configure but have to reset the switch after adoption."* The [device-key
zero-touch guide](https://support.omadanetworks.com/en/document/35227/) (updated 2026-08-20) needs
Cloud Access and Device Management, and says nothing about pre-configuring ports.

**Firmware fit.** SG2218 release notes: 1.20.14 *"Recommended Omada Controller V6.0.0"*; 1.20.19
*"Recommended Omada Controller V6.1.0"*. No release note was found for 1.20.24, the build the switch
runs and the newest on TP-Link's download page.

**Why the switch may be silent.** The 1.20.4 release note: *"Add support for enabling/disabling
the switch sending Omada controller related broadcast packets via CLI."* A [community
thread](https://community.tp-link.com/en/business/forum/topic/843928) about other models mentions
`no controller discover` and `no controller dns-adoption`, and standalone switches querying the
DNS name `omada` every 15 seconds. Neither line is in this switch's running config. Not verified on
the SG2218; the Inform URL route does not depend on it.

### Expected state after adoption

*Inference* from doc 110873, before any port is re-applied. To be confirmed on the day.

| Port | Today | Management VLAN native? | Expected |
|---|---|---|---|
| `gi1/0/2`, `gi1/0/16` (builder) | access 99 | yes | kept |
| `gi1/0/15` (hv01, carries the controller) | native 99, tagged 25, 35 | yes | native kept; tagged unknown |
| `gi1/0/13` (hv02) | native 99, tagged 50, 51 | yes | native kept; tagged unknown |
| `gi1/0/4` (AP) | native 99, tagged 10, 30, 31, 40 | yes | native kept; tagged unknown |
| `gi1/0/1` (uplink to OPNsense) | native 999, tagged all | **no** | **not maintained**: routing through `10.20.99.1` is likely lost |
| `gi1/0/3`, `gi1/0/14` (IoT) | access 30 | no | not maintained |
| Management interface | VLAN 99, static `10.20.99.10` | — | kept, **if the VLAN 99 network exists on the controller first** |

The part that matters: the management path — controller, builder, both hypervisors, the AP and
the switch, all untagged on VLAN 99 — should survive adoption. The API then stays reachable to
re-apply the rest. What is expected to break until then: routing on the uplink, the tagged VM,
wifi and tenant VLANs, and the IoT access ports.

---

## Prerequisites

- [ ] ADR-0009 §6 amended for in-place adoption through the Inform URL.
- [ ] `gi1/0/5` resolved: the Pi moved to its declared port, or the port declared in inventory.
- [ ] `playbooks/omada-switch.yml` written, and a plan-mode run reviewed.
- [ ] Every switch VLAN, **including 99 and 999**, exists as a controller network (controller-only
  apply; no switch contact).
- [ ] The site Device Account read (`GET device-account`). It replaces the switch's login on
  adoption, so it becomes the credential break-glass `switch_vlans` needs.
- [ ] Operator on site, connected through the travel router. Vault decrypted.
- [ ] `show running-config`, `show vlan brief` and `show controller` captured on the day.

## Procedure (outline)

1. **Networks first.** `omada-switch.yml -e omada_apply=true` creates the missing networks, VLAN
   only, matched on VLAN id. The switch is not touched.
2. **Point the switch at the controller.** Set the Inform URL to `10.20.99.40` in the switch UI,
   with cloud-based management left disabled. **Stop point:** confirm the switch appears as
   pending in the controller.
3. **Adopt and re-apply.** `omada-switch.yml -e omada_apply=true -e omada_adopt=true`:
   - adopt, and wait for Connected;
   - read back the switch networks, and stop if the management VLAN is not 99 with `10.20.99.10`;
   - apply per-port native and custom tagged VLANs from `switch_ports`, **uplink first**, with
     tagged = allowed minus native and STP and loopback detection stated off;
   - verify every port against inventory, then ping `10.20.99.1`, the controller, both
     hypervisors, the AP and `10.20.35.20`.
4. **Hand over ownership.** Set `switch_management: omada` in inventory, and confirm
   `switch-vlans.yml` refuses.
5. **Record what adoption actually kept**, port by port, to replace the inference in the table
   above.

## Undo

- **Before adoption:** clear the Inform URL. Nothing else has changed on the switch.
- **After adoption, controller still reaches the switch:** re-run the port apply.
- **Controller has lost the switch:** the reset route in
  [Access Switch](/docs/runbook/substrate/recovery/console-recovery/access-switch/): factory reset, reach it
  at `192.168.0.1` or through bootstrap DHCP, then
  `switch-vlans.yml -e switch_vlans_break_glass=true`. The whole site is down meanwhile, as
  ADR-0009 already accepts for that route.

---

## Outcome

Not yet run.

## Follow-ups

- [ ] Resume after the Deevnet API and the first tenant are working.
- [ ] Amend ADR-0009 §6, and its Evidence table (per-port VLANs on 6.3; what adoption keeps).
- [ ] Resolve `gi1/0/5`.
- [ ] Write `playbooks/omada-switch.yml`.
- [ ] Record the Device Account credentials for break-glass.
