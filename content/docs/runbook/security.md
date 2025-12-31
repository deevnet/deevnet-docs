---
title: "Security"
weight: 4
---

# Security & Vulnerability Management

Documents **security posture, assumptions, and lifecycle practices**.

---

## Scope

This section includes:

- Trust boundaries and threat assumptions
- Credential and key management philosophy
- Vulnerability monitoring and response expectations
- Patch and upgrade responsibility by layer
- Security-related guardrails and invariants

This section defines what "secure enough" means for Deevnet.

---

## Status: Planned

Detailed security documentation is planned. Key areas to document:

### Trust Boundaries

- Substrate network is trusted
- Upstream/WAN is untrusted
- Tenant isolation requirements

### Credential Management

- SSH key distribution via artifact server
- No passwords in playbooks or inventory
- API tokens for service accounts

### Vulnerability Response

- Monitoring sources (CVE feeds, vendor advisories)
- Patch timelines by severity
- Emergency response procedures

---

## See Also

- [Patching](../patching/) - Day 2 update procedures
- [Building & Recovery](../building-recovery/) - Secure provisioning
