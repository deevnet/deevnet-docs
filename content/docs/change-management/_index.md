---
title: "Change Management & CI/CD"
weight: 7
bookCollapseSection: true
---

# Change Management, Automated Testing, and CI/CD

Defines how **change is introduced safely** into the Deevnet ecosystem.

## Scope

This section includes:
- Change classification (routine vs disruptive)
- Required validation before changes are applied
- Automated testing expectations by layer
- CI/CD pipeline responsibilities
- Guardrails that prevent unsafe changes from reaching production substrates

Automated testing and CI/CD exist to:
- validate assumptions early,
- prevent regressions,
- and ensure changes preserve correctness.

Manual changes without validation are considered defects.
