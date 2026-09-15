---
title: "ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs"
weight: 13
---

# ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-14 |
| **Scope** | How services on the management hypervisor are grouped into VMs and named, where the site's Omada controller officially runs, and the order a rebuild uses them in |
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

The site's Omada controller also needs a permanent home, and logging and observability are coming.

**Continuing one VM per function would mean a VM and an OS to patch for every container.** The
hypervisor's platform page says its *"**32GB RAM** meets management hypervisor requirements for
multiple VMs"*, and sketches management VMs as groups for observability and automation, not one per
container ([Management Hypervisor](/docs/platforms/management-plane/management-hypervisor/)).

### What limits how services can be grouped

- **A VM sits on specific segments.** A VM with an interface on two segments carries traffic between
  them without passing the core router, which bypasses the zone policy that
  [Network Segmentation](/docs/standards/network-segmentation/) relies on. Any grouping that stays
  honest to the zones puts no VM on two segments.
- **Tenant-facing services can't sit on management.** The standard says *"Tenant networks MUST NOT
  have direct access to the management segment"* (§4). Today's tenant DNS and state store break
  this, and tenants reach them only because the core router currently passes everything
  ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)).
- **Some segments can't reach management at all.** *"IoT backend segment MUST NOT access management
  segment directly"* (§9). Platform, by contrast, *"MUST be reachable from management, trusted,
  tenant, and IoT backend segments"* (§5).
- **ADR-0004 already drew a split, and accepted sharing within it:**
  - *"PowerDNS shares a host with future tenant-facing services. An OS update or a container restart
    on that host takes tenant DNS with it. Accepted at lab scale"*
  - *"Substrate-facing management services are deliberately kept off this host, on a separate one,
    because their change cadence is much higher."*
- **The services are already containers.** The Builder's controller is a podman container, built by
  the builder collection's `omada_controller` role from the `mbentley/omada-controller` image at
  6.3.0.45, with its data under `/opt/omada-controller`.

### How hosts are named

The naming standard gives every host a three-letter role mnemonic
([Naming](/docs/standards/naming/) §3.4):
- Mnemonics are *"allocated deliberately"*.
- *"A new class MUST have its code added here in the same change that introduces the host."*

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

### B — One services VM per segment

The first draft of this record: a management services VM, a Platform services VM and an IoT Backend
services VM.

- **Pros:** no VM bridges two segments, and there are few VMs.
- **Cons:**
  - It groups by where a service sits, not by what it's for. Provisioning, identity and tenant
    observability would share one Platform VM only because they share a VLAN.
  - The VM's name says nothing about its purpose.
- **Verdict:** Superseded the same day by Option C.

### C — Domain VMs, each on exactly one segment

Group services by the domain they belong to, name each VM for its domain, and pin every VM to one
segment. If a domain needs a presence on two segments, it becomes two VMs.

- **Pros:**
  - A VM's name says what it's for, and related services share a VM.
  - No VM bridges two segments, so the zone policy keeps its meaning.
  - It keeps ADR-0004's split: substrate-facing and tenant-facing services never share a VM.
- **Cons:**
  - More VMs than one per segment, though far fewer than one per function.
  - Containers in one VM share its fate: a reboot takes all of them.
- **Verdict: Chosen.**

### D — Group by function family, regardless of segment

- **Cons:** a family such as "data stores" spans segments (the API's database is on Platform, the
  broker's auth database is on IoT Backend), so its VM would need an interface on each.
- **Verdict:** Rejected.

### E — One general management VM on every segment it serves

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

**Option C**, with the Omada controller's official home in the network management VM.

### 1. The domain VMs

All run on `dv02hyp001p01`. Host names are proposed (§4).

| Host | Domain | Segment | Containers | Serves |
|---|---|---|---|---|
| `dv02nms001v01` | **Network management** | management (VLAN 99) | the Omada controller; later network monitoring and config backup | the substrate |
| `dv02sob001v01` | **Substrate observability** | management (VLAN 99) | substrate logs and metrics | the substrate |
| `dv02prv001v01` | **Provisioning** | Platform (VLAN 25) | the Deevnet API and its database (ADR-0012); the tenant state store, folded in (§6) | tenants |
| `dv02idn001v01` | **Identity** | Platform (VLAN 25) | tenant DNS, folded in (§6); later an LDAP or Active Directory–compatible directory | tenants, and operators, since management can reach Platform |
| `dv02tob001v01` | **Tenant observability** | Platform (VLAN 25) | tenant-shared logs and metrics | tenants |
| `dv02msg001v01` | **Device messaging** | IoT Backend (VLAN 35) | the VerneMQ broker and its auth database (ADR-0012); later other device rendezvous services | devices |

- **Provisioning** holds what a tenant's `terraform apply` talks to: the API that registers devices,
  and the store that keeps the tenant's state.
- **Identity** holds naming and directory: who and what things are called.
- **Every VM is created the way the hypervisor's page prescribes:** *"Management VMs are created
  using **Ansible only**"*, with a MAC derived from its VMID.

### 2. A VM never spans two segments

- **A domain VM has an interface on exactly one segment.** Anything that crosses segments goes
  through the core router and its zone policy.
- **A domain that needs two segments becomes two VMs.** Observability is the first case: one on
  management for the substrate, one on Platform for tenants (§5).

### 3. Each function stays separable

- **Every function is its own container**, with its own data directory.
- **Every function keeps its own inventory group**, as tenant DNS, tenant state and the MQTT broker
  already do. Moving a function to another VM changes which host is in its group. It isn't a
  rebuild.
- **A new service joins the VM of its domain**, on the segment that domain sits on. If no existing
  domain fits, it's a new domain VM.

### 4. Naming

- **New role mnemonics:** `nms` (network management), `sob` (substrate observability), `tob` (tenant
  observability), `prv` (provisioning), `idn` (identity) and `msg` (device messaging).
- **Each code joins the naming standard's §3.4 table in the change that introduces its host**, as
  the standard requires, not in this record.
- **The two observability VMs get separate roles:** `sob` for the substrate on management, and `tob`
  for tenants on Platform. They serve different audiences on different segments, so they are
  different classes of host, not two instances of one. The `t` prefix follows `tdn` and `tst`.
- **Retired codes:** `tdn`, `tst` and `mqt` retire when their services fold into `idn`, `prv` and
  `msg`.

### 5. Observability comes in two flavours

- **Substrate observability (`sob`) sits on management.** IoT Backend can't reach management
  (§9), and no rule lets Platform reach it. So it **collects by pull** from Platform and IoT
  Backend, over `management -> platform` and `management -> iot_backend`, both already declared.
  Hosts on management can push to it. *This follows from the zone policy; the collection tooling is
  not yet chosen.*
- **Tenant observability (`tob`) sits on Platform.** Tenants reach it over
  `tenant_transit -> platform`, which is already declared.

### 6. Tenant DNS and the tenant state store fold in

- **The intent:** `dv02tdn001v01` becomes a container in the identity VM, and `dv02tst001v01` a
  container in the provisioning VM.
- **What that fixes:** it also moves them off the management segment, where the standard says tenants
  must not reach.
- **When:** it's done by its own change record, not by this one.

### 7. The Omada controller is a container in the network management VM

- **It sits on the management segment (VLAN 99)**, the subnet and VLAN that ADR-0009 requires for
  adoption.
- **Its host, the network management VM, is the host in `network_controllers`.** Playbooks such as
  `omada-wireless.yml` and the Open API client talk to it, not to the Builder.

### 8. A rebuild uses the network management VM's controller

1. **Build the pre-VLAN substrate with no controller:** the core router, and the access switch
   configured standalone by `switch_vlans`.
2. **Build the management hypervisor**, then the domain VMs.
3. **Start the controller container**, and run the controller's manual floor on it (ADR-0009 §5):
   the setup wizard and Owner account, then the Open API client.
4. **Define the site from inventory, adopt, then provision** (ADR-0009 §6).

The Builder's controller is not a step in this order.

### 9. CHG-0005 waits for the network management VM

The AP is adopted straight into the controller's official home, so it is adopted once. Adopting it
into the Builder's controller first would mean a second adoption later. That wasn't chosen
(operator decision, 2026-09-14).

### 10. How the Deevnet API reaches the controller

The API runs on Platform and the controller on management. A narrow `platform -> management` rule,
from the provisioning VM to the network management VM's Open API port only, is declared when the API
is built (ADR-0012 §7).

---

## Consequences

**Grouping follows purpose, and names say it.** Five of the six VMs come from services that were
heading for a VM each, and the sixth, substrate observability, was coming anyway. Each VM holds a
domain, not a single container.

**Containers in one VM share its fate.**
- **Identity:** rebooting the identity VM takes tenant DNS, and later the directory. ADR-0004 already
  accepted that for tenant DNS at lab scale.
- **Messaging:** rebooting the messaging VM takes the broker and its auth database together, which
  is the intended fate-sharing (ADR-0012 §7).
- **Provisioning:** rebooting the provisioning VM stops provisioning and the state store, but no
  device.
- **Audiences stay apart:** substrate-facing and tenant-facing services never share a VM, which
  keeps ADR-0004's reason for separate hosts.

**Moving the controller costs nothing today.** The Builder's controller has no adopted devices, and
its database is derived state. Only the manual floor is repeated: the Owner account and the Open API
client.

**CHG-0005 moves back** behind the network management VM, and so does the PPSK device test in
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
- the naming standard's §3.4 table, as each host is introduced
- the controller runbooks: [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/)
  and the upgrade procedure
- [Important URLs](/docs/runbook/network/important-urls/)
- the tenant networking page, which still describes shared services on the management segment

---

## Open questions

1. **What happens to the Builder's `omada_controller` role?** Retire it, or keep it as a recovery
   fallback for when the management hypervisor is down.
2. **How is the new controller's Owner account registered?** **Answered on 2026-09-15**
   ([CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) Step 9): a **local** Owner, not
   cloud-registered.
   - **`registeredRoot: true` does not mean cloud-registered.** The new controller reports it with
     a local Owner, exactly as the Builder's does. The reading of that field in this question and
     in CHG-0005's baseline was wrong. *This is inference from the two controllers, not a vendor
     statement.*

---

## Current state

- **Proposed.** Nothing is built.
- The controller still runs on the Builder, with no devices adopted.
- Tenant DNS, tenant state and the MQTT broker are still one VM each on `dv02hyp001p01`.
