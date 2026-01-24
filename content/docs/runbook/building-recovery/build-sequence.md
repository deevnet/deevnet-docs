---
title: "Build Substrate"
weight: 4
---

# Build Substrate

Linear sequence for a greenfield substrate build. Callouts indicate where to start for component-only rebuilds.

---

## Prerequisites

1. **Artifacts staged** — See [Stage Artifacts](../online-preparation/)
2. **Inventory seeded** — See [Seed Inventory](../inventory-setup/)
3. **Bootstrap node connected** to substrate network

---

## Step 1: Enable Bootstrap-Authoritative Mode

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make bootstrap-auth
```

> **Component rebuild:** If Core Router is running, skip to Step 4.

---

## Step 2: Build Network

See [Build Network](../build-network/) for Core Router, VLANs, and wireless.

> **Core Router rebuild only:** Start here, then proceed to Step 3.

---

## Step 3: Enable Core-Authoritative Mode

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make core-auth
```

---

## Step 4: Build Management Plane

See [Build Management Plane](../build-management-plane/) for hypervisor provisioning.

> **Hypervisor rebuild only:** Start here.

---

## Quick Reference

| Scenario | Start at |
|----------|----------|
| Greenfield | Step 1 |
| Core Router rebuild | Step 2 |
| Hypervisor rebuild | Step 4 |
| Tenant rebuild | [Build Tenants](../build-tenants/) |
