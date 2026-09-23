---
title: "Risk Management"
weight: 3
bookCollapseSection: true
aliases:
  - /docs/runbook/security/
---

# Risk Management

How Deevnet decides what can go wrong, what to do about it, and what to accept. It replaces the
earlier *Security & Vulnerability Management* stub: security is one kind of risk, alongside losing
state, losing a device, and not being able to explain why something is configured the way it is.

Deevnet is a portable lab run by a small team on consumer hardware. The aim is not to eliminate
risk — it is to **know** each risk, choose a treatment deliberately, and write the choice down, so
nothing is a surprise.

---

## The cycle

| Step | What happens | Where it is written |
|---|---|---|
| **Identify** | a risk is noticed — in design, in a change, in an incident, from an advisory | an ADR's consequences, a change record, an incident record |
| **Assess** | how likely, and how bad if it happens | the [risk register](risk-register/) |
| **Treat** | reduce it, transfer it, avoid it, or **accept** it — explicitly | a change record (reduce), an ADR (avoid/accept) |
| **Review** | is the treatment still right? | the register, when a related change or incident lands |

Accepting a risk is a legitimate treatment. Accepting it *silently* is not.

## The areas

<div class="section-cards">
  <a class="section-card" href="vulnerability-management/">
    <h3>Vulnerability Management</h3>
    <p>Tracking CVEs and advisories, checking code before production, and evaluating patches.</p>
  </a>
  <a class="section-card" href="security-controls/">
    <h3>Security Controls</h3>
    <p>Segmentation, tenant isolation, encryption, and how credentials are held.</p>
  </a>
  <a class="section-card" href="traceability/">
    <h3>Traceability</h3>
    <p>How every decision and change can be traced from why, to what, to what happened.</p>
  </a>
  <a class="section-card" href="resiliency/">
    <h3>Resiliency &amp; Limits</h3>
    <p>What the hardware cannot do, the risks that accepts, and what holds it together instead.</p>
  </a>
  <a class="section-card" href="risk-register/">
    <h3>Risk Register</h3>
    <p>The known risks, how each is treated, and the record that owns it.</p>
  </a>
</div>
