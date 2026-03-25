---
title: "Troubleshooting"
weight: 7
---

# Troubleshooting & Known Issues

## Lost switch access after trunk configuration
- Connect via console cable
- Check `show interface switchport gigabitEthernet 1/0/1` for native VLAN mismatch
- Revert to access mode on uplink if needed

## Device not getting DHCP lease
- **Kea not listening on VLAN interfaces:** Check OPNsense GUI → Services → Kea DHCP → Settings → Interfaces. All VLAN interfaces must be selected. By default, Kea only listens on LAN (re0). The `opnsense_dhcp` role automates this, but verify with: `ssh root@10.20.99.1 'cat /usr/local/etc/kea/kea-dhcp4.conf'` and check the `interfaces-config` section.
- Verify port VLAN assignment: `show vlan brief`
- Verify DHCP subnet exists in OPNsense for that VLAN
- Check OPNsense firewall rules allow DHCP on VLAN interface
- Check `show mac address-table` to confirm device is on expected port

## AP not discoverable or adoption fails in Omada
- **Factory reset AP** uses static fallback IP `192.168.0.254`, not DHCP. Add temp IP on builder (`sudo ip addr add 192.168.0.1/24 dev enp4s0`) and access AP web UI at `http://192.168.0.254` (admin/admin) to set inform URL.
- **Adoption timeout (errorCode -39002):** AP can't reach controller on required ports. Check `ss -tlnp | grep 29814` — Omada must listen on **TCP** 29814 (not just UDP). Newer AP firmware (EAP650-Outdoor) requires TCP 29814 for v2 adoption.
- **Omada controller version mismatch:** Controller 5.12.7 does not listen on TCP 29814. Update the controller to a version that supports v2 adoption protocol.
- **Firewalld missing ports:** Verify `sudo firewall-cmd --list-ports` includes `29810-29814/udp` AND `29811-29814/tcp`.

## Builder lost connectivity during Step 5
- Verify ethernet cable is connected to `gi1/0/16` — do not rely on WiFi for substrate access
- Check port VLAN assignment: `show interface switchport gigabitEthernet 1/0/16`
- Verify VLAN 99 interface is enabled with IP `10.20.99.1` in OPNsense
- If the builder has the wrong static IP config, revert the port to VLAN 1 and re-run the builder playbook with the dvntm inventory
- If the builder is unreachable, Omada adoption ([Step 12](../port-migration/#step-12-omada-device-adoption)) cannot proceed — but the switch and AP continue to function independently
- Last resort: revert the builder port to VLAN 1 via console:
  ```
  configure
  interface gigabitEthernet 1/0/16
    switchport access vlan 1
  end
  copy running-config startup-config
  ```

## Inter-VLAN routing not working
- **Check default gateway on target device:** Devices on VLAN 99 (management) need `ip route 0.0.0.0 0.0.0.0 10.20.99.1` to route responses back to other VLANs. Without this, the device receives cross-VLAN traffic but replies are silently dropped (no return route). This was the root cause of the "builder can't ping cross-VLAN gateways" issue — the switch had no default gateway.
- Verify VLAN interfaces have IP addresses assigned in OPNsense
- Check OPNsense firewall rules for inter-VLAN traffic
- Verify routing table: OPNsense GUI -> System -> Routes

---

## To Do

Automation gaps and improvements identified during the initial migration run.

- [ ] **Automate OPNsense interface assignment and IP config:** OPNsense (as of 25.7) has no API for interface assignment ([GitHub #7324](https://github.com/opnsense/core/issues/7324)) OR setting interface IPs (`setInterface` does not exist in the `OverviewController`). Step 5a requires two manual GUI steps: assigning VLAN devices and configuring IPs. Fix: enable SSH access for `a_autoprov` on OPNsense, write a playbook that edits `/conf/config.xml` to add assignments and IPs, then call `configctl interface reconfigure`.
- [ ] **OPNsense firewall rules for new VLAN interfaces:** New OPT interfaces have a default-deny policy with no rules. Each VLAN interface needs at least a temporary pass-all rule before any traffic flows. The Step 5a GUI instructions should include adding pass rules per interface, or Step 9 (firewall automation) should run immediately after interface assignment. Consider automating temp pass rules via the OPNsense filter API as part of Step 5a.
- [ ] **Fix builder port VLAN membership bug:** The `no switchport general allowed vlan 1` command on SG2218 does not reliably leave VLAN 99 as a member. The 05d-builder-port-move playbook must explicitly add VLAN 99 untagged AND remove VLAN 1 in the correct order. Verify the playbook matches what worked manually: `switchport general allowed vlan 99 untagged` first, then `no switchport general allowed vlan 1`.
- [ ] **Remove VLAN 1 from trunk after migration:** VLAN 1 (System-VLAN) remains as an untagged member on the trunk uplink after migration. It is harmless (PVID 999 takes precedence) but should be cleaned up for hygiene.
- [ ] **Verify `cli_config` idempotency on TP-Link SG2218:** The `cli_config` module does not detect existing config on SG2218 due to the minimal cliconf plugin. All switch tasks use `cli_command` with `changed_when: true` (always reports changed). Investigate implementing `get_config` parsing in the cliconf plugin for proper idempotency.
- [ ] **Add pi03, pi04, hv02 port assignments:** These devices were removed from `switch_ports` because they were not connected during migration. Re-add when physically cabled.
- [ ] **Add `builder` group to inventories:** The `builder` group was missing from both `dvntm` and `dvntm-new` inventories, causing the `base` role play in `site.yml` to skip. Added during migration — verify this is the correct long-term grouping.
- [ ] **Switch inventory after builder cutover:** After the builder moves to VLAN 99, the `dvntm` inventory still resolves the switch `ansible_host` to `192.168.10.10` (unreachable from VLAN 99). All post-cutover switch steps must either use the `dvntm-new` inventory (`-i ../ansible-inventory-deevnet/dvntm-new`) or override `ansible_host`. Consider promoting the inventory earlier or adding a migration-phase inventory override to the Makefile.
- [ ] **Fix test-port default port number:** The `04-switch-test-port.yml` playbook defaults to `gigabitEthernet 1/0/24`, but the SG2218 only has 18 ports. Update the default to a valid unused port (e.g., `gigabitEthernet 1/0/18`).
- [ ] **Step 6 verify assumes DHCP before Step 7:** The Step 6 verification expects a DHCP lease on the test VLAN, but DHCP for new subnets is not configured until Step 7. Update Step 6 verify to only check gateway reachability (ping), not DHCP.
- [x] **Switch default gateway for cross-VLAN routing:** The switch had no default route, causing cross-VLAN traffic responses to be silently dropped. Fixed: added `ip route 0.0.0.0 0.0.0.0 10.20.99.1` and gateway to inventory. The `05a-switch-dual-mgmt.yml` playbook should also configure the default gateway, or add it to the `switch_vlans` role so it's applied during any switch provisioning.
- [x] **Update Omada controller for v2 adoption:** Controller upgraded to 6.1. TCP 29814 now supported. AP adoption works.
- [ ] **Update EAP650-Outdoor firmware:** AP firmware 1.0.4 (2023) does not accept VLAN config from Omada 6.1 controller — `ssidOverrides` always show `vlanEnable: false` despite correct controller-side config. Force Provision and reboot don't help. Workaround: configure SSIDs with VLAN tagging via AP standalone web UI. Fix: update AP firmware to a version compatible with Omada 6.1, then re-adopt and verify VLAN provisioning works via controller.
- [ ] **Omada SSID automation incomplete:** The `13-omada-ssids.yml` playbook creates SSIDs and Networks via API, but Omada 6.1 requires both Network objects AND `networkId` references in SSID `vlanSetting.customConfig`. Even with correct API config, the AP didn't apply VLANs (firmware issue). For rebuild: update AP firmware first, then verify the full automation chain works end-to-end.
- [ ] **AP standalone config not automated:** SSIDs were configured manually via the AP's standalone web UI as a workaround. Investigate if the EAP650-Outdoor has a standalone API, or automate via Omada after firmware update.
- [ ] **Remove temp VLAN 99 DHCP pool:** A temporary DHCP pool (10.20.99.200-210) was added for AP discovery. Remove it after the AP gets a static IP via Omada adoption. Management VLAN devices should use static IPs only.
- [ ] **OPNsense automation filter API non-functional:** The `firewall/filter/addRule` API saves rules but they never compile into the pf ruleset on OPNsense 25.7.10. The `05e-opnsense-temp-firewall.yml` playbook uses this API but the rules don't take effect. Temp rules had to be loaded via `pfctl -f` over SSH. Investigate whether this is a version bug or misconfiguration.
- [ ] **Automate Kea DHCP interface enablement in subnet creation:** The `configure_kea_interfaces.yml` task was added to the opnsense_dhcp role. Verify it runs correctly during a clean rebuild and doesn't conflict with manual GUI interface selections.
