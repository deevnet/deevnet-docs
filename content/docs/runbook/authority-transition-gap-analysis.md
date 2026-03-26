---
title: "Authority Transition Gap Analysis"
weight: 3
---

# Authority Transition Gap Analysis

Analysis of gaps between the [authority transition runbook](/docs/runbook/authority-transition/) and the actual state of automation, performed 2026-03-26 against the segmented 10-space (10.20.x.x with per-VLAN subnets).

**Scope:** `bootstrap-authoritative.yml`, `core-authoritative.yml`, the `bootstrap` role, inventory group_vars, dnsmasq templates, and the OPNsense DNS/DHCP roles in `deevnet.net`.

---

## Critical Gaps

### GAP 1: `bootstrap-authoritative.yml` doesn't enable DHCP

**Runbook says:** `make bootstrap-auth` enables DNS/DHCP/gateway on the builder.

**Reality:** The playbook calls `include_role: bootstrap` without overriding `bootstrap_tftp_backend` or `bootstrap_dnsmasq_dhcp_enabled`. Inventory has both set to their production values (`tftpd` / `false`), so running the playbook installs standalone tftpd with DHCP off.

The playbook enables IP forwarding and masquerading but never actually starts dnsmasq or enables DHCP. The procedure is non-functional.

**Fix:** The playbook needs to pass `bootstrap_tftp_backend: dnsmasq`, `bootstrap_dnsmasq_dhcp_enabled: true`, and `bootstrap_dnsmasq_service_enabled: true` as vars to the role include.

### GAP 2: No IP reconfiguration during transition — RESOLVED

**Runbook says:** "Reconfigure builder IP — Move the builder from the gateway IP to its reserved IP" (promote) and the reverse for revert.

**Fix (2026-03-26):** Both playbooks now swap the management interface IP as the final step using NetworkManager (`nmcli`). The swap uses `async`/`poll: 0` (fire-and-forget) because changing the IP drops the SSH connection. All configuration work completes first while connectivity is stable. The playbooks also handle the default gateway: removed in bootstrap mode (builder IS the gateway), restored in production mode (core router is the gateway). An idempotency check skips the swap if the target IP is already configured.

### GAP 3: No DNS host records in bootstrap dnsmasq — RESOLVED

**Runbook/architecture says:** In bootstrap mode, the builder holds all `dvntm.deevnet.net` DNS records locally.

**Fix (2026-03-26):** Added `gather_hosts.yml` task to the bootstrap role that builds DNS A records and CNAME records from inventory (same data patterns as the `opnsense_dns` role). The `dnsmasq.conf.j2` template now renders `address=` lines for host records and `cname=` lines for aliases. All hosts with `host_a_record: true` are included regardless of segment.

---

## High-Severity Gaps

### GAP 4: DHCP gateway points to reserved IP

**Runbook says:** In bootstrap mode, the builder IS the gateway.

**Inventory has:** `bootstrap_dhcp_gateway: "10.20.99.95"` — the reserved (production) IP. Should be `10.20.99.1` in bootstrap mode.

DHCP clients would receive the wrong gateway. This is related to Gap 2 (the IP never changes), but even if the IP were swapped, this variable would need to change too.

### GAP 5: No DHCP static reservations in dnsmasq — RESOLVED

**Runbook says:** Builder carries DHCP configuration with static reservations for every host MAC.

**Fix (2026-03-26):** The `gather_hosts.yml` task also builds DHCP static reservations from inventory, filtered to management segment hosts with `dhcp_reservation: true` (same data patterns as the `opnsense_dhcp` role). The `dnsmasq.conf.j2` template now renders `dhcp-host=` entries for each reservation.

---

## Medium-Severity Gaps

### GAP 6: Single-VLAN bootstrap vs. multi-VLAN 10-space — RESOLVED

The segmented model has 9+ VLANs. The bootstrap playbook assumes a single flat management segment — dnsmasq serves DHCP on one interface for one subnet.

**Decision (2026-03-26):** Bootstrap mode is management-VLAN-only (10.20.99.0/24). The builder provides DNS/DHCP/gateway for the management segment only — enough to PXE-boot the core router and any management-plane hosts. Once OPNsense is online, it takes authority for all VLANs. Other segments (trusted, storage, IoT, etc.) are created by the OPNsense and switch playbooks after the core router exists.

This keeps dnsmasq simple (one interface, one subnet) and avoids replicating VLAN trunking and multi-scope DHCP on the builder. The switch and OPNsense VLAN configuration remain manual/semi-automated steps in the build sequence.

### GAP 7: No OPNsense disable automation (revert direction) — RESOLVED

**Runbook says:** "Disable production DNS/DHCP on router (if it is still operational)"

**Fix (2026-03-26):** Added `disable-opnsense-services.yml` and `enable-opnsense-services.yml` playbooks to the `deevnet.net` collection. These use the OPNsense API (`kea/service/stop`, `unbound/service/stop` and their start counterparts) to stop/start DNS and DHCP services. The authority transition runbook now documents running `disable-opnsense-services.yml` before `make bootstrap-auth` as a separate step (since it requires vault credentials and targets a different collection).

### GAP 8: Hardcoded WAN interface

Both playbooks hardcode `bootstrap_wan_interface: wifi`. The dvnt provisioner (AOOSTAR N1 PRO) has dual Ethernet and no WiFi. This should come from inventory.

---

## Low-Severity Gaps

### GAP 9: No validation steps automated — RESOLVED

The runbook specifies validation checkpoints at each step.

**Fix (2026-03-26):** Both playbooks now include validation tasks before the IP swap:
- `bootstrap-authoritative.yml`: verifies dnsmasq is running and TFTP port 69 is listening. Fails before IP swap if dnsmasq didn't start.
- `core-authoritative.yml`: warns if dnsmasq is still running, verifies TFTP port 69 is listening.
- Post-swap validation remains manual (operator reconnects at new IP and runs verification commands documented in the runbook).

### GAP 10: No transition logging — RESOLVED

The runbook says "Record transition with timestamp and operator."

**Fix (2026-03-26):** Both playbooks append a timestamped entry to `/var/log/authority-transitions.log` with the transition direction, operator (`$USER`), and hostname.

---

## Severity Summary

| Gap | Summary | Severity |
|-----|---------|----------|
| 1 | ~~`bootstrap-auth` doesn't enable DHCP — procedure non-functional~~ | ~~Critical~~ RESOLVED |
| 2 | ~~No IP reconfiguration (gateway vs reserved)~~ | ~~Critical~~ RESOLVED |
| 3 | ~~No DNS host records in dnsmasq template~~ | ~~Critical~~ RESOLVED |
| 4 | ~~DHCP gateway variable points to wrong IP~~ | ~~High~~ RESOLVED |
| 5 | ~~No static DHCP reservations from inventory~~ | ~~High~~ RESOLVED |
| 6 | ~~Single-VLAN bootstrap vs multi-VLAN architecture~~ | ~~Medium~~ RESOLVED |
| 7 | ~~No OPNsense disable automation for revert~~ | ~~Medium~~ RESOLVED |
| 8 | ~~Hardcoded `wifi` WAN interface~~ | ~~Medium~~ RESOLVED |
| 9 | ~~No validation steps in playbooks~~ | ~~Low~~ RESOLVED |
| 10 | ~~No transition logging~~ | ~~Low~~ RESOLVED |

---

## Architectural Decisions (2026-03-26)

### Multi-site provisioner model

The physical provisioner (provisioner-ph01) acts as an appliance — it plugs into one site's management VLAN at a time. No dual-homing, no simultaneous multi-site. Switching sites means unplugging from one and plugging into the other.

**Key requirement:** Zero config changes between sites. The same playbooks and role code work for both dvntm and dvnt. All site-specific values (management IP, DHCP range, gateway, DNS domain, artifact server URLs, host records) come from inventory. The site switch is just which inventory directory is selected (`-i ../ansible-inventory-deevnet/dvntm/` vs `/dvnt/`).

This means:
- Each site inventory needs a complete `group_vars/bootstrap_nodes.yml` with site-appropriate values
- The bootstrap role and dnsmasq template must be fully parameterized — no hardcoded site assumptions
- The provisioner's IP per site is defined in that site's inventory host_vars

### DNS domain: drop mgmt.deevnet.net

The `mgmt.deevnet.net` subdomain adds a layer of indirection that doesn't buy much when the builder operates on one site at a time. Use site-scoped domains only:
- dvntm site: `dvntm.deevnet.net` (e.g., `artifacts.dvntm.deevnet.net`)
- dvnt site: `dvnt.deevnet.net` (e.g., `artifacts.dvnt.deevnet.net`)

During bootstrap, the builder's dnsmasq serves records in the site zone. In production, OPNsense is authoritative for the same zone.

**Impact:** The architecture docs (`core-services.md`, `builder.md`) reference `mgmt.deevnet.net` extensively. The multi-homing naming convention (`provisioner-01-dvnt.mgmt.deevnet.net`) also uses it. These docs will need updating, but that can be a separate pass.

---

## Suggested Chunking

**Chunk A — Make bootstrap-auth functional (Gaps 1, 4, 8):**
Fix the playbook vars overrides and inventory so `make bootstrap-auth` actually enters bootstrap mode. Low risk, high value.

**Chunk B — DNS and DHCP content (Gaps 3, 5):**
Extend `dnsmasq.conf.j2` to render host records and static DHCP reservations from inventory. Requires template work and possibly a gather-hosts task similar to the OPNsense DHCP role.

**Chunk C — IP reconfiguration (Gap 2):**
Automate the interface IP swap. Riskiest chunk — modifying the IP of the host you're running Ansible on can break the connection.

**Chunk D — Architectural decision (Gap 6):**
Decide the multi-VLAN bootstrap scope. This is a design discussion, not a code change, but it affects Chunks B and C.

**Chunk E — Polish (Gaps 7, 9, 10):**
OPNsense disable automation, validation steps, transition logging. Nice-to-haves.
