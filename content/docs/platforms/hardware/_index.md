---
title: "Hardware"
aliases:
  - /docs/hardware/
weight: 1
bookCollapseSection: true
---

# Hardware

The physical boxes the mobile site runs on: one page per model, with its specs, why it was chosen,
which hosts it is, how it is cabled and powered, how to reach its console, and whether it has
been evaluated. How each box is configured for its role is on the role pages that follow in
[Implementation & Tooling](/docs/platforms/), and every firmware and software version is in the
[Software Catalog](/docs/platforms/software-catalog/).

Serial numbers and service tags are deliberately not published here.

---

## Inventory

| Model | Role | Qty | Hosts | Switch port |
|---|---|---|---|---|
| [GL-iNet GL-AXT1800 Slate AX](network/gl-inet-slate-ax/) | Edge router | 1 | `dv02edg001p01` | none (upstream of the core router) |
| [ZimaBoard 832](network/zimaboard-832/) | Core router | 1 | `dv02cor002p01` | `gi1/0/1` |
| [TP-Link Omada SG2218](network/tp-link-sg2218/) | Access switch | 1 | `dv02acc001p01` | — |
| [TP-Link Omada EAP650-Outdoor](network/tp-link-eap650-outdoor/) | Wireless access point | 1 | `dv02wap001p01` | `gi1/0/4` |
| [AOOSTAR N1 PRO](compute/aoostar-n1-pro/) | Builder | 1 | `dv00bld001p01` | `gi1/0/16` |
| [Dell OptiPlex 7050 Micro](compute/dell-optiplex-7050-mff/) | Management hypervisor | 1 | `dv02hyp001p01` | `gi1/0/15` |
| [Dell OptiPlex 7060 Micro](compute/dell-optiplex-7060-mff/) | Tenant hypervisor | 1 | `dv02hyp002p02` | `gi1/0/13` |
| [Raspberry Pi 4 Model B](compute/raspberry-pi-4/) | Pi bank | 4 | `dv02rpi001p01` to `dv02rpi004p01` | `gi1/0/3`, `gi1/0/5`, `gi1/0/14` |

The full switch port map is on the [SG2218](network/tp-link-sg2218/#port-map) page.

---

## Evaluation

Each model page is also its evaluation record: its current verdict, and the evaluations behind it.
The criteria are in the
[Hardware Evaluation](/docs/policies/lifecycle-management/evaluation/hardware-evaluation/)
policy. Everything above predates the policy and is
{{< status-badge "planned" "Not yet evaluated" >}}. Candidates not yet in service are under
[Evaluations](/docs/platforms/evaluations/).
