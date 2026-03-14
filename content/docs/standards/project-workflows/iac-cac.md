---
title: "IaC/CaC"
weight: 3
---

# IaC/CaC Workflow

Template for Infrastructure as Code and Configuration as Code projects that automate a single system, appliance, or service. Use this for focused automation projects that don't require full site orchestration.

For complex multi-layer infrastructure, see [Site IaC](../site-iac/).

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Define the automation target and goals.

**In Scope**
- Target system or service
- Automation tooling
- Configuration scope
- Deployment target

**Out of Scope**
- Unrelated systems
- Features deferred to future phases

---

## Milestone: Image & Provisioning ⏳

Establish the base system and automation foundation.

| Task | Status |
|------|--------|
| Base image selection or creation | ⏳ |
| Automation tooling setup (role, playbook, module) | ⏳ |
| Target host provisioning | ⏳ |
| Initial connectivity and access validation | ⏳ |

---

## Milestone: Configuration Automation ⏳

Implement the core automation.

| Task | Status |
|------|--------|
| Package and dependency installation | ⏳ |
| Service configuration | ⏳ |
| Integration with external systems | ⏳ |
| Post-configuration validation | ⏳ |
| Idempotency verification | ⏳ |

---

## Milestone: Documentation ⏳

Create documentation for deployment and operation.

| Task | Status |
|------|--------|
| Build/deployment instructions | ⏳ |
| Configuration reference | ⏳ |
| Troubleshooting guide | ⏳ |

---

## Milestone: Operations ⏳

Establish ongoing maintenance approach.

| Task | Status |
|------|--------|
| Update/patching strategy | ⏳ |
| Backup considerations (if applicable) | ⏳ |
| Known issues and workarounds | ⏳ |
