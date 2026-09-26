---
title: "Software Certification"
weight: 2
---

# Software Certification

How a release line of a product is certified for a role. The records are under
[Certification → Software](/docs/platforms/certification/software/).

---

## What is certified

A **release line of a product, for a role**: OPNsense 26.7 as the core router, Proxmox VE 9 as a
hypervisor, Grafana 13 as the tenant dashboards. Device firmware is software, and is certified the
same way.

**A line, not a version.** Patch releases inherit the line's certification. Before a patch is
applied, its release notes are read. If they change something a criterion depends on, the patch is
re-checked against that criterion, and the result is a dated addendum on the line's record.
A new line is a new revision.

**What runs inside it.** A product that bundles other software is certified as a whole, and the
record lists the bundled components the role uses. For OPNsense, that is Kea, Unbound and pf,
matching the [Software Catalog](/docs/platforms/software-catalog/#core-router-opnsense-dv02cor002p01).

---

## Criteria

*Draft. Each area is checked, and the record says what was done and what was seen.*

| Area | What is checked |
|---|---|
| **Automation** | Installed and configured from code, through an API or CLI the automation can drive; a second run changes nothing ([Correctness](/docs/standards/correctness/) §7.2) |
| **Offline supply** | The artifact can be pinned, checksummed and mirrored, and installs with no internet ([Correctness](/docs/standards/correctness/) §5.4) |
| **Upgrade and rollback** | The path from the current line is known; rollback is tested, or the step is declared irreversible |
| **Behavior the role depends on** | The specific features the role uses work on this line, tested rather than read from the release notes |
| **Security** | The line receives security fixes, and advisories have a channel the operator watches ([Vulnerability Management](/docs/policies/risk-management/vulnerability-management/)) |
| **Support and lifetime** | Support model, and the line's end-of-life date, if it has one |
| **License** | Compatible with how Deevnet uses it; recorded in the [Software Catalog](/docs/platforms/software-catalog/) |
| **Fit** | Runs within the resources its host gives it, at a realistic load |

---

## Process

1. **Open the record.** Create the item if it's new, and a revision page for the line, with the
   verdict *Under evaluation*.
2. **Evaluate off the site first.** Test in a throwaway environment where one can be built, as
   the change records do before applying. Record anything that could only be tested on the site
   as such.
3. **Record the evidence.** For each criterion: what was tested, how, and what was seen. A criterion
   that could not be tested is written as not tested, never as passed.
4. **Set the verdict.** The operator decides. *Certified with conditions* names each condition and
   what would clear it.
5. **Update the item page**: the certified lines, and the new row in its revisions table.
6. **Deploy through change management.** The change that moves to the line cites the certification,
   and updates the [Software Catalog](/docs/platforms/software-catalog/).

A line that fails is kept like one that passes. The next evaluation starts from what is already known.
