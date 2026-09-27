---
title: "Software Evaluation"
weight: 2
aliases:
  - /docs/policies/lifecycle-management/certification/software-certification/
---

# Software Evaluation

How a release line of a product is evaluated for a role. The records are under
[Evaluations → Software](/docs/platforms/evaluations/software/).

---

## What is evaluated

A **release line of a product, for a role**: OPNsense 26.7 as the core router, Proxmox VE 9 as a
hypervisor, Grafana 13 as the tenant dashboards. Device firmware is software, and is evaluated the
same way.

**A line, not a version.** Patch releases inherit the line's approval. Before a patch is applied,
its release notes are read. If they change something a criterion depends on, the patch is
re-checked against that criterion, and the result is a dated addendum on the line's record.
A new line is a new revision.

**What runs inside it.** A product that bundles other software is evaluated as a whole, and the
record lists the bundled components the role uses. For OPNsense, that is Kea, Unbound and pf,
matching the [Software Catalog](/docs/platforms/software-catalog/#core-router-opnsense-dv02cor002p01).

---

## Criteria

Each criterion is checked and recorded as passed, failed, not tested or not applicable, with what
was done and what was seen. How the columns work is in [Evaluation](/docs/policies/lifecycle-management/evaluation/#how-the-criteria-are-written).

| # | Criterion | Level | Passes when | How to check |
|---|---|---|---|---|
| S1 | **Automation** | Required | Installed and configured entirely from code, through an API or CLI the automation can drive. A second run changes nothing ([Correctness](/docs/standards/correctness/) §7.2) | Run the automation twice. The second run reports no changes |
| S2 | **Offline supply** | Required | The artifact is pinned by version and checksum, mirrored on the artifact server, and installs with no internet ([Correctness](/docs/standards/correctness/) §5.4) | Install it in a throwaway environment with the upstream unplugged |
| S3 | **Upgrade and rollback** | Required | The upgrade from the current line has been done once. Rollback has been done once, or the record declares the step irreversible | Do both in a throwaway environment, following the written procedure |
| S4 | **Behavior the role depends on** | Required | Every feature the role uses is listed in the record, and each one works on this line | One test per listed feature, run rather than read from the release notes. One failure fails the criterion |
| S5 | **Security fixes** | Required | The line receives security fixes and is not due to reach end of life within **6 months**. Its advisories have a channel the operator watches ([Vulnerability Management](/docs/policies/risk-management/vulnerability-management/)) | The vendor's lifecycle page, and the advisory channel named in the record |
| S6 | **Upstream alive** | Required | Upstream is not archived, and has shipped a release in the last **12 months** | The repository's status and its release history |
| S7 | **License** | Required | The license allows how Deevnet uses it, and is recorded in the [Software Catalog](/docs/platforms/software-catalog/) | Read the license or EULA. Where the binaries carry different terms from the source, record both |
| S8 | **Fit** | Required | It runs within its host's allocation at a realistic load for **24 hours**, with no out-of-memory kills or restarts | Run it on the target allocation for 24 hours while watching memory and restarts |
| S9 | **Secrets at deploy time** | Required | Its credentials are supplied at deploy time from the secret store, never baked into an image or committed to a repository | Deploy it with the credentials injected, and search the built artifact for secrets |
| S10 | **Observable** | Preferred | Its logs and health can reach the site's log store or monitoring | Find its logs in the log store after the S8 run |

**Where these came from.** S6 is MinIO, whose community edition was archived while in use
([ADR-0026](/docs/architecture/decisions/0026-object-storage/)). S7 is VerneMQ, whose upstream
binaries carry an EULA, so it is built from source
([CHG-0015](/docs/changes/2026/0015-vernemq-broker/)). S9 is the build secrets that used to sit on
disk ([CHG-0026](/docs/changes/2026/0026-build-secrets/)).

---

## Process

1. **Open the record.** Create the item if it's new, and a revision page for the line, with the
   verdict *Under evaluation*.
2. **Evaluate off the site first.** Test in a throwaway environment where one can be built, as
   the change records do before applying. Record anything that could only be tested on the site
   as such.
3. **Record the evidence.** For each criterion: the result, what was tested, how, and what was seen.
4. **Set the verdict.** The operator decides. *Approved with conditions* names each Required criterion
   it misses or couldn't test, and what would clear it.
5. **Update the item page**: the approved lines, and the new row in its revisions table.
6. **Deploy through change management.** The change that moves to the line cites the evaluation,
   and updates the [Software Catalog](/docs/platforms/software-catalog/).

A rejected line is kept like an approved one. The next evaluation starts from what is already known.
