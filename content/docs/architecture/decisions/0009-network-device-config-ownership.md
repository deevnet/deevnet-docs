---
title: "ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied"
weight: 9
---

# ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-09-10 |
| **Accepted** | 2026-09-10 |
| **Scope** | Who owns, and who applies, the configuration of controller-managed network devices — the access switch and the AP — and how automation talks to the Omada controller |
| **Related** | [CHG-0004](/docs/changes/2026/0004-omada-controller-and-network-firmware/) — brings the controller and firmware current, so the devices can be adopted; [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) — the guards any reconciling role now carries |

---

## Context

The mobile site's network devices are configured three different ways today:

- **The access switch** is configured by the `switch_vlans` role over its CLI, from inventory:
  `deevnet_vlans` declares the VLANs, and `switch_ports` in `host_vars/dv02acc001p01.yml` declares
  every trunk, native VLAN and access port.
- **The AP's SSIDs** were configured by hand in its own web UI, because the controller could not
  push VLAN-tagged SSIDs to its 2023 firmware
  ([CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/)).
- **The Omada controller** holds hand-grown, partial state: six networks created by a migration
  playbook in March, and nothing else. It has never adopted the switch.

[CHG-0004](/docs/changes/2026/0004-omada-controller-and-network-firmware/) brings the controller
and both devices' firmware current, so that Omada can manage them. That raises the question this
record settles. Adopting a device hands its configuration to the controller, so something has to
own that configuration: inventory, or the controller.

Two things make the question pressing rather than academic.

- **Adoption is not neutral.** On adoption the controller applies its own port profile. The
  built-in `All` profile is native VLAN 1 with every other network tagged. Adopted as it stands, the
  live switch would move the builder's port and the uplink onto VLAN 1, and the builder runs the
  controller, so the controller would cut its own path mid-adoption. That is the failure shape of
  [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/): the automation host behind
  the thing it is changing.
- **`switch_vlans` is the weakest role in the estate.** It drives the CLI through `cli_command`,
  which reports every run as changed, and its `--check` fails on every configuration line. It
  cannot say what a run is about to do.

---

## Options considered

### A — The controller owns the configuration

Configure the site in the controller's UI, and let its database be the record.

Rejected. The controller's database would become the only copy of the network's configuration. It
is also one-way across upgrades — a newer controller's database cannot be opened by an older one —
so losing it, or falling back a version, loses configuration
([Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/)). That runs
against the substrate's premise that everything is declared in git and rebuilt from it.

### B — Inventory owns it, applied over the CLI; the controller only watches

Keep `switch_vlans`, and do not adopt the switch.

Rejected. It leaves the weakest role as the switch's only mechanism, and it leaves the AP on
hand-set SSIDs, because the controller is what provisions an adopted AP. A switch cannot be both
controller-managed and configured over its CLI: a CLI change to a managed switch is overwritten
at the controller's next provision.

### C — Inventory owns it; the controller applies it

Inventory stays the only declaration. Automation turns it into controller objects through the
controller's API, and the controller pushes them to the devices.

**Chosen.**

---

## Decision

### 1. Inventory is the only source of network device configuration

`deevnet_vlans`, `switch_ports` and the SSID definitions stay as they are. The controller's
database is **derived state**: whatever it holds can be rebuilt from inventory by re-running the
automation.

### 2. The controller is the actuator

Automation applies inventory through the controller's API. The controller then provisions the
devices. Nobody configures a managed device in the controller's UI, or on the device.

### 3. The documented Open API first; undocumented calls only as a marked fallback

- **"Documented" means the spec the running controller publishes** at `/v3/api-docs` — 1,856
  paths on 6.3.0.45. That spec, not a vendor web page, is what automation checks itself against.
- **An undocumented `/api/v2` call is allowed only where the documented API cannot do the job.**
- **Every call site is marked**, in one greppable form:

  ```
  # omada-api: documented <operationId> spec <controller version>
  # omada-api: UNDOCUMENTED <path> tested-on <controller version>
  ```

- **On a controller upgrade**, `grep -rn "omada-api: UNDOCUMENTED"` lists what to re-test by hand.
  Automation also checks, before it writes, that every documented endpoint it uses is present in
  the running controller's spec, and refuses to run if one has gone.

### 4. `switch_vlans` is break-glass for an adopted switch

A switch declares `switch_management: omada` in `host_vars` when it is adopted. From then on,
`switch_vlans` refuses to run against it. The only way past that is a per-run
`-e switch_vlans_break_glass=true`, and it is for one situation only: the controller cannot be
used, and the switch has first been returned to standalone (forgotten, or factory reset). The run
announces itself as break-glass. Adopting the switch again afterwards puts it back under the
controller, which re-applies the same inventory.

A switch that has not been adopted is standalone, and `switch_vlans` remains its tool.

### 5. The manual floor is short, and written down

What must exist before automation can do anything:

| Item | Why it is manual |
|---|---|
| The controller's setup wizard, and the Owner account in the vault | Nothing exists to automate against yet |
| **One Open API client**, created by the Owner, with its id and secret in the vault | Creating one needs a global role; the automation account is deliberately site-scoped |
| The automation account (`a_autoprov`) | Already created by a playbook, from the Owner |
| A device at factory defaults, cabled, in the controller's subnet | A reset switch asks for DHCP on VLAN 1, and falls back to `192.168.0.1` without an answer. On this site only the builder's **bootstrap** DHCP answers it, with the switch's own reservation (`10.20.99.10`). So the rebuild window runs in bootstrap-authoritative mode, or the address is set by hand at `192.168.0.1`. See Evidence. |
| *(Not a floor item)* device credentials | A reset device returns to `admin`/`admin` and adopts with them. The controller then applies its site Device Account. See Evidence. |

### 6. Define the site first, then adopt, then provision

1. Create the site-level objects through the API: networks from `deevnet_vlans`, and one port
   profile per distinct port shape in `switch_ports`.
2. Adopt the device.
3. Assign each port its profile, and set the device's name and management VLAN and IP.
4. Verify reachability.

For a switch already in service, adoption is done **as a planned rebuild**: factory reset, adopt,
provision from inventory. The [console-recovery procedure](/docs/runbook/recovery/console-recovery/access-switch/)
already treats a reset as legitimate, because everything worth keeping is in inventory. A new
site, a recovery and an adoption then follow the same path.

### 7. The API role carries INC-0001's guards from the start

- Refuse to reconcile from an empty or partial desired set.
- Deletion of objects inventory does not declare is off by default, and reported rather than
  done.
- The ports carrying the controller's own path — the uplink and the builder's port — and the
  management VLAN are protected from change.
- Reachability is checked after every apply.

---

## Consequences

**What this buys:**

- **A lost controller is an inconvenience, not a data loss.** Reinstall it and re-run the
  automation. The snapshot-and-fallback care CHG-0004 needed matters much less once nothing lives
  only in the controller.
- **One mechanism for the switch and the AP**, SSIDs included, that can report what it will
  change, instead of a CLI role that always says "changed".
- **Version bumps become checkable:** diff the published spec, and sweep the markers.
- **The translation forces good declarations.** An Omada profile *requires* STP, LLDP-MED and
  loop detection, so each becomes a stated choice rather than a firmware default that can move
  underneath the configuration.

**What it costs:**

- **Changes need the controller.** While it is down, adopted devices keep forwarding but cannot be
  changed, except by break-glass, which means taking the switch back to standalone.
- **The manual floor grows** by one Open API client, and the adoption window has to run with the
  builder bootstrap-authoritative, or with the switch's address set by hand.
- **The first run has to reconcile, not assume an empty controller**, because six networks from
  March are already there, named by a different convention.
- **Two schema rules need encoding.** An Omada profile cannot list its native VLAN as tagged,
  though inventory lists it in both places, so the role subtracts it.
- **`switch_vlans`, and the runbook steps that call it**, become break-glass for adopted
  switches. The runbook pages change when a switch is actually adopted.

---

## Evidence

Gathered on 2026-09-10 against controller 6.3.0.45. The discovery calls were read-only; nothing
was written to the controller.

| Question | Finding |
|---|---|
| Does the documented API cover what `switch_vlans` does? | Yes. It has `lan-networks` and `lan-profiles` (create, modify, delete); per-port `profile`, `profile-override` and `name`; switch `general-config`; and `switches/{mac}/networks` for the management VLAN and IP. Adoption is covered by `start-adopt`, `batch-adopt` and `forget`. |
| Can automation authenticate? | The client-credentials token endpoint exists, and rejects an unknown client cleanly (`-44106`). Creating a client is gated on a global role (`globalSetting`), so it is a manual Owner step. |
| What does the controller already hold? | Networks on VLANs 1, 10, 30, 31, 40 and 99. The built-in `All` profile is native VLAN 1, with those networks tagged. |
| Does inventory translate cleanly? | Yes. The proof of concept (`ansible-collection-deevnet.net`, `playbooks/poc/omada-openapi-poc.yml`) in plan mode found all 8 endpoints it uses in the running spec. The network body from `deevnet_vlans` carries all 3 required fields, and the profile body from `switch_ports` all 9. |
| Has a write been tested? | Not yet. The PoC's apply mode — create, read back, compare, delete — waits for the Open API client. |
| What address does a reset switch take? | A DHCP lease if one is offered, otherwise `192.168.0.1` ([SG2218 installation guide](https://static.tp-link.com/upload/manual/2023/202305/20230511/7106510303_TL-SG2218(UN)_IG.pdf) §4.2). Adoption needs the switch and the controller in the same subnet (§4.3) — and the same VLAN ([adoption guide](https://support.omadanetworks.com/us/document/122955)). |
| Who would answer that DHCP request here? | After a reset, every port is untagged VLAN 1, so the request reaches the builder and OPNsense's untagged `lan`. **OPNsense does not answer**: Kea listens on `lan`, but `lan` still carries the pre-migration `192.168.10.1/23` and Kea has no subnet for it. **The builder answers only in bootstrap-authoritative mode**, where its dnsmasq holds the switch's reservation (`5c:62:8b:0c:40:ec` → `10.20.99.10`, from inventory). |
| What credentials does adoption need? | The defaults. TP-Link's adoption guide (updated 2026-09-10) and forgot-password guide (updated 2026-08-24) both give `admin`/`admin` for switches after a reset, and the controller's site Device Account (`admin` here) takes over on adoption. Switch firmware 1.20.17's note — *"remove default username and password"* — most likely means a forced change at first login, which the installation guide already mentions *"for certain devices"*. It is confirmed on the device itself after CHG-0004 phase 2. |
