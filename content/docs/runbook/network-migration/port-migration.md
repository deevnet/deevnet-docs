---
title: "Port Migration & Wireless"
weight: 5
---

# Port Migration & Wireless

Move remaining switch ports to their assigned VLANs, perform the management cutover, adopt devices in Omada, and configure AP SSIDs.

---

## Step 10: Migrate Remaining Access Ports

Move all remaining switch ports to their assigned VLANs as defined in `host_vars/access-sw01.yml`.

{{< hint info >}}
**DNS:** New 10.20.x.x addresses will not resolve via DNS until post-migration ([Step 11](#step-11-management-cutover) / [Post-Migration](../post-migration/)). This is expected — Ansible uses inventory IPs directly. Use IP addresses for any manual verification during this step.
{{< /hint >}}

{{< hint warning >}}
**Wireless clients:** AP SSID-to-VLAN mappings are not reconfigured in this step. When the AP's port moves to its target VLAN, wireless clients may lose connectivity. SSID configuration is handled in [Step 13](#step-13-ap-ssid-configuration) after Omada adoption ([Step 12](#step-12-omada-device-adoption)).
{{< /hint >}}

**Run:**
```bash
make migration-switch-access-ports
```

**Verify:**
1. `show vlan brief` — each port in correct VLAN
2. Each device gets correct VLAN IP via DHCP or static
3. Spot-check: SSH to a management host, ping across VLANs (where firewall permits)

**Rollback:**
Move ports back to VLAN 1 (SG2218 General mode):
```
configure
interface gigabitEthernet 1/0/3
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/14
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/15
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
interface gigabitEthernet 1/0/16
  switchport general allowed vlan 1 untagged
  switchport pvid 1
exit
end
copy running-config startup-config
```

---

## Step 11: Management Cutover

After all ports are migrated and verified:

1. **Clean up VLAN 1 from migrated ports** — remove stale VLAN 1 membership from all ports that have been moved to new VLANs. On the SG2218, adding a new VLAN does not automatically remove VLAN 1. SSH to the switch and run:
   ```
   configure
   interface gigabitEthernet 1/0/3
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/4
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/14
   no switchport general allowed vlan 1
   exit
   interface gigabitEthernet 1/0/15
   no switchport general allowed vlan 1
   exit
   end
   copy running-config startup-config
   ```

2. **Switch management VLAN** — remove the old VLAN 1 management interface. The switch already has a VLAN 99 management IP (`10.20.99.10`) from [Step 5b](../builder-cutover/#5b--add-vlan-99-management-ip-to-the-switch).
   ```
   configure
   no interface vlan 1
   end
   copy running-config startup-config
   ```

3. **Promote inventory** — `dvntm-new` becomes the active `dvntm`. Use `git mv` to preserve file history:
   ```bash
   cd ansible-inventory-deevnet
   git mv dvntm dvntm-old
   git mv dvntm-new dvntm
   git commit -m "Promote dvntm-new to dvntm for management cutover"
   ```
   No `ansible.cfg` changes needed — it already points to `dvntm`.

4. **Verify Ansible connectivity** from each collection that uses the inventory:
   ```bash
   cd ansible-collection-deevnet.net
   # Switch (SSH/CLI)
   ansible switches -m ansible.netcommon.cli_command -a "command='show image-info'"
   # OPNsense (API only — SSH is not available for a_autoprov)
   ansible dns_servers -m uri -a "url='https://10.20.99.1/api/core/firmware/status' \
     url_username='{{ opnsense_api_key }}' url_password='{{ opnsense_api_secret }}' \
     force_basic_auth=true validate_certs=false"
   ```

5. **Clean up** — once stable, remove the old inventory:
   ```bash
   cd ansible-inventory-deevnet
   git rm -rf dvntm-old
   git commit -m "Remove pre-migration inventory (dvntm-old)"
   ```

---

## Step 12: Omada Device Adoption

After management cutover, adopt the switch and AP into the Omada SDN controller. Treat this as a fresh Omada install — devices are on new IPs/VLANs and need to be discovered and adopted.

**Prerequisites:**
- Step 11 complete (switch on VLAN 99 management IP, inventory promoted)
- Builder reachable at `10.20.99.95`

**Run:**
1. Access the Omada controller at `https://10.20.99.95:8043`
2. Complete the initial setup wizard (fresh install)
3. Adopt `access-sw01` — it should appear as pending on VLAN 99 (management) at `10.20.99.10`
4. Adopt `ap01` — it should appear as pending on its assigned VLAN
5. If devices don't auto-discover, use manual adoption by IP

**Verify:**
1. Both devices show as "Connected" in the Omada dashboard
2. Switch and AP firmware/model info visible in Omada

**Rollback:**
Omada adoption is non-disruptive — devices continue to function without Omada management. Remove a device from Omada if needed and re-adopt later.

---

## Step 13: AP SSID Configuration

Configure SSID-to-VLAN mappings for wireless networks.

{{< hint warning >}}
**AP Firmware Limitation:** Omada 6.1 cannot push VLAN config to EAP650-Outdoor firmware 1.0.4 (2023). The SSIDs must be configured via the **AP's standalone web UI** until the firmware is updated. After firmware update, Omada provisioning should work and this step can use `make migration-omada-ssids`.
{{< /hint >}}

**SSIDs to configure:**

| SSID | VLAN | Security | Purpose |
|------|------|----------|---------|
| DVNTM | 10 | WPA-Personal | Trusted |
| DVNTM-IOT | 30 | WPA-Personal | IoT devices |
| DVNTM-IOTV | 31 | WPA-Personal | IoT vendor devices |
| DVNTM-GUEST | 40 | WPA-Personal | Guest |

WiFi passwords are in `group_vars/all/vault.yml` under `deevnet_wifi_psk`.

**Via AP standalone web UI:**
1. Access AP web UI: `ssh -L 8080:<ap-ip>:80 a_autoprov@<builder-transit-ip>`, then `http://localhost:8080` (admin/admin or site device password)
2. Go to **Wireless → SSID** settings
3. Create each SSID with WPA-Personal, set the password, enable VLAN tagging with the correct VLAN ID
4. Set the AP's management IP to static `10.20.99.9/24`, gateway `10.20.99.1`

**Via Omada (after AP firmware update):**
```bash
make migration-omada-ssids
```

**Verify:**
1. Connect to each SSID and confirm correct VLAN IP:
   - DVNTM → `10.20.10.x`
   - DVNTM-IOT → `10.20.30.x`
   - DVNTM-IOTV → `10.20.31.x`
   - DVNTM-GUEST → `10.20.40.x`
2. Internet access works from each SSID

**Rollback:**
Factory reset the AP and reconfigure SSIDs.
