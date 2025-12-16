---
title: "Correctness"
weight: 1
---

# Deevnet Infrastructure Correctness

### Purpose
This document defines what it means for **Deevnet infrastructure to be correct**.

Correctness is not defined by whether something “works once,” but whether it:
- is deterministic,
- is reproducible,
- respects separation of concerns,
- and remains understandable months later.

This document captures the **intent, principles, and invariants** of Deevnet infrastructure design.

---

## 1. Foundational Principles

### 1.1 Determinism Over Convenience
Infrastructure behavior MUST be deterministic.

- Hosts have stable identities (MAC → IP → DNS)
- Provisioning does not depend on timing, luck, or manual intervention
- Re-running automation yields the same result

Anything that “usually works” but cannot be proven deterministic is considered incorrect.

---

### 1.2 Names Over Addresses
IP addresses are implementation details.

- All provisioning, bootstrap, and integration flows MUST use DNS names
- Hard-coded IPs in Kickstart, PXE, scripts, or configs are considered defects
- DNS names express intent; IPs express plumbing

Correct infrastructure can survive IP changes without rewriting logic.

---

### 1.3 Separation of Concerns
Each layer has a clear responsibility:

- **Network (deevnet.network)**  
  Defines substrate topology, identity, DHCP/DNS, and provisioning readiness.
- **Builder / Bootstrap (deevnet.builder)**  
  Provides artifact hosting, PXE/TFTP, and tooling — but does not define topology.
- **Image Factory (deevnet-image-factory)**  
  Builds OS images only; assumes the network contract is already satisfied.
- **Tenants / Applications**  
  Consume infrastructure; do not define it.

Any component that “reaches across layers” is incorrect.

---

## 2. Substrate Model Correctness

### 2.1 Substrates Are Physical/Logical Environments
Substrates (e.g., `dvnt`, `dvntm`) represent **where** things run, not **what** runs.

- Each substrate has its own IP space
- Each substrate has its own routing/security boundary
- Each substrate may have its own OPNsense instance
- Substrates may be separate VLANs or separate physical networks

Mixing workload identity into substrate naming is incorrect.

---

### 2.2 Substrate Independence
Each substrate MUST be operable independently.

- dvnt and dvntm can be brought up, torn down, or rebuilt independently
- Provisioning in one substrate must not implicitly depend on the other
- Shared global aliases (e.g., `artifacts.deevnet.net`) must be explicit and controlled

---

## 3. Identity and Addressing Correctness

### 3.1 Host Identity Is Declarative
Hosts typically have multiple network interfaces (e.g., wired Ethernet, WiFi, management/IPMI, virtual bridges). Each interface has its own identity chain:

- MAC address (L2 identity, per interface)
- Assigned IP (L3 identity, per interface)
- DNS name (human/contract identity, per interface)

A host's **canonical identity** is the name used to refer to the host as a logical unit (e.g., `node01.dvnt.deevnet.net`). Individual interfaces are named to reflect their role:

- `node01.dvnt.deevnet.net` — canonical host identity (typically the primary interface)
- `node01-mgmt.dvnt.deevnet.net` — management/IPMI interface
- `node01-stor.dvnt.deevnet.net` — storage network interface

All interface-to-identity mappings are **Config-as-Code**, version-controlled, and auditable.

If identity exists in more than one place, correctness is violated.

---

### 3.2 Hosts vs Services
Hosts and services are distinct concepts.

- Hosts are physical or virtual machines
- Services are logical endpoints that may move between hosts

Correct infrastructure:
- Resolves hosts via A/AAAA records
- Resolves services via CNAMEs (or equivalent abstraction)

Binding a service permanently to a host name is incorrect.

---

### 3.3 Multihoming (Service Co-location)
A single host may run multiple logical services. This is called **multihoming**.

Example: `build-01.dvntm.deevnet.net` hosts:
- `artifacts.dvntm.deevnet.net`
- `pxe.dvntm.deevnet.net`
- `dns.dvntm.deevnet.net`

#### Naming Rule
Each service MUST have its own DNS name (CNAME → host A record). Consumers address services by service name, never by host name.

Host identity and service identity remain separate—this is what allows services to move.

#### Blast Radius Awareness
Co-located services share a failure domain:
- Host failure = all co-located services fail simultaneously
- Host maintenance = all co-located services unavailable

Co-location relationships MUST be documented in config-as-code inventory. Implicit or undocumented co-location is incorrect.

#### When Multihoming Is Appropriate
- Resource-constrained environments (lab, mobile substrate)
- Non-critical or tightly-coupled services
- Services with similar security posture and trust level

#### When Multihoming Should Be Avoided
- Services with different trust levels (e.g., public-facing alongside internal secrets)
- Services where isolation is a hard requirement
- When the combined blast radius is unacceptable

#### Correctness Invariant
Service names MUST remain stable regardless of co-location decisions.

- Moving a service from a shared host to a dedicated host = DNS record change only
- If moving a service requires consumer changes, correctness is violated

---

## 4. DNS and Naming Correctness

### 4.1 DNS Is the Contract
DNS is the primary contract between infrastructure layers.

- Provisioning tools assume DNS works
- Kickstart assumes DNS works
- Automation assumes DNS works

If DNS is wrong, everything else is wrong.

---

### 4.2 Substrate-Scoped Names Are Mandatory
Every infrastructure service MUST have a substrate-scoped name:

- `artifacts.dvnt.deevnet.net`
- `artifacts.dvntm.deevnet.net`

Global aliases are optional but must never replace substrate-scoped truth.

---

### 4.3 Global Aliases Are Explicit
If a global alias (e.g., `artifacts.deevnet.net`) exists:

- It MUST be controlled by automation
- It MUST be intentionally switched
- It MUST be validated before use

Silent alias drift is incorrect.

---

## 5. Provisioning Correctness

### 5.1 Provisioning Is a Contracted Workflow
Provisioning assumes the following are true **before** it starts:

- DNS resolves required service names
- DHCP reservations match expected MAC → IP mappings
- Artifact endpoints are reachable
- PXE options (if used) are correct

Provisioning workflows must never “figure this out on the fly.”

---

### 5.2 Authority Modes Are Explicit
Provisioning operates in one of two modes:

- **OPNsense-authoritative**
- **Bootstrap-authoritative**

The mode MUST be explicitly declared.
Implicit authority is incorrect.

---

### 5.3 Preflight Validation Is Mandatory
Correct infrastructure supports preflight checks that:

- Validate DNS resolution
- Validate HTTP artifact access
- Validate DHCP reservations
- Fail fast with actionable errors

If you only find out something is wrong *after* PXE boots, correctness has failed.

---

### 5.4 Substrate Provisioning Is Air-Gapped
Substrate hosts MUST be provisionable without upstream internet dependencies.

- All artifacts (Kickstart, PXE, packages) served from local infrastructure
- No fetches from public mirrors, CDNs, or external URLs during install
- External dependencies create non-determinism and single points of failure

Air-gap scope is **substrate only**. Tenants and edge devices may follow different policies.

See [Artifacts Server](/docs/architecture/artifacts-server/) for implementation details.

---

## 6. Tenancy Correctness

### 6.1 Tenants Are Logical, Not Physical
Tenants represent workloads, not networks.

- Tenants live on substrates
- Tenants do not define routing boundaries
- Tenants may be deployed to multiple substrates

Embedding tenant identity into substrate design is incorrect.

---

### 6.2 Tenant Naming Is Explicit
Tenant services are named clearly:

- `<service>.<tenant>.<substrate>.deevnet.net`

This makes placement, ownership, and blast radius obvious.

---

## 7. Automation Correctness

### 7.1 Infrastructure Is Code
All infrastructure state MUST be derivable from code:

- DHCP reservations
- DNS records
- Firewall rules (where applicable)
- Provisioning readiness

Manual configuration is considered temporary at best, incorrect at worst.

---

### 7.2 Idempotency Is Non-Negotiable
Automation must be safely repeatable.

- Re-running playbooks must not cause drift
- No “first run only” magic without explicit guards

---

## 8. Failure Semantics

### 8.1 Fail Loud, Fail Early
Correct infrastructure fails:
- early,
- loudly,
- and with enough context to fix it.

Silent failures, retries without explanation, or “best effort” provisioning are incorrect.

---

## 9. Human Factors (This Matters)

### 9.1 Readability Is a Feature
Infrastructure must be understandable by:
- future you,
- tired you,
- or someone you trust to run it.

If it requires oral tradition, correctness has failed.

---

### 9.2 Debuggability Is Required
A correct system allows you to answer quickly:
- What environment am I in?
- What substrate is authoritative?
- Where should this service resolve?
- Why would provisioning fail?

If those questions require guesswork, correctness is violated.

---

## 10. Definition of “Correct”

Deevnet infrastructure is **correct** when:

- A fresh node can be provisioned deterministically
- No hard-coded IPs exist in provisioning paths
- Network identity is declared once and reused everywhere
- Substrates and tenants are cleanly separated
- DNS expresses intent, not accidents
- Automation can validate readiness before irreversible actions
- Rebuilding a lab is boring

If rebuilding is boring, the infrastructure is correct.

---
