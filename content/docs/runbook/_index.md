---
title: "📋 Operational Runbook"
weight: 5
bookCollapseSection: true
---

# Operational Runbook

Step-by-step procedures, in two halves that are written for two different readers.

<div class="section-cards">
  <a class="section-card" href="substrate/">
    <h3>Substrate Operations</h3>
    <p>For the operator: building and recovering the platform, keeping it current, the network, and admitting tenants.</p>
  </a>
  <a class="section-card" href="tenant/">
    <h3>Tenant Operations</h3>
    <p>For whoever is building on Deevnet: getting a tenant, using each service, and running it day to day.</p>
  </a>
</div>

The split follows the [architecture](/docs/architecture/): the substrate is run by the operator
through Ansible, and a tenant is run by its owner through Terraform against the Deevnet API. Nothing
in the tenant half needs substrate credentials, and nothing in the substrate half creates tenant
content.

How change and incidents are handled on either side is under
[Policies & Procedures](/docs/policies/).
