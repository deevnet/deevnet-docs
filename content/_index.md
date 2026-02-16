---
title: "Deevnet Infrastructure Platform"
type: docs
---

<div class="landing-hero">
  <h1>Deevnet Infrastructure Platform</h1>
  <p class="subtitle">Hardware, automation, and documentation for building reproducible on-premise infrastructure.</p>
</div>

## Two Deployments

{{% columns %}}

### Deevnet Mobile (dvntm)

<img src="dvntm.png" alt="Deevnet Mobile kit" style="max-height: 220px; border-radius: 8px; margin-bottom: 0.8rem;" />

A **portable lab** that packs into a toolkit. Includes:

- Network infrastructure (router, switch, wireless AP)
- Compute nodes (Proxmox hypervisors, Raspberry Pis)
- Breadboards and components for embedded device prototyping
- Full on-premise network that can be set up anywhere

Deevnet Mobile provides a complete, self-contained environment for development, testing, and demos — whether at home, a coffee shop, or a Meetup site.

<--->

### Deevnet Home (dvnt)

<img src="dvnt-home.png" alt="Deevnet Home rack" style="max-height: 220px; border-radius: 8px; margin-bottom: 0.8rem;" />

A **home infrastructure** deployment supporting various functions:

- Permanent compute and storage
- Home automation and IoT backends
- Development and CI/CD environments
- Media and personal services

{{% /columns %}}

---

## Explore the Documentation

<div class="section-cards">
  <a class="section-card" href="docs/architecture/">
    <h3>Architecture</h3>
    <p>Substrates, tenants, and system-level design intent.</p>
  </a>
  <a class="section-card" href="docs/standards/">
    <h3>Standards</h3>
    <p>Non-negotiable rules for naming, correctness, and identity.</p>
  </a>
  <a class="section-card" href="docs/platforms/">
    <h3>Platforms & Tooling</h3>
    <p>Hardware and software platform decisions with rationale.</p>
  </a>
  <a class="section-card" href="docs/runbook/">
    <h3>Operational Runbook</h3>
    <p>Step-by-step procedures for operating and maintaining infrastructure.</p>
  </a>
  <a class="section-card" href="docs/roadmap/">
    <h3>Roadmap</h3>
    <p>Forward-looking project plans and progress tracking.</p>
  </a>
  <a class="section-card" href="docs/github/">
    <h3>Code Repositories</h3>
    <p>GitHub repos, layout, and getting started guides.</p>
  </a>
</div>

---

## Adaptability

While this project targets specific hardware, the patterns, automation, and documentation are designed to be **adaptable to any infrastructure**. The standards and architecture defined here can be applied to your own collection of devices and networks.

---

## Documentation Philosophy

This documentation exists to:
- seed context to AI agent tooling,
- make intent explicit,
- prevent knowledge from living only in someone's head,
- and ensure future changes remain coherent.

{{% hint danger %}}
If something "works" but violates these documents, it is considered **incorrect**.
{{% /hint %}}
