---
title: "Core Router Patch"
weight: 3
---

# Core Router Patch

How the core router, `dv02cor002p01`, is brought up to date within its OPNsense release line. The
update itself is applied by hand in OPNsense's web interface; everything around it is not. **Each
patch is a change: open a [change record](/docs/runbook/substrate/change-management/change-record-template/)
of type Upgrade, classification Routine, before the update is applied.** Its steps are the ones below.

A move to a new release line (26.7 to 27.1, say) is not a patch. It is evaluated and approved first,
as [Lifecycle Management](/docs/policies/lifecycle-management/) requires, and gets its own change.

| | |
|---|---|
| Router | `dv02cor002p01`, OPNsense, on the [Software Catalog](/docs/platforms/software-catalog/) |
| Applied through | The web interface's firmware page, by the operator. Automation reads the router through its API and has no SSH login |
| Version read by | `make discover` in `deevnet.mgmt`, which reads `core/firmware/info` |
| Configuration backup | `make backup-router` in `deevnet.net`: `config.xml`, vault-encrypted into the inventory, committed through a pull request |
| Way back | The backup taken in step 3, on the release before the update ([Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/)) |

---

## 1. Open the record

**The record exists before anything is clicked.** Start it from the template: type Upgrade,
classification Routine, the router as the system, the current and target versions in its Summary.
Add it to both change indexes in the same commit.

## 2. Read the release notes

**Every version between the running one and the target is read, not only the last.** OPNsense
publishes notes for each point release, and the firmware page shows the changelog. Quote anything
that touches a service the router runs for the site (Kea, Unbound, the firewall, the plugins
installed) in the record's Risk section, word for word.

## 3. Record where it starts

**The starting version and configuration are captured before the update.**

```bash
cd ansible-collection-deevnet.mgmt && make discover      # the version, in /srv/discovery/<date>.md
cd ansible-collection-deevnet.net && make backup-router  # config.xml into the inventory
```

Commit the backup through a pull request. It is the way back.

## 4. Have the console ready

**The router carries the management path, so its console is the way in if it does not come back.**
The operator is on site with the console cable, as [Core Router console recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/)
describes.

## 5. Apply the update

**Disruptive while the router reboots:** every segment loses routing, DHCP and DNS until it is back.

In the web interface's firmware page, check for updates, read the list against step 2, and update.
Reboot when it asks. Note the time it went down and came back.

## 6. Verify

**The router is checked from the Builder, the same way it is read every day.**

1. `make discover` reports the target version for OPNsense, and nothing else on the router changed
   unexpectedly. Compare its router section with step 3's report.
2. A name resolves through the router from the Builder, and a host on a DHCP segment still holds its
   lease.

## 7. Close

**The record closes with the backup and the catalog current.**

1. `make backup-router` again, committed through a pull request.
2. The Software Catalog's OPNsense rows updated from the report, citing the record.
3. The record's Outcome written, its status Complete, and both indexes updated.

## When a patch skipped these steps

**A patch applied without a record is recorded after the fact, as soon as it is noticed.** The
record says so in its Summary, gives what is known and marks what is not, and carries the steps it
missed (the backup, the catalog) as follow-ups. [CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/)
is one.
