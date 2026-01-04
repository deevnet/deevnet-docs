---
title: "Change Management"
weight: 6
---

# Change Management & CI/CD

Defines how **change is introduced safely** into the Deevnet ecosystem.

---

## Scope

This section includes:

- Change classification (routine vs disruptive)
- Required validation before changes are applied
- Automated testing expectations by layer
- CI/CD pipeline responsibilities
- Guardrails that prevent unsafe changes from reaching production substrates

---

## Principles

Automated testing and CI/CD exist to:

- Validate assumptions early
- Prevent regressions
- Ensure changes preserve correctness

**Manual changes without validation are considered defects.**

---

## Change Classification

| Type | Examples | Validation Required |
|------|----------|-------------------|
| **Routine** | Package updates, config tweaks | Syntax check, dry run |
| **Structural** | New roles, playbook changes | Full test run |
| **Disruptive** | Network changes, storage migration | Staged rollout, backup |

---

## Validation Checklist

Before applying changes:

- [ ] Syntax check passes (`ansible-playbook --syntax-check`)
- [ ] Packer validate passes (for image changes)
- [ ] Dry run shows expected changes (`--check --diff`)
- [ ] Changes committed to version control
- [ ] Rollback plan documented (for disruptive changes)

---

## Status: Planned

CI/CD automation is planned. Current validation is manual.

Future enhancements:

- GitHub Actions for syntax validation
- Automated testing in dvntm substrate
- Promotion workflow (dvntm → dvnt)

