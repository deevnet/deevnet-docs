---
title: "DVNTM Extended Management Plane"
weight: 2
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 33
---

# DVNTM Extended Management Plane

Extended management services for the dvntm (mobile) substrate — logging, telemetry, alerting, secrets, and identity. Builds on the core substrate once it is operational.

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Deploy a unified management plane providing observability, security, and identity services for all substrate components, running as tenants on the Proxmox hypervisor.

**In Scope**
- Centralized logging aggregation and search
- Metrics collection and telemetry
- Alerting and notification
- Secrets management
- Identity and access management
- Ansible automation via `deevnet.mgmt` collection

**Out of Scope**
- Application-specific monitoring (handled per-tenant)
- External identity federation (future phase)
- Multi-substrate federation

---

## Requirements ⏳

- ⏳ Define service selection criteria
- ⏳ Define retention policies (logs, metrics)
- ⏳ Define alerting channels and escalation
- ⏳ Define secrets access policies
- ⏳ Define identity/RBAC model

---

## Centralized Logging ⏳

Aggregate logs from all substrate hosts and services.

- ⏳ Evaluate logging stack (Loki, Elasticsearch, etc.)
- ⏳ Deploy log aggregation service
- ⏳ Configure log shipping from hosts (Promtail, Filebeat, etc.)
- ⏳ Deploy log visualization (Grafana, Kibana)
- ⏳ Define log retention and rotation

---

## Telemetry ⏳

Collect metrics from infrastructure and services.

- ⏳ Evaluate metrics stack (Prometheus, VictoriaMetrics, etc.)
- ⏳ Deploy metrics collection service
- ⏳ Configure exporters on substrate hosts
- ⏳ Deploy dashboards (Grafana)
- ⏳ Define metrics retention

---

## Alerting ⏳

Proactive notification of issues.

- ⏳ Evaluate alerting solutions (Alertmanager, Grafana Alerting)
- ⏳ Deploy alerting service
- ⏳ Define alert rules for infrastructure
- ⏳ Configure notification channels (email, webhook, etc.)

---

## Secrets Management ⏳

Secure storage and distribution of credentials.

- ⏳ Evaluate secrets solutions (Vault, SOPS, etc.)
- ⏳ Deploy secrets management service
- ⏳ Integrate with Ansible for secret injection
- ⏳ Define secrets rotation policies

---

## Identity Management ⏳

Centralized authentication and authorization.

- ⏳ Evaluate identity solutions (Keycloak, Authentik, etc.)
- ⏳ Deploy identity provider
- ⏳ Configure SSO for infrastructure services
- ⏳ Define RBAC policies

---

## Build Verification ⏳

Automated verification that the substrate was built according to inventory and is fully functional. Produces a single report proving build correctness.

- ⏳ Inventory conformance checks (running state matches inventory definitions)
- ⏳ Network connectivity matrix (verify all expected paths work)
- ⏳ Service health checks (DNS, DHCP, PXE, Proxmox API)
- ⏳ Hardware validation (MAC addresses, IP assignments match inventory)
- ⏳ Build report generation (consolidated pass/fail with evidence)

---

## Documentation ⏳

- ⏳ Management plane architecture overview
- ⏳ Service deployment runbook
- ⏳ Operations and troubleshooting guide
