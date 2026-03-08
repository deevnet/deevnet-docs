---
title: "Future Evaluations"
weight: 4
---

# Future Evaluations

Technologies being considered for future adoption. These evaluations are informational—none are blocking the current MVP dvntm platform.

---

## VyOS Evaluation {{< status-badge "on-hold" "On Hold" >}}

OPNsense has served well for production routing. The lack of automated installation (no PXE) is **not a show-stopper** for the MVP—a fresh OPNsense install is treated as a manual prerequisite to the building/recovery plan, alongside factory-resetting the access switch and AP.

### Original Motivation

| Requirement | OPNsense | VyOS |
|-------------|----------|------|
| Automated install | No PXE, manual USB only | cloud-init + staged ISO |
| Air-gap recovery | Manual reinstall | Staged ISO, automated |
| Config-as-code | API-based | Native CLI + Ansible |
| Day-2 automation | Good (Ansible) | Excellent (vyos.vyos) |
| WebUI | Yes | No (CLI-centric) |

### Why On Hold

- **OPNsense Day-2 automation is mature** — the `deevnet.net` Ansible collection handles DNS, DHCP, firewall, and WoL configuration
- **Manual install is an accepted MVP prerequisite** — same category as factory-resetting the switch and AP before the automated build begins
- **WebUI remains valuable** for visual firewall auditing and one-off diagnostics
- **VyOS rolling release risk** — LTS requires subscription; rolling is less predictable for a core network device
- **No pressing need** — the current OPNsense deployment is stable and well-automated for Day-2 operations

### Conditions to Revisit

- OPNsense automation becomes insufficient for a new requirement
- VyOS LTS becomes freely available
- A use case arises where CLI-only management is a clear advantage

---

## N100 Router Hardware Evaluation

A future hardware evaluation. The current core routers (ZimaBoard 832 for dvntm, ODYSSEY X86J4125864 for dvnt) are general-purpose SBCs repurposed as routers. Purpose-built Intel N100 router appliances offer better performance, more Ethernet ports, and a form factor designed for the role.

### Why N100 Router Appliances?

| Attribute | Current (Zima / Odyssey) | N100 Appliance |
|-----------|--------------------------|----------------|
| **CPU** | Celeron N3450 / J4125 | Intel N100 (4C, 3.4GHz boost) |
| **Ethernet** | 2x 1GbE | 4x 2.5GbE (typical) |
| **TDP** | 6-12W | 6W |
| **Cooling** | Passive / Active fan | Fanless (typical) |
| **NVMe** | Via M.2 (Odyssey only) | Built-in M.2 slot |
| **Form factor** | SBC (not router-specific) | Mini PC / firewall appliance |
| **Purpose** | General-purpose | Built for routing/firewall |

### Provisioning Model Change

The N100 hardware evaluation also introduces a future shift in the provisioning approach for the core router:

| Aspect | Current Model | Future Model |
|--------|---------------|--------------|
| **Install method** | Manual USB install | Pre-imaged NVMe drive |
| **Storage** | eMMC (soldered) | Removable NVMe M.2 |
| **Recovery** | Reinstall from USB | Swap in pre-imaged NVMe |
| **Imaging** | Manual | Scripted image-to-NVMe (on build host) |

**Pre-imaged NVMe** means the OPNsense installation is written to an NVMe drive on a build host, then physically installed in the router appliance. This approach:

- Eliminates the need for PXE or USB boot during provisioning
- Enables offline preparation of recovery drives
- Aligns with air-gap recovery requirements (spare NVMe kept ready)
- Fits the image factory model already used for other substrate hosts

This provisioning model is part of the N100 evaluation, not the current MVP approach.

### Evaluation Criteria

| Criterion | Requirement |
|-----------|-------------|
| **CPU** | Intel N100 or equivalent |
| **Ethernet** | Minimum 4x 2.5GbE (Intel NICs preferred over Realtek) |
| **NVMe** | M.2 slot for removable NVMe storage |
| **Cooling** | Fanless preferred |
| **RAM** | Minimum 8GB |
| **OPNsense compatibility** | Verified FreeBSD driver support |

### Evaluation Status

| Phase | Status |
|-------|--------|
| Requirements definition | Complete |
| Hardware research | Pending |
| OPNsense NVMe imaging workflow | Pending |
| Procurement | Pending |
| Validation (dvntm first) | Pending |
| Production cutover (dvnt) | Pending |
