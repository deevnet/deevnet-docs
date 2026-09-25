---
title: "Risk Register"
weight: 5
---

# Risk Register

The known risks, how likely and how bad each is, how it is being treated, and the record that owns
it. An entry is added when a risk is identified — in an ADR, a change or an incident — and reviewed
when a related record changes state.

**Likelihood** and **impact** are *low / medium / high*. **Treatment** is one of *reduce*
(something is being done), *accept* (deliberately lived with), *avoid* (the design routes around
it) or *transfer*.

---

## Register

| # | Risk | Likelihood | Impact | Treatment | Owning record | Status |
|---|---|---|---|---|---|---|
| R-01 | **Tenant state and API registry have no second copy.** Both sit on the provisioning VM's OS disk; losing that disk loses the copies tenants restore *from* | Medium | High | Reduce — data disk and replica | [ADR-0014](/docs/architecture/decisions/0014-tenant-state-durability/) | Open — Proposed; replica location undecided |
| R-02 | **The state store's software is unmaintained upstream.** MinIO's community edition was archived on 2026-04-25; no further releases or fixes. Since 2026-09-24 quay.io also refuses the pinned image (`unauthorized`), so the Builder's mirrored tarball is the only copy a rebuild can use ([CHG-0025](/docs/changes/2026/0025-tenant-downloads/)) | High | Medium | Reduce — replace behind a stable S3 contract | [ADR-0026](/docs/architecture/decisions/0026-object-storage/) | Open — Proposed |
| R-03 | **The state store is plain HTTP.** Tenant state, which holds every credential a tenant was issued, crosses the platform network unencrypted | Medium | High | Reduce — TLS, as the design already says | [ADR-0026](/docs/architecture/decisions/0026-object-storage/), [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/) | Open |
| R-04 | **The core router is a single device with a NIC fault.** Recurring `re0` watchdog timeouts; the router is the whole site's gateway and policy point | High | High | Reduce — vendor driver or replacement hardware | [INC-0004](/docs/incidents/2026/0004-core-router-lost/) | Open — investigating |
| R-05 | **No redundancy in the critical path.** One router, one switch, standalone hypervisors, local storage, no out-of-band management | Medium | High | Accept — recovery is *rebuild*, not failover | [Resiliency & Limits](/docs/policies/risk-management/resiliency/) | Accepted |
| R-06 | **The rebuild path lives inside what it rebuilds.** The Builder is one physical node | Low | High | Accept, for now — a second detachable Builder is hardware, not design | [Resiliency & Limits](/docs/policies/risk-management/resiliency/) | Accepted |
| R-07 | **No automated vulnerability tracking or scanning.** Advisories are followed by hand | Medium | Medium | Reduce — feeds, scanning, CI | [Vulnerability Management](/docs/policies/risk-management/vulnerability-management/) | Open — planned |
| R-08 | **Tenant enrollment tokens are handed over by hand.** The designed age-encrypted delivery is not built | Low | Medium | Reduce — build the delivery; meanwhile admit close to use (72h expiry, single use) | [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §9 | Open |
| R-09 | **Broker accounts are not bound to a client id.** A leaked device password works from any client id | Low | Medium | Accept — revoke by `-replace`; topic confinement still holds | [Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/) | Accepted |
| R-10 | **Build secrets rendered to plaintext files.** The Proxmox API token was written to `build/pve-env/*.env` for Packer and the fabric, and the files outlived every build | Medium | High | Reduce — fetch per run from OpenBao, never to disk | [CHG-0026](/docs/changes/2026/0026-build-secrets/) | Closed — CHG-0026 Complete |

---

## Adding or changing an entry

- **Add** an entry when a record identifies a risk that outlives the record — an ADR consequence, a
  change's "not tested", an incident's root cause that is not fixed
- **Close** it in the same commit as the record that treats it, with the record linked
- **Keep closed entries**, struck through or moved to a closed table, so the history stays
  traceable ([Traceability](/docs/policies/risk-management/traceability/))
