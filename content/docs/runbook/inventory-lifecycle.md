---
title: "Inventory Lifecycle"
weight: 5
---

# Inventory & Lifecycle Management

Documents how **infrastructure assets are tracked, managed, and retired**.

---

## Scope

This section includes:

- Host identity and inventory sources of truth
- Hardware lifecycle stages (active, standby, retired)
- Image and configuration lifecycle expectations
- Decommissioning and cleanup principles

This section ensures infrastructure ages intentionally, not accidentally.

---

## Lifecycle Stages

| Stage | Description |
|-------|-------------|
| **Provisioning** | Host being set up, not yet in service |
| **Active** | In production use |
| **Standby** | Available but not currently assigned |
| **Maintenance** | Temporarily offline for updates/repairs |
| **Retired** | Decommissioned, removed from inventory |

---

## Inventory Sources of Truth

- **ansible-inventory-deevnet** - Canonical host identity
- **OPNsense** - Authoritative DNS/DHCP (production)
- **Bootstrap node** - Authoritative DNS/DHCP (during provisioning)

---

## Decommissioning

When retiring a host:

1. Remove from active service (update DNS CNAMEs)
2. Run cleanup playbook (remove secrets, keys)
3. Update inventory status to retired
4. Archive or wipe storage as appropriate
5. Update documentation

---

## See Also

- [Identity vs Intent](/docs/standards/identity-vs-intent/) - How identity and intent are separated
- [Building & Recovery](../building-recovery/) - Provisioning new hosts
