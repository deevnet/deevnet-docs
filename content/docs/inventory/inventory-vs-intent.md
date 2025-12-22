---
title: "Identity vs Intent in Deevnet"
weight: 3
---

# Identity vs Intent in Deevnet

## Purpose

This document explains how **identity** and **intent** are deliberately separated in the Deevnet infrastructure model.

The goal of this separation is to ensure that:

- Hosts can change purpose without renaming
- Workloads can move without rewriting inventory
- Configuration intent can be preserved, detached, and reused
- Infrastructure history is not lost when systems are repurposed
- Inventory remains truthful over time

This document complements the **Deevnet Naming Standard** and focuses specifically on how inventory and configuration are modeled in Deevnet.

---

## Core Principle

**Identity describes what a system *is*.  
Intent describes what a system is *doing right now*.**

These two concerns are related, but they must not be conflated.

When identity and intent are mixed:

- hostnames become lies
- inventory accumulates drift
- configuration becomes sticky
- repurposing hardware becomes painful

Deevnet explicitly avoids this by design.

---

## What Identity Means in Deevnet

**Identity** is the stable, long-lived description of a system.

Identity answers questions like:

- What physical or virtual system is this?
- Where does it live (substrate)?
- How is it addressed?
- What hardware or execution class is it?

Identity is expressed via:

- DNS hostname
- Inventory hostname
- Deterministic MAC-to-IP mapping
- Minimal host variables

### Examples of Identity

- pi01.dvntm.deevnet.net  
  A specific Raspberry Pi slot

- hv01.dvntm.deevnet.net  
  A hypervisor host

- edge-rt01.dvntm.deevnet.net  
  An edge routing appliance

Identity does **not** change simply because software or workloads change.

Hardware identity is expressed under deevnet: and is substrate-agnostic. Environment binding is expressed under env:.

---

## What Intent Means in Deevnet

**Intent** describes what functionality is being applied to a system at a given point in time.

Intent answers questions like:

- What services should this system provide?
- What packages should be installed?
- What roles should be applied?
- What behavior does this host currently embody?

Intent is:

- movable
- reusable
- optional
- allowed to become temporarily unused (orphaned)

Intent is *not* permanently bound to a specific host.

---

## Why Host Variables Are Not Enough

Inventory host variables are convenient, but overusing them causes long-term problems.

If workload-specific configuration is embedded directly in host variables:

- repurposing a host requires deleting history
- configuration intent becomes trapped
- inventory becomes dishonest
- temporary experiments become permanent accidents

Example of what **not** to do:

```yaml
# host_vars/pi01.yml
install_sdr: true
rtl_device: 0
soapysdr_enabled: true
```

This couples **identity** (pi01) with **intent** (SDR).

---

## The Deevnet Model: Identity First, Intent Detached

Deevnet separates these concerns explicitly.

### Identity Lives In

- Inventory structure
- host_vars
- Substrate boundaries

Identity variables should be:

- stable
- minimal
- long-lived

Typical identity variables include:

- IP address
- MAC address
- hardware class
- management metadata
- baseline configuration flags

---

## Intent Lives in Workload Profiles

Deevnet expresses workload intent via **reusable workload profiles**.

These are typically stored in a directory such as:

```
workload_vars/
```

Each file represents **a unit of intent**, not a host.

Examples:

- sdr.yml
- metrics.yml
- pxe.yml
- dns-cache.yml

A workload profile may include:

- packages
- services
- configuration templates
- role parameters

Workload profiles are loaded explicitly by playbooks and are **not** part of Ansible’s automatic variable precedence.

---

## Orphaned Intent Is a Feature

In Deevnet, it is acceptable — and intentional — for workload profiles to exist even when no host currently uses them.

This allows:

- pausing a project without deleting its configuration
- moving workloads between hosts cleanly
- preserving institutional memory
- experimenting without polluting inventory

A workload profile with zero active assignments is not dead — it is **parked intent**.

---

## Assigning Intent to Hosts

How intent is assigned is intentionally flexible.

### Option 1: Host-local workload list

```yaml
# host_vars/pi01.yml
dvnt_workloads:
  - sdr
```

Playbooks load the referenced workload profiles dynamically.

### Option 2: Assignment files

```
assignments/
  pi01.yml
  pi02.yml
```

Each assignment file lists the workloads currently attached to that host.

Both approaches preserve the same separation:

- identity stays stable
- intent moves freely

---

## Services Are Intent, Not Identity

A host named `pi01` running an SDR workload does **not** become `sdr-pi01`.

Instead:

- the service name `sdr.dvntm.deevnet.net` points to the host
- DNS expresses current intent
- the hostname remains truthful

When SDR moves to another host:

- the CNAME changes
- the workload assignment changes
- hostnames do not

---

## Relationship to Naming

This document complements the **Deevnet Naming Standard**.

The naming standard defines:

- how systems are identified
- how services are named
- how topology is expressed

This document defines:

- how behavior is applied
- how configuration moves
- how inventory remains truthful over time

Together, they form a coherent infrastructure model.

---

## Summary

- Identity is stable and long-lived
- Intent is movable and reusable
- Hostnames describe what a system *is*
- Services describe what a system *does*
- Workload profiles allow intent to be detached and reassigned
- Orphaned intent is intentional, not accidental

This separation allows Deevnet to grow, change, and experiment without naming drift, inventory corruption, or configuration debt.
