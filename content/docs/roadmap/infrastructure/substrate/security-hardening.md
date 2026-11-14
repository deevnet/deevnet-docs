---
title: "Security Hardening"
weight: 13
value: [secure-by-default, contained-failure]
waypoints:
  - title: "Tenant workloads keep their own source address at platform services, so a secrets reader is bound to its one workload"
    status: planned
    value: [contained-failure]
  - title: "A device's broker account works only from its own MQTT client id"
    status: planned
  - title: "A revoked or exposed certificate under a Deevnet CA stops being trusted before it expires"
    status: planned
  - title: "Tenant enrollment tokens are delivered encrypted to the tenant's own key"
    status: planned
---

# Security Hardening

Hardening that was found along the way and deliberately deferred. Each one is a gap the site runs
with today on purpose: the [risk register](/docs/policies/risk-management/risk-register/) entry
beside it says why that is acceptable for now, and what would bring it forward. A plan is written
when work on one of them starts.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

## What each one closes

- **A secrets reader bound to its own workload:**
  [R-16](/docs/policies/risk-management/risk-register/#register). The tenant fabric's exit node
  source-NATs every workload, so a reader is bound to the whole fabric
  ([CHG-0067](/docs/changes/2026/0067-tenant-secrets/)).
- **Broker accounts bound to a client id:**
  [R-09](/docs/policies/risk-management/risk-register/#register). A leaked device password works from
  any client id ([Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/)).
- **Revocation under the Deevnet CAs:**
  [R-14](/docs/policies/risk-management/risk-register/#register). No CRL or OCSP is published
  ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)).
- **Encrypted enrollment token delivery:**
  [R-08](/docs/policies/risk-management/risk-register/#register). Tokens are handed over by hand
  ([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §9).
