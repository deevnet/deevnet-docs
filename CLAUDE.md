# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is the **authoritative documentation repository** for the Deevnet ecosystem. It contains no code—only documentation that defines standards, architecture, and policies that apply across all Deevnet repositories.

## Key Principles

- **Standards are authoritative**: If a project conflicts with standards defined here, standards win
- **Documentation is normative**: Documents define expectations and contracts, not just descriptions
- **Intent over implementation**: This repo defines "what" and "why"; implementation details live in their respective repositories
- **Explicit versioning**: Standards are versioned; repositories should declare which standards version they conform to

## Document Domains

1. **Standards** - Non-negotiable rules (naming conventions, correctness definitions)
2. **Architecture** - System-level design intent and layer contracts
3. **Roadmap** - Forward-looking shared intent (informational, not binding)
4. **Implementation & Tooling** (`platforms/`) - Hardware/software selections, current and under evaluation, with rationale; the Software Catalog; and certification records (`platforms/certification/`, by item, revisions folded beneath). No procedures
5. **Operational Runbook** (`runbook/`) - `substrate/` for the operator (building, lifecycle, network, recovery, tenant admission); `tenant/` for tenants (getting started, services, operating, Pi Lab)
6. **Policies & Procedures** (`policies/`) - Change management, incident management, risk management (vulnerabilities, security controls, traceability, resiliency, risk register), lifecycle management (the stages from selection to retirement, with certification beneath it: the hardware and software process, criteria and record template)
7. **Change / Incident Records** (`changes/`, `incidents/`) - Numbered records
8. **Completed Projects** (`completed/`) - Finished projects, graduated from the Roadmap
9. **Platforms Integration** - How docs integrate into developer workflow

## Usage by Other Repos

Other Deevnet repositories include this as a Git submodule at `docs/deevnet/` and reference standards by version.

## Documentation Guidelines

- **No "See Also" sections**: Cross-references are unstable during active development. Focus on content, not links.
- **Placeholder sections OK**: Create structure with TBD/placeholder content to establish document organization.
- **Versions live in the Software Catalog** (`content/docs/platforms/software-catalog.md`), the system of record. Elsewhere, name the software and link to the catalog instead of stating a version. Keep a version only where the context needs it: change and incident records (what was true at the time), a behaviour tied to a version, a minimum requirement, or a literal value in a procedure (a firmware chain, an image tag). A change that upgrades something updates the catalog.
