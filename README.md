## Shared Documentation for the Deevnet Infrastrure Ecosystem

### Purpose
`deevnet-docs` is the **authoritative documentation repository** for the Deevnet ecosystem.

It exists to capture:
- shared standards,
- architectural intent,
- correctness definitions,
- roadmaps,
- platform and tooling decisions,
- and operational policies

that apply **across all Deevnet repositories**.

This repository defines **what Deevnet is**, **how it is meant to work**, and **what “correct” means**, independent of any single implementation.

---

## Scope

This repository contains documentation that is:
- **cross-cutting** (applies to multiple projects),
- **normative** (defines expectations and contracts),
- **stable over time**, but
- **explicitly versioned** when meaning changes.

Implementation details live in their respective repositories.  
This repository defines the **rules, intent, and constraints** of the system.

---

## Document Domains

### 1. Standards
Defines **non-negotiable rules** that all Deevnet projects must follow.

Includes:
- Naming conventions
- Infrastructure correctness definitions
- Versioned standards contracts

If a project conflicts with standards, **standards win**.

---

### 2. Architecture
Describes **system-level design intent** and contracts between layers.

Includes:
- Substrate and tenant models
- Network contracts and authority boundaries
- Assumptions between collections (network, builder, image factory, etc.)

Architecture documents explain **why** things are shaped the way they are.

---

### 3. Roadmap
Captures **forward-looking intent** that is shared across projects.

Includes:
- Platform-level roadmap
- Collection-specific roadmaps
- Phased evolution plans

Roadmaps are **informational**, not binding contracts.

---

### 4. Platforms & Tooling
Documents **hardware and software platform decisions**, including rationale and trade-offs.

Includes:
- Operating system choices (e.g., why Fedora)
- Network platforms (e.g., why OPNsense)
- Virtualization platforms (e.g., why Proxmox)
- Toolchain selections (Ansible, Terraform, Packer, etc.)
- Criteria for adopting or rejecting technologies

This section answers the question:
> “Why did we choose this, and under what conditions would we change it?”

---

### 5. Security & Vulnerability Management
Documents **security posture, assumptions, and lifecycle practices**.

Includes:
- Trust boundaries and threat assumptions
- Credential and key management philosophy
- Vulnerability monitoring and response expectations
- Patch and upgrade responsibility by layer
- Security-related guardrails and invariants

This section defines what “secure enough” means for Deevnet.

---

### 6. Inventory & Lifecycle Management
Documents how **infrastructure assets are tracked, managed, and retired**.

Includes:
- Host identity and inventory sources of truth
- Hardware lifecycle stages (active, standby, retired)
- Image and configuration lifecycle expectations
- Decommissioning and cleanup principles

This section ensures infrastructure ages intentionally, not accidentally.

---

### 7. Platforms Integration & Tooling
Documents how documentation and standards integrate into the developer workflow.

Includes:
- Submodule usage conventions
- Local AI tooling visibility and context
- Repo bootstrapping expectations
- Documentation discoverability requirements

This section ensures documentation is **present and usable**, not ornamental.

---

## How Other Repositories Use This Repo

Other Deevnet repositories are expected to:
- include `deevnet-docs` as a Git submodule at a consistent path (e.g. `docs/deevnet/`)
- reference standards explicitly (including version)
- avoid duplicating canonical documents

Each repo may include a small local `STANDARDS.md` or `DOCS.md` that points back to this repository.

---

## Versioning

- Standards are versioned explicitly
- Architectural documents evolve with clear intent
- Roadmaps and platform rationale are expected to evolve over time

Repositories should declare which **standards version** they conform to.

---

## Design Philosophy

This repository exists to:
- make rebuilds boring,
- make intent explicit,
- prevent knowledge from living only in someone’s head,
- and ensure future changes remain coherent.

If something “works” but violates these documents, it is considered **incorrect**.

---

## Audience

This repository is written for:
- future maintainers,
- collaborators,
- automated tooling,
- and AI-assisted workflows.

Clarity, explicitness, and stability are valued over cleverness.

---
