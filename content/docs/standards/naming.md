---
title: "Naming"
weight: 2
---

# Deevnet Naming Standard

## Purpose
This document defines the canonical naming conventions for the Deevnet ecosystem. The goal is to ensure that names are:

- Deterministic (predictable, repeatable)
- Scalable (works as the lab grows)
- Readable (humans can understand intent quickly)
- Environment-safe (dvnt vs dvntm is always explicit)
- Service-oriented (service names are stable even if hosts move)

This naming standard applies to:
- DNS zones and hostnames
- Service endpoints (artifacts, PXE, DNS, etc.)
- Tenants (logical workload namespaces)
- Inventory naming (Ansible host identifiers)

---

## 1. Definitions

### Substrate
A substrate is a network environment that hosts systems and workloads.

Current substrates:
- dvnt — home substrate
- dvntm — mobile substrate

Substrate names are treated as environment identifiers, not workloads.

### Tenant
A tenant is a logical workload namespace (e.g., grooveiq, vintronics). Tenants may be deployed to one or more substrates.

### Host
A host is a physical, virtual, or embedded system with a deterministic identity (ideally MAC → IP mapping on a substrate network).

### Service
A service is a logical endpoint that may move between hosts without changing its public name.

---

## 2. DNS Zones

### 2.1 Root Zone
deevnet.net is the root DNS zone.

### 2.2 Substrate Zones
Each substrate has its own sub-zone:

- dvnt.deevnet.net
- dvntm.deevnet.net

All substrate-specific host and service records MUST exist in the corresponding substrate zone.

---

## 3. Host Naming

### 3.1 Hostname Format

Hosts MUST use short, functional hostnames within a substrate zone using the following grammar:

[role-]formNN.substrate.deevnet.net

Where:
- role (optional) = architectural or functional role
- form = execution or hardware class
- NN = two-digit ordinal (01, 02, …)

Examples:
- hv01.dvntm.deevnet.net
- netctrl-vm01.dvntm.deevnet.net
- provisioner-ph01.dvntm.deevnet.net
- pi01.dvntm.deevnet.net
- em01.dvntm.deevnet.net

---

### 3.2 Form Codes (Execution / Hardware Class)

Form codes describe what the system is, not what software it runs.

- hv — Hypervisor host (physical machine whose purpose is to host VMs)
- vm — Virtual machine
- ph — Physical host (non-hypervisor)
- pi — Raspberry Pi (full-size / primary Pi class)
- em — Embedded device (non-primary Pi: Pi Zero, Arduino Q, Jetson, etc.)
- rt — Router / firewall appliance
- sw — Switch
- ap — Wireless access point

Form codes MUST remain valid if the operating system or platform changes.



---

### 3.3 Role Usage Rules (Prescriptive)

The role component is OPTIONAL and MUST be omitted when the form factor alone fully implies the architectural role.

Role MAY be omitted when:
- The form factor is unambiguous
- The host is an anchor device
- The name remains truthful if software changes

Examples:
- hv01 (hypervisor role implied)
- sw01, ap01
- pi01 (general-purpose Pi pool)

Role MUST be included when:
- The form factor does not imply purpose
- The host provides a specific service
- The host is not fungible capacity

Examples:
- netctrl-vm01
- provisioner-ph01

For routing devices, role prefixes (e.g., edge, core) describe stable topological position rather than software implementation.

Examples:
- edge-rt01
- core-rt02

---

### 3.4 Allowed Characters
- Lowercase letters a–z
- Digits 0–9
- Hyphen (-)
- No underscores

---

## 4. Service Naming

### 4.1 Service Names Are Not Hostnames
Service names MUST remain stable even if the service moves between hosts.

Services SHOULD resolve to hosts using DNS records (CNAME preferred).

---

### 4.2 Substrate-Scoped Service Names (Preferred)

Infrastructure services MUST use substrate-scoped DNS names:

service.substrate.deevnet.net

Examples:
- artifacts.dvntm.deevnet.net
- pxe.dvntm.deevnet.net
- dns.dvnt.deevnet.net
- vault.dvnt.deevnet.net

These records SHOULD be CNAMEs pointing to host A records.

---

### 4.3 Global Provisioning Alias (Optional)

A global alias MAY exist for provisioning workflows:

service.deevnet.net

Rules:
- MUST be managed via Config-as-Code
- MUST NOT change implicitly
- SHOULD be a CNAME to a substrate-scoped service

Example:
artifacts.deevnet.net → artifacts.dvntm.deevnet.net

---

## 5. Tenant Naming

### 5.1 Tenant Names
Tenant names represent workload namespaces and MUST be distinct from substrate names.

Examples:
- grooveiq
- vintronics
- moneyrouter

---

### 5.2 Tenant DNS Patterns
Tenants SHOULD be expressed under the substrate zone:

tenant.substrate.deevnet.net

Examples:
- grooveiq.dvntm.deevnet.net
- vintronics.dvnt.deevnet.net

---

### 5.3 Tenant Service Names
Tenant services SHOULD be expressed as:

service.tenant.substrate.deevnet.net

Examples:
- api.grooveiq.dvntm.deevnet.net
- mqtt.grooveiq.dvntm.deevnet.net

---

## 6. Inventory Naming (Ansible)

### 6.1 Inventory Host Identifiers

Ansible inventory hostnames SHOULD match the DNS hostname without the domain:

Examples:
- hv01
- netctrl-vm01
- provisioner-ph01
- pi01
- em01

Environment (substrate) association MUST be expressed by **one of the following methods**:

- **Inventory boundary (preferred):**  
  Separate inventories per substrate (e.g., `inventory/dvnt/`, `inventory/dvntm/`) implicitly define environment membership.

- **Explicit substrate groups:**  
  When using a combined inventory, hosts MUST belong to exactly one substrate group:
  - `dvnt`
  - `dvntm`


---

### 6.2 Mapping to DNS
Inventory entries SHOULD map deterministically to FQDNs:

inventory_hostname.substrate.deevnet.net

---

## 7. Addressing and Deterministic Identity

### 7.1 Identity Source of Truth
Hosts SHOULD be assigned deterministic identity via:
- MAC → IP → DNS

This mapping is considered identity, not configuration, and SHOULD be maintained as Config-as-Code.

---

### 7.2 Host vs Service Resolution
- Hosts resolve to fixed IPs via A / AAAA records
- Services resolve to hosts via CNAME (preferred)

---

## 8. Examples

### 8.1 dvntm Infrastructure
Hosts:
- hv01.dvntm.deevnet.net
- netctrl-vm01.dvntm.deevnet.net
- provisioner-ph01.dvntm.deevnet.net

Services:
- omada-ctrl.dvntm.deevnet.net → netctrl-vm01.dvntm.deevnet.net  
- artifacts.dvntm.deevnet.net → provisioner-ph01.dvntm.deevnet.net
- pxe.dvntm.deevnet.net → provisioner-ph01.dvntm.deevnet.net

---

### 8.2 Embedded Capacity
Hosts:
- pi01.dvntm.deevnet.net
- pi02.dvntm.deevnet.net
- em01.dvntm.deevnet.net

Services:
- sdr.dvntm.deevnet.net → pi01.dvntm.deevnet.net

---

## 9. Policy Notes

- Substrate names MUST remain environment identifiers only.
- Roles MUST describe architecture, not implementation.
- Form codes MUST reflect execution or hardware class.
- Hard-coded IPs in provisioning flows SHOULD be treated as defects.
- Inventory, DHCP, and DNS SHOULD be generated from the same source of truth.
