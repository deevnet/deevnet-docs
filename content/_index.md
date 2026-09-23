---
title: "Deevnet Infrastructure Platform"
type: docs
---

<div class="landing-hero">

# Deevnet Infrastructure Platform

<p class="subtitle"><em>Infrastructure. Automated. Reproducible. Documented.</em></p>

</div>

{{% columns %}}

### Deevnet Mobile (mobile)

<img src="20260210_160235.jpg" alt="Deevnet Mobile kit" style="max-height: 220px; border-radius: 8px; margin-bottom: 0.8rem;" />

**A cloud you can carry.** Set it up on-premise, anywhere, and get:

- **Portable network addressing.** Its address space and DNS zone travel with the case: the same
  addresses and names on the road or at home, with no renumbering.
- **IoT as a Service.** Per-device Wi-Fi keys, scoped MQTT accounts and a device registry, all from
  Terraform. *(in&nbsp;development)*
- **Self-service tenants.** Isolated networks, DNS zones and state storage, from the tenant's own
  code.
- **Works offline.** Builds and rebuilds itself from code, with no internet needed.
- **A bench for its devices.** Prototype embedded hardware right beside the platform.

<small>In the case: router, switch, wireless AP, Proxmox hypervisors, Raspberry Pis, and
breadboards and components.</small>


<--->

### Deevnet Home (home)

<img src="20230509_181137.jpg" alt="Deevnet Home rack" style="max-height: 220px; border-radius: 8px; margin-bottom: 0.8rem;" />

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
    <p>Sites, substrates, tenants, and system-level design intent.</p>
  </a>
  <a class="section-card" href="docs/standards/">
    <h3>Standards</h3>
    <p>Non-negotiable rules for naming, correctness, and identity.</p>
  </a>
  <a class="section-card" href="docs/platforms/">
    <h3>Implementation & Tooling</h3>
    <p>Hardware and software platform decisions with rationale.</p>
  </a>
  <a class="section-card" href="docs/runbook/">
    <h3>Operational Runbook</h3>
    <p>Step-by-step procedures for operating and maintaining infrastructure.</p>
  </a>
  <a class="section-card" href="docs/changes/">
    <h3>Change Records</h3>
    <p>Significant changes, one dated record each — goal, procedure, undo, outcome.</p>
  </a>
  <a class="section-card" href="docs/incidents/">
    <h3>Incident Records</h3>
    <p>What broke, how it was found, why, and what was done so it does not happen again.</p>
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
