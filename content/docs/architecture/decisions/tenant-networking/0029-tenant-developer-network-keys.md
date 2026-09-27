---
title: "ADR-0029: Tenant Developer Network Keys"
weight: -29
---

# ADR-0029: One Key per Tenant on the Tenant Developer Network, Issued at Admission

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-27 |
| **Scope** | How a tenant developer's laptop gets onto `DVNTM-TD`, how one tenant is kept from another there, and how that access ends. Not what the segment may reach (CHG-0022, CHG-0024, ADR-0028 §5). |
| **Amends** | [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/)'s design note *"A shared key, not PPSK"*; [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §10 (what an admission hands over) |
| **Related** | [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §3 (per-tenant PPSK keys), [ADR-0028](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/), [CHG-0029](/docs/changes/2026/0029-tenant-developer-network-keys/) |

---

## Context

`DVNTM-TD` is where a tenant developer's laptop sits to apply Terraform, reach the broker, read logs
and, after ADR-0028, log in to its workloads. Today every tenant shares one WPA2-Personal key on it,
with PMF off, and laptops on it can reach each other. Together that lets tenant A take tenant B's
tenant:

- **One shared key decrypts everyone.** Anyone holding a WPA2-Personal key who captures another
  client's handshake can decrypt that client's traffic.
- **No client isolation.** A laptop can reach any other laptop on the segment directly, and can
  spoof ARP for the gateway.
- **The state store is plain HTTP.** A tenant's state crosses the segment in the clear, and it holds
  the tenant's API token and every other substrate-issued secret.

A shared key also cannot be revoked for one tenant: offboarding one means re-keying everyone.

What the controller offers (Open API spec 6.3.0.45, as the running controller publishes it):

- **Guest mode** isolates clients but also *"blocked from reaching any private IP subnet"* (Omada
  support document 12928), so a laptop could not reach the API. Not usable.
- **EAP ACLs** match on an SSID (`sourceType` 4) and drop or allow to an IP group.
- **PPSK** gives each key its own password and an optional MAC binding (`PpskSetting.mac`). It is
  WPA2 only; the PPSK settings carry no WPA3 option.

## Decision

### 1. Admission issues the tenant's first key

A laptop needs `DVNTM-TD` to reach the API, so the first key cannot come from the tenant's own
apply. `POST /v1/admissions` returns a `DVNTM-TD` PPSK key with the enrollment token, and the
operator hands both over together. When the tenant creates itself the key becomes its own Wi-Fi key
`admission`: listed, deletable, and revoked when the tenant is deleted. Admitting the name again
replaces the key, and `DELETE /v1/admissions/{name}` revokes one never used.

### 2. A tenant issues itself more keys

`DVNTM-TD` becomes a PPSK segment in inventory, so it becomes an API trust class, `tenant_dev`,
like `iot`. A tenant issues itself a key per laptop, for a teammate or a second machine, with
`deevnet_iot_wifi_key`, and revokes it the same way.

### 3. A key may be bound to one laptop's MAC

Optional, on the admission and on any key. A key that leaks, or is shared, then works only from the
laptop it was issued for. It is optional because modern laptops use a private, sometimes rotating,
Wi-Fi address, and registering one is friction a tenant may not want.

### 4. Laptops are isolated from each other

Two EAP ACLs on the SSID: allow to the segment's gateway, then drop to the rest of its subnet. This
filters IP, not ARP, so it stops a laptop reaching a laptop but not an ARP-spoofing man in the
middle. **Every service `DVNTM-TD` reaches must therefore be TLS.** The API, broker, log store,
Grafana and downloads are; the state store is not, and its TLS is the next change.

### 5. New PPSK profiles are never empty

The wireless play creates a profile holding the API's placeholder key, and the API clears it when it
issues the first real key. An SSID bound to a profile that was empty when the SSID was created did
not authenticate keys added later ([CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/)
phase 5). `DVNTM-TD`'s new profile is the first built this way, and its first key working is the
proof.

## Consequences

- **Access ends with the tenant.** Deleting a tenant revokes every key it holds on `DVNTM-TD`.
- **One key per laptop is the tenant's choice,** at the cost of one resource each.
- **Existing tenants need a key before they can apply from `DVNTM-TD` again.** The operator issues one
  with the operator token, or the tenant applies once from a trusted seat.
- **Everyone on `DVNTM-TD` today is disconnected** when the SSID is recreated as PPSK.
- **Still WPA2.** A tenant's own key protects its traffic from other tenants, because each key yields
  its own session keys; WPA3-SAE would add forward secrecy but is not offered with PPSK.

## Alternatives considered

- **A shared WPA3-SAE key.** Stops passive decryption, but it is mixed mode with WPA2 clients, and it
  is still one key that cannot be revoked per tenant. Rejected.
- **A MAC allow-list on the SSID.** A MAC address is sent in the clear and is easy to copy, it
  encrypts nothing, and it does not separate one tenant from another. Kept only as §3's optional
  binding on top of a per-tenant key.
- **Guest mode.** Blocks the private addresses the segment exists to reach. Rejected.
- **A VLAN per tenant, bound per key.** Real separation, but it multiplies segments, DHCP scopes and
  firewall rules by tenant, which ADR-0011 rejected for devices for the same reason.

## Open questions

1. **A per-session expiry for meetups.** A PPSK profile can expire (`PPSKExpirationVO`), but per
   profile, not per key. Not built.
