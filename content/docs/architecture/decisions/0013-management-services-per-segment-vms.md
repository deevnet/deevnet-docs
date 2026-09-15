---
title: "ADR-0013: Management-Hypervisor Services Run as Containers on Per-Segment VMs"
weight: 13
---

# ADR-0013: Management-Hypervisor Services Run as Containers on Per-Segment VMs

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-14 |
| **Scope** | How services on the management hypervisor are grouped into VMs, where the site's Omada controller officially runs, and the order a rebuild uses them in |
| **Extends** | [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/), which decided that the controller is the actuator for switch and AP configuration, but not where it runs |
| **Related** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0008: Host Naming and Site Codes](/docs/architecture/decisions/0008-host-naming-site-codes/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) (its Open questions 2, 5 and 6), [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) |

---

## Context

### One VM per function is where things were heading

The management hypervisor, `dv02hyp001p01`, runs one VM per service today:

| VM | Service | Segment |
|---|---|---|
| `dv02tdn001v01` | tenant DNS (PowerDNS) | management |
| `dv02tst001v01` | tenant state store | management |
| `dv02mqt001v01` | MQTT broker | IoT Backend |

ADR-0012 adds more:
- the Deevnet API and its database
- a broker auth database

The site's Omada controller also needs a permanent home.

**Continuing one VM per function would mean five or more VMs, each with its own OS to patch.** The
hypervisor's platform page says its *"**32GB RAM** meets management hypervisor requirements for
multiple VMs"*, and sketches management VMs as groups for observability and automation, not one per
container ([Management Hypervisor](/docs/platforms/management-plane/management-hypervisor/)).

### What limits how services can be grouped

- **A VM sits on specific segments.** A VM with an interface on two segments carries traffic between
  them without passing the core router, which bypasses the zone policy that
  [Network Segmentation](/docs/standards/network-segmentation/) relies on. So a grouping that stays
  honest to the zones puts no VM on two segments.
- **Tenant-facing services can't sit on management.** The standard says *"Tenant networks MUST NOT
  have direct access to the management segment"* (§4). Today's tenant DNS and state store break
  this, and tenants reach them only because the core router currently passes everything
  ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)).
- **ADR-0004 already drew the split, and accepted sharing within it:**
  - *"PowerDNS shares a host with future tenant-facing services. An OS update or a container restart
    on that host takes tenant DNS with it. Accepted at lab scale"*
  - *"Substrate-facing management services are deliberately kept off this host, on a separate one,
    because their change cadence is much higher."*
- **The services are already containers.** The Builder's controller is a podman container, built by
  the builder collection's `omada_controller` role from the `mbentley/omada-controller` image at
  6.3.0.45, with its data under `/opt/omada-controller`.

### Where the Omada controller runs today, and why that has to change

- **It runs on the Builder, `dv00bld001p01`**, the only host in the inventory's `network_controllers`
  group. It was wiped to a fresh install on 2026-09-11, and no device is adopted into it (CHG-0005
  baseline).
- **The Builder belongs to no site.** ADR-0008 gives it site code `00`: *"No site — the roaming
  builder appliance"*. A site's device controller is part of that site's steady state.
- **The pre-VLAN substrate is built without a controller.** The switch is configured standalone by
  `switch_vlans`, which ADR-0009 §4 keeps as the tool for any switch not yet adopted. A controller is
  needed only once devices are adopted and provisioned (ADR-0009 §6).
- **Its database is derived state.** ADR-0009: *"whatever it holds can be rebuilt from inventory by
  re-running the automation."* A new controller is a fresh install that inventory provisions, not a
  migration.
- **Adoption needs the device and the controller on the same subnet.** ADR-0009's evidence:
  *"Adoption needs the switch and the controller in the same subnet … and the same VLAN"*. Devices
  manage on VLAN 99, the management segment.

---

## Options considered

### A — One VM per function

Today's pattern, extended to the controller, the API and the broker's auth database.

- **Pros:** each service can be rebuilt, patched and moved alone.
- **Cons:** a VM, an OS and a patch cycle per container, on a 32 GB host. ADR-0004 had already
  accepted sharing a host within one audience.
- **Verdict:** Rejected.

### B — One services VM per segment, each function a container

- **Pros:**
  - No VM bridges two segments, so the zone policy keeps its meaning.
  - It follows ADR-0004's split: substrate-facing services on management, tenant-facing services
    on Platform, each on a separate host.
  - The number of VMs grows with segments, not services.
- **Cons:**
  - Containers on one VM share its fate: a reboot of the VM takes all of them.
  - A function has to be moved by container, not by VM.
- **Verdict: Chosen.**

### C — Group by function family, regardless of segment

- **Cons:** a family such as "data stores" spans segments (the API's database is on Platform, the
  broker's auth database is on IoT Backend), so its VM would need an interface on each.
- **Verdict:** Rejected.

### D — One general management VM on every segment it serves

- **Pros:** the fewest VMs.
- **Cons:** it bridges management, Platform and IoT Backend inside one VM, bypassing the core
  router's zone policy entirely.
- **Verdict:** Rejected.

### Also rejected: the controller stays on the Builder

It works today and the Builder is present at every rebuild. But it ties the site's steady state to
an appliance ADR-0008 defines as belonging to no site, and the Builder would have to stay attached
for the site's wireless to be managed at all.

---

## Decision

**Option B**, with the Omada controller's official home in the management services VM.

### 1. One services VM per segment

| Services VM, on `dv02hyp001p01` | Segment | Containers | Serves |
|---|---|---|---|
| **Management services** | management (VLAN 99) | the Omada controller; later management services such as observability and automation | the substrate |
| **Platform services** | Platform (VLAN 25) | the Deevnet API and its database (ADR-0012); tenant DNS and the tenant state store, folded in later (§5) | tenants |
| **IoT Backend services** | IoT Backend (VLAN 35) | the VerneMQ broker and its auth database (ADR-0012) | devices |

- **A VM never has an interface on more than one segment.** Anything that needs to cross segments
  goes through the core router and its zone policy.
- **Every VM is created the way the hypervisor's page prescribes:** *"Management VMs are created
  using **Ansible only**"*, with a MAC derived from its VMID.

### 2. Each function stays separable

- **Every function is its own container**, with its own data directory.
- **Every function keeps its own inventory group**, as the tenant DNS, tenant state and MQTT broker
  already do. Moving a function to another VM changes which host is in its group. It isn't a
  rebuild.
- **Grouping is by segment, not convenience.** A new service joins the services VM of the segment it
  must sit on. If that would put a substrate-facing service with tenant-facing ones, it takes the
  segment's placement anyway, and the conflict is recorded.

### 3. The Omada controller is a container in the management services VM

- **It sits on the management segment (VLAN 99)**, the subnet and VLAN that ADR-0009 requires for
  adoption.
- **Its host is the management services VM in `network_controllers`.** Playbooks such as
  `omada-wireless.yml` and the Open API client talk to it, not to the Builder.

### 4. A rebuild uses the management services VM's controller

1. **Build the pre-VLAN substrate with no controller:** the core router, and the access switch
   configured standalone by `switch_vlans`.
2. **Build the management hypervisor**, then the services VMs.
3. **Start the controller container**, and run the controller's manual floor on it (ADR-0009 §5):
   the setup wizard and Owner account, then the Open API client.
4. **Define the site from inventory, adopt, then provision** (ADR-0009 §6).

The Builder's controller is not a step in this order.

### 5. Tenant DNS and the tenant state store fold into the Platform services VM

- **The intent:** `dv02tdn001v01` and `dv02tst001v01` become containers in the Platform services VM.
- **What that fixes:** it also moves them off the management segment, where the standard says
  tenants must not reach.
- **When:** it's done by its own change record, not by this one.

### 6. CHG-0005 waits for the management services VM

The AP is adopted straight into the controller's official home, so it is adopted once. Adopting it
into the Builder's controller first would mean a second adoption later. That wasn't chosen
(operator decision, 2026-09-14).

### 7. How the Deevnet API reaches the controller

The API runs on Platform and the controller on management. A narrow `platform -> management` rule,
from the Platform services VM to the controller's Open API port only, is declared when the API is
built (ADR-0012 §7).

---

## Consequences

**Fewer VMs, and fewer operating systems to patch.** One VM per function would reach at least five
(the controller, the API, the broker, tenant DNS and tenant state). Grouped by segment, it's three.

**Containers in one VM share its fate.**
- **On Platform:** rebooting the Platform services VM takes tenant DNS and the API together. ADR-0004
  already accepted that for tenant DNS at lab scale.
- **On IoT Backend:** rebooting that VM takes the broker and its auth database together, which is
  the intended fate-sharing (ADR-0012 §7).
- **Separate VMs for separate audiences:** ADR-0004's reason for keeping substrate-facing services
  apart from tenant-facing ones, their different change cadence, is kept by the segment split.

**Moving the controller costs nothing today.** The Builder's controller has no adopted devices, and
its database is derived state. Only the manual floor is repeated: the Owner account and the Open API
client.

**CHG-0005 moves back** behind the management services VM, and so does the PPSK device test in
ADR-0011, which needs the AP adopted.

**The reset-device adoption window is expected to work the same way.**
- ADR-0009 §5 relies on the Builder's bootstrap DHCP to give a factory-reset switch its address on
  the management subnet. A controller on that subnet, in a VM, doesn't change that.
- *This is inference, to confirm at the first adoption into the new controller.*
- If a device ever has to find the controller from another subnet, Omada documents DHCP Option 138:
  *"the DHCP Server will tell the EAPs where the EAP/Omada Controller is, so that the EAP/Omada
  Controller and EAPs can communicate with each other among different subnets"*
  ([Omada, DHCP Option 138](https://support.omadanetworks.com/us/document/12950/), updated
  08-12-2026). The page is written for EAPs; it doesn't state that switches work the same way.

**Descriptive pages change on acceptance, not before:**
- the management hypervisor's platform page
- the controller runbooks: [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/)
  and the upgrade procedure
- [Important URLs](/docs/runbook/network/important-urls/)
- the tenant networking page, which still describes shared services on the management segment

---

## Open questions

1. **What happens to the Builder's `omada_controller` role?** Retire it, or keep it as a recovery
   fallback for when the management hypervisor is down.
2. **What are the services VMs called?** The naming standard has no function code for a
   general-purpose services VM ([Naming](/docs/standards/naming/)). Codes have to be allocated,
   with VMIDs through the identity allocator. Whether `dv02mqt001v01` is renamed or replaced by the
   IoT Backend services VM follows from that.
3. **How is the new controller's Owner account registered?** The Builder's controller has a
   cloud-registered Owner (`registeredRoot: true`, CHG-0005 baseline). Whether the new one repeats
   that is a choice for its setup.

---

## Current state

- **Proposed.** Nothing is built.
- The controller still runs on the Builder, with no devices adopted.
- Tenant DNS, tenant state and the MQTT broker are still one VM each on `dv02hyp001p01`.
