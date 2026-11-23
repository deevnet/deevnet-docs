---
title: "CHG-0082: The Unused ISC DHCP Plugin Removed From the Core Router"
weight: -82
---

# CHG-0082: The Unused ISC DHCP Plugin Removed From the Core Router

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Decommission |
| **Classification** | Routine |
| **Status** | **Planned** |
| **Window** | A few minutes, operator on site. No outage expected: Kea serves DHCP throughout |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` |
| **Automation** | None for the removal: the web interface's firmware page, by the operator. Read before and after by `make discover` |
| **Risk** | Low. Most likely to go wrong: removing the plugin disturbs DHCP on a segment, found by a lease renewing after it |
| **Related changes** | [CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/), whose discovery report found the plugin |
| **Related incidents** | None |
| **Related runbooks** | [Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/), whose steps this change follows |

---

## Summary

The core router serves DHCP with Kea. The site started with ISC dhcpd and moved to Kea for its API,
which the `opnsense_dhcp` role and the Deevnet API both write reservations through. ISC dhcpd has
not been used since, but its plugin, `os-isc-dhcp` (1.0_7), is still installed: the discovery report
of 2026-11-23 found it. There is no plan to go back to it. This change removes the plugin, so what is
installed is what is used.

## Goal

- `make discover` no longer lists `os-isc-dhcp` on the router.
- Kea serves DHCP on every segment with a pool, as before.

## Scope

**In scope:** the `os-isc-dhcp` plugin.
**Out of scope:** Kea and its configuration; any other plugin.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| ISC dhcpd is still enabled on an interface and something depends on it | the router's DHCP | Step 2 checks that no interface has ISC DHCP enabled and that Kea holds the leases, before anything is removed |
| The removal disturbs Kea | every segment with a pool | Step 4 renews a lease on a DHCP segment and reads Kea's leases |
| The router misbehaves after the removal | the management path | The operator on site with the console ([Core Router console recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/)); the configuration backup from Step 1 |

## Prerequisites

- [ ] The operator on site, with the router's console
- [ ] [CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/)'s follow-up done: a backup of 26.7.9's configuration in the inventory

## Procedure

### Step 1: Record where it starts

No outage.

**Run:**

```bash
cd ansible-collection-deevnet.mgmt && make discover
cd ansible-collection-deevnet.net && make backup-router
```

**Verify:** the report lists `os-isc-dhcp`; the backup is committed through a pull request.

### Step 2: Check that ISC DHCP is unused

No outage.

**Verify,** in the web interface: no interface has ISC DHCPv4 or DHCPv6 enabled, and Kea's leases
list holds the site's current leases.

If any interface has ISC DHCP enabled, stop: that is a finding, not part of this change.

### Step 3: Remove the plugin

No outage expected.

**Run:** on the firmware page's plugins list, remove `os-isc-dhcp`.

**Verify:** the plugins list no longer shows it as installed.

### Step 4: Verify DHCP

**Verify:**
1. A host on a DHCP segment renews its lease, and Kea's leases list shows the renewal.
2. `make discover`: no `os-isc-dhcp`, and nothing else on the router changed against Step 1's report.

## Verification

The two points under Goal.

## Undo

Reinstall `os-isc-dhcp` from the same plugins list. Its settings, if it needs them, are in the
configuration backup from Step 1.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: discovery report and configuration backup taken
- [ ] Step 2: ISC DHCP enabled on no interface; Kea holding the leases
- [ ] Step 3: `os-isc-dhcp` removed
- [ ] Step 4: a lease renewed through Kea; discovery shows the plugin gone
- [ ] The router's configuration backed up again, through a pull request
- [ ] The Software Catalog's gap for `os-isc-dhcp` closed

## Outcome

To be written when the change has run.

## Follow-ups

None yet.
