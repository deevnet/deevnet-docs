---
title: "Patching"
weight: 2
---

# Patching

Day 2 maintenance and security updates for substrate hosts.

---

## Status: Planned

This section will document:

- Online patching (hosts with internet access)
- Offline patching (air-gapped substrate)
- Local dnf mirror setup for full air-gap

---

## Decision Required

Post-install updates currently require internet access. Options:

| Option | Pros | Cons |
|--------|------|------|
| Accept internet required | Simple, no extra storage | Not true air-gap |
| Full local dnf mirror | True air-gap | ~200GB per Fedora release |
| Hybrid (security only) | Balanced | Complex to maintain |

---

## Current State

Install-time packages come from ISO/cdrom (air-gap ready).

Post-install `dnf update` reaches public Fedora mirrors unless a local mirror is configured.

---

## Future Work

When this decision is made, document:

1. Mirror setup (if local)
2. Update frequency and process
3. Rollback procedures
4. Security advisory monitoring

