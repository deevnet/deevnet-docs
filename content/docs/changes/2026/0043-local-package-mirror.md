---
title: "CHG-0043: A Local Package Mirror"
weight: -43
---

# CHG-0043: A Local Package Mirror

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After the [package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/) evaluation |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the artifact server), every Fedora substrate host, both hypervisors |
| **Automation** | `deevnet.builder` `artifacts` role; `deevnet.builder` and `deevnet.mgmt` `base` roles for the repository configuration |
| **Risk** | Medium. Most likely to go wrong: a stale mirror that leaves hosts unpatched. A sync schedule and an age check guard it |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/), [Stage Artifacts](/docs/runbook/substrate/building-recovery/online-preparation/) |

---

## Summary

Substrate hosts install offline, but every package installed or updated after the first boot comes from
the internet: the local mirror carries each Fedora release as released, and hosts aren't pointed at it.
[Correctness](/docs/standards/correctness/) §5.4 was narrowed to the install to say so. This change
mirrors the update repositories and points hosts at them, so a rebuild can run with no internet, and
restores the stricter standard
([2026-10 review: R8](/docs/architecture/reviews/2026-10-rebuild-and-access/#r8-packages-from-the-internet)).

## Goal

- The artifact server mirrors Fedora's `updates` for each release in use, and the Proxmox and Debian
  repositories the hypervisors use, on a schedule.
- Every substrate host takes packages from the local mirror.
- A rebuild of a management-plane VM with the site's internet link down completes.
- §5.4 covers provisioning again, not only the install.

## Scope

**In scope:** the mirrors, the sync, the hosts' repository configuration.
**Out of scope:** tenants and edge devices (§5.4's scope is the substrate).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The mirror goes stale | the artifact server | A sync timer and an age check that fails visibly |
| Disk use | the Builder | Sized by the evaluation before any sync runs |

## Prerequisites

- [ ] The package mirror evaluation, Approved, with its sizing

## Procedure

### Step 1: The mirrors

Sync `updates` and the hypervisors' repositories to the artifact server on a schedule.

### Step 2: Point the hosts at them

The `base` roles configure each host's repositories to the local mirror.

**Verify:** `dnf` and `apt` on a host fetch from the artifact server.

### Step 3: The offline rebuild

Rebuild one management-plane VM with the internet link down.

**Verify:** it completes; every role that installs a package succeeds.

### Step 4: The standard

Restore §5.4 to cover provisioning.

## Verification

Step 3 passes.

## Undo

Point hosts back at the upstream repositories.

## To discover

- Mirror sizing and sync time, from the evaluation.
