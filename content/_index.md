---
title: "Deevnet IoT as a Service"
type: docs
---

<div class="landing-hero">

# Deevnet IoT as a Service

<p class="subtitle"><em>Mobile Factory</em></p>

</div>

<img src="20260210_160235.jpg" alt="The Deevnet Mobile Factory kit" style="max-height: 220px; border-radius: 8px; margin-bottom: 0.8rem;" />

## Why I built this

> I organize the [Columbus Arduino and Raspberry Pi Enthusiasts](https://carpe-tech.org) meetup
> group. I originally built the Mobile Factory to have a portable network for multi-device IoT
> development: something I could carry to a meetup and set up, so a room full of boards, sensors and
> laptops had a network to work on together.
>
> It grew from there into a reference implementation for infrastructure automation. The network, the
> services and the images it runs are all built from code, and the whole thing can be rebuilt from
> scratch.
>
> The mobile Bauer toolkit travels with it, so device components and tools can be brought on site for
> hardware hacks and prototyping.
>
> — Chris Deever

**A cloud you can carry.** The Mobile Factory is a case of hardware that is carried to a site, set up,
and then builds and runs IoT services for the people who use it. A tenant declares what it needs in
its own Terraform and gets:

- **A network for its devices.** Per-device Wi-Fi keys on the IoT network, issued to the tenant, with no
  one touching the controller.
- **MQTT.** Broker accounts scoped to the tenant's own topics, and a registry of its devices.
- **Logs and dashboards.** Its workloads' and devices' logs in a store only it can read, and its own
  Grafana organisation to chart them.
- **Isolated workloads.** Its own network, DNS zone and state storage, rebuilt from its code.

## What makes it a factory

- **It builds everything from code**: its network, its services and the images it runs, and it works
  offline once it is set up.
- **It produces what tenants take away**: the take-home Pi kit, which reproduces the same services on a
  single Raspberry Pi, and the prebuilt provider and tools a developer needs on their own laptop.
- **It travels.** Its address space and DNS zone move with the case, so it is the same factory wherever
  it is set up, with no renumbering.

<small>In the case: router, switch, wireless AP, two Proxmox hypervisors, Raspberry Pis, and a bench
of breadboards and components for prototyping devices.</small>

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
  <a class="section-card" href="docs/policies/">
    <h3>Policies & Procedures</h3>
    <p>Change, incident, risk and lifecycle management, including certification.</p>
  </a>
  <a class="section-card" href="docs/platforms/">
    <h3>Implementation & Tooling</h3>
    <p>Hardware and software selections with rationale, the software catalog, and certifications.</p>
  </a>
  <a class="section-card" href="docs/runbook/">
    <h3>Operational Runbook</h3>
    <p>Step-by-step procedures for operating the factory, and guides for its tenants.</p>
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

## One instance of Deevnet

This site documents the Mobile Factory, the mobile instance of Deevnet. **Architecture, Standards and
Policies** are written for any Deevnet site. **Implementation & Tooling, the Runbook, the records and
the Roadmap** are this instance's. Another site would be its own instance, and would more likely run
a variant of the take-home kit than a factory of its own.

The patterns, automation and documentation are meant to be adaptable: the standards and architecture
can be applied to your own collection of devices and networks.

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
