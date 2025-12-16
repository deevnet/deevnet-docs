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
4. **Platforms & Tooling** - Hardware/software platform decisions with rationale
5. **Security & Vulnerability Management** - Trust boundaries, credential management, security posture
6. **Inventory & Lifecycle Management** - Asset tracking, hardware lifecycle stages
7. **Change Management, Testing, CI/CD** - How change is introduced safely
8. **Platforms Integration** - How docs integrate into developer workflow

## Usage by Other Repos

Other Deevnet repositories include this as a Git submodule at `docs/deevnet/` and reference standards by version.
