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
- Environment-safe (the site is always explicit in the name)
- Service-oriented (service names are stable even if hosts move)

This naming standard applies to:
- DNS zones and hostnames
- Service endpoints (artifacts, PXE, DNS, etc.)
- Tenants (logical workload namespaces)
- Inventory naming (host identifiers)

---

## 1. Definitions

### Site
A site is a self-contained infrastructure boundary that hosts systems and workloads.

Current sites:
- home — home site, site code `01`
- mobile — mobile site, site code `02`

Site names are treated as environment identifiers, not workloads.

### Tenant
A tenant is a logical workload namespace (e.g., grooveiq, vintronics). Tenants may be deployed to one or more sites.

### Host
A host is a physical, virtual, or embedded system with a deterministic identity (ideally MAC → IP mapping on a site network).

### Service
A service is a logical endpoint that may move between hosts without changing its public name.

---

## 2. DNS Zones

### 2.1 Root Zone
deevnet.net is the root DNS zone.

### 2.2 Site Zones
Each site has its own sub-zone:

- home.deevnet.net
- mobile.deevnet.net

All site-specific host and service records MUST exist in the corresponding site zone.

> **Migration in progress.** This standard was updated on acceptance of
> [ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/) and states the target. The
> estate currently runs on the `home` / `mobile` zones and the previous `[role-]formNN` hostnames;
> both are being migrated in stages. Until that completes, the standard leads and reality follows —
> see the [Host Rename runbook](/docs/runbook/host-rename/) for where the estate actually is.

---

## 3. Host Naming

### 3.1 Hostname Format

Hosts MUST use a fixed-width hostname of exactly **thirteen characters**, per
[ADR-0008](/docs/architecture/decisions/0008-host-naming-site-codes/):

```
dv{NN}{rrr}{sss}{f}{gg}

dv | 02 | hyp | 001 | p | 01
```

| Range | Field | Meaning |
|-------|-------|---------|
| `[0:2]` | `dv` | Constant. Marks the estate, and keeps the label off a leading digit |
| `[2:4]` | site | Two-digit site code |
| `[4:7]` | role | Three-letter mnemonic |
| `[7:10]` | sequence | `001`–`999`, restarting per role per site |
| `[10]` | form | Execution class — one letter |
| `[11:13]` | version | `01`–`99`, hardware generation of that instance |

Every field is fixed width, so a field is a substring at a known offset. Names MUST NOT contain a
separator.

Examples:
- dv02hyp001p01.mobile.deevnet.net
- dv02cor001v01.mobile.deevnet.net
- dv01hyp001p01.home.deevnet.net
- dv00bld001p01.deevnet.net

---

### 3.2 Site Codes

| Code | Site |
|------|------|
| `00` | No site — an appliance that moves between sites |
| `01` | Home |
| `02` | Mobile |

A host that belongs to no site MUST use `00`. Site codes are allocated deliberately and MUST NOT be
derived from the addressing plan, so that renumbering a site does not rename its hosts.

---

### 3.3 Form Codes (Execution Class)

Form codes describe what the system is, not what software it runs.

- `p` — Physical
- `v` — Virtual machine
- `e` — Embedded device
- `c` — Container *(reserved; unused)*

Form codes MUST remain valid if the operating system or platform changes. The hardware class beyond
physical-versus-virtual is carried by the role mnemonic, not by the form code.

---

### 3.4 Role Mnemonics

The role is a three-letter mnemonic and is **mandatory** — there is no unprefixed form.

| Code | Class | | Code | Class |
|---|---|---|---|---|
| `hyp` | Hypervisor | | `bld` | Builder |
| `cor` | Core router | | `tdn` | Tenant DNS |
| `edg` | Edge router | | `tst` | Tenant state |
| `acc` | Access switch | | `bgw` | Bell gateway |
| `wap` | Wireless AP | | `rpi` | Raspberry Pi |

Mnemonics are allocated deliberately, like tenant indices. A new class MUST have its code added
here in the same change that introduces the host.

For network devices the mnemonic names **topological position** rather than device type — `cor` is
correct whether the core router is an appliance or a virtual machine.

---

### 3.5 Sequence and Version

The sequence distinguishes instances of the same role at the same site and restarts per role per
site. It is allocated densely.

The version distinguishes successive hardware behind one logical instance, so a replacement and the
thing it replaces can exist at the same time. It MUST be incremented **when old and new must
coexist** — a physical box being replaced, or a VM stood up as a separate instance for a migration.
A plain rebuild MUST NOT increment it: a rebuilt host returns to the same identity through the same
hardware address.

---

### 3.6 Secondary Interfaces

The hostname is the host's **root name** and belongs to its primary address. Additional addressed
interfaces MUST be named as the root name, a hyphen, and an interface code:

```
dv02cor002p01        the primary
dv02cor002p01-wan    the upstream interface
```

A host with one addressed interface MUST NOT carry a suffix.

| Code | Interface |
|------|-----------|
| `-wan` | Wired upstream |
| `-wifi` | Wireless upstream |
| `-lan` | Downstream |
| `-stor` | Storage |
| `-tran` | Fabric transit |
| `-oob` | Lights-out / BMC |
| `-mgmt` | Management, when it is not the primary |

Interface codes are curated, and MUST NOT be derived from an interface's declared purpose or
segment — a purpose collides where one host has two interfaces serving the same one, and a segment
is absent on precisely the interfaces that need a name.

Being named is not the same as being published: a record is published only where the address is
deterministic. An interface leasing its address from an upstream network has a name here and no
record in DNS.

---

### 3.7 Allowed Characters
- Lowercase letters a–z
- Digits 0–9
- Hyphen (-), only as the separator before an interface code
- No underscores

---

## 4. Service Naming

### 4.1 Service Names Are Not Hostnames
Service names MUST remain stable even if the service moves between hosts.

Services SHOULD resolve to hosts using DNS records (CNAME preferred).

---

### 4.2 Site-Scoped Service Names (Preferred)

Infrastructure services MUST use site-scoped DNS names:

service.site.deevnet.net

Examples:
- artifacts.mobile.deevnet.net
- pxe.mobile.deevnet.net
- dns.home.deevnet.net
- vault.home.deevnet.net

These records SHOULD be CNAMEs pointing to host A records.

---

### 4.3 Global Provisioning Alias (Optional)

A global alias MAY exist for provisioning workflows:

service.deevnet.net

Rules:
- MUST be managed via Config-as-Code
- MUST NOT change implicitly
- SHOULD be a CNAME to a site-scoped service

Example:
artifacts.deevnet.net → artifacts.mobile.deevnet.net

---

## 5. Tenant Naming

### 5.1 Tenant Names
Tenant names represent workload namespaces and MUST be distinct from site names.

Examples:
- grooveiq
- vintronics
- moneyrouter

---

### 5.2 Tenant DNS Patterns
Tenants SHOULD be expressed under the site zone:

tenant.site.deevnet.net

Examples:
- grooveiq.mobile.deevnet.net
- vintronics.home.deevnet.net

---

### 5.3 Tenant Service Names
Tenant services SHOULD be expressed as:

service.tenant.site.deevnet.net

Examples:
- api.grooveiq.mobile.deevnet.net
- mqtt.grooveiq.mobile.deevnet.net

---

## 6. Inventory Naming

### 6.1 Inventory Host Identifiers

Inventory hostnames MUST match the DNS hostname without the domain:

Examples:
- dv02hyp001p01
- dv02cor001v01
- dv00bld001p01
- dv02rpi001p01

Because the site code is part of every hostname, names are unique across the whole estate, not only
within a site. Environment (site) association MAY additionally be expressed by:

- **Inventory boundary (preferred):**
  Separate inventories per site (e.g., `inventory/home/`, `inventory/mobile/`) implicitly define environment membership.

- **Explicit site groups:**
  When using a combined inventory, hosts MUST belong to exactly one site group:
  - `home`
  - `mobile`


---

### 6.2 Mapping to DNS
Inventory entries SHOULD map deterministically to FQDNs:

inventory_hostname.site.deevnet.net

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

### 8.1 Mobile Site Infrastructure
Hosts:
- dv02hyp001p01.mobile.deevnet.net
- dv02cor001v01.mobile.deevnet.net
- dv02acc001p01.mobile.deevnet.net

Services:
- omada-ctrl.mobile.deevnet.net → dv00bld001p01.deevnet.net
- artifacts.mobile.deevnet.net → dv00bld001p01.deevnet.net
- pxe.mobile.deevnet.net → dv00bld001p01.deevnet.net

---

### 8.2 Edge / IoT
Hosts:
- dv02rpi001p01.mobile.deevnet.net
- dv02rpi002p01.mobile.deevnet.net
- dv02bgw001e01.mobile.deevnet.net

Services:
- sdr.mobile.deevnet.net → dv02rpi001p01.mobile.deevnet.net

---

### 8.3 Secondary Interfaces
- dv02cor002p01.mobile.deevnet.net — the primary address
- dv02cor002p01-wan.mobile.deevnet.net — the upstream interface
- dv02edg001p01-wifi.mobile.deevnet.net — wireless upstream, where `-wan` is already the wired one

---

## 9. Policy Notes

- Site names MUST remain environment identifiers only.
- Roles MUST describe architecture, not implementation.
- Form codes MUST reflect execution or hardware class.
- Hard-coded IPs in provisioning flows SHOULD be treated as defects.
- Inventory, DHCP, and DNS SHOULD be generated from the same source of truth.
