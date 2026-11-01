---
title: "Builder & Core Services"
aliases:
  - /docs/roadmap/infrastructure/mobile/builder/
weight: 1
milestones:
  - title: "Builder requirements defined: hardware inventory, network layout and offline artifacts"
    status: done
    date: "2026-01-09"
  - title: "The Builder provisions the substrate from its own Ansible collection, images and offline package mirror"
    status: done
    date: "2025-12-31"
  - title: "The Omada controller deployed from code on the Builder"
    status: done
    date: "2025-12-07"
  - title: "Nodes install themselves from the Builder over PXE, BIOS and UEFI"
    status: done
    date: "2026-01-10"
  - title: "Hypervisors install unattended from a Proxmox ISO with an embedded answer file"
    status: active
  - title: "Bare-metal inventory and standards documented on a Hugo docs site"
    status: done
    date: "2026-01-09"
  - title: "Core router, access switch, DNS and DHCP configured from code, with 12 VLANs under a zone firewall policy"
    status: done
    date: "2026-03-26"
  - title: "Hosts and zones renamed to the site-coded scheme (CHG-0003)"
    status: done
    date: "2026-09-05"
---

# Builder & Core Services 🔄

Builder infrastructure, network automation, and core services required to provision and rebuild the mobile (mobile) site from bare metal.

- **GitHub:** https://github.com/deevnet
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Builder & Core Services](/projects/builder/)
