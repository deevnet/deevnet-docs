---
title: "Builder & Core Services"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/mobile/builder/
weight: 1
value: [rebuild-from-code]
milestones:
  - title: "Build server requirements defined: hardware inventory, network layout and offline artifacts"
    status: done
    date: "2026-01-09"
  - title: "The build server provisions the site's infrastructure from its own Ansible collection, images and offline package mirror"
    value: [rebuild-from-code, works-anywhere]
    status: done
    date: "2025-12-31"
  - title: "The Omada Wi-Fi controller deployed from code on the build server"
    status: done
    date: "2025-12-07"
  - title: "Machines install themselves from the build server over PXE, BIOS and UEFI"
    status: done
    date: "2026-01-10"
  - title: "Hypervisors install unattended from a Proxmox ISO with an embedded answer file"
    status: active
  - title: "Bare-metal inventory and standards documented on a Hugo docs site"
    value: [one-operator]
    status: done
    date: "2026-01-09"
  - title: "Core router, access switch, DNS and DHCP configured from code, with 12 VLANs under a zone firewall policy"
    value: [rebuild-from-code, one-operator]
    status: done
    date: "2026-03-26"
  - title: "Hosts and DNS zones renamed to a scheme that includes the site's code (CHG-0003)"
    value: [works-anywhere]
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

**Project plan:** [Builder & Core Services](/docs/roadmap/infrastructure/substrate/builder/plan/)
