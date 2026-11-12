---
title: "🏁 Completed Projects"
weight: 10
bookCollapseSection: true
aliases:
  - /docs/platforms/tenant-compute/pi-production/
---

# Completed Projects

Projects that have left the [Roadmap](/docs/roadmap/) because they are **done**: built from code, in
service, and documented well enough to rebuild. Each entry records what the project is,
how it is built and checked, and links to the plan it was delivered against, kept in the
[archive](/projects/archive/), or to the project's own site.

The Deevnet side of each project is here; write-ups of these and other projects are on
[my projects page](https://cdeever.github.io/projects/).

---

## Projects

| Project | Hardware | Purpose |
|---------|----------|---------|
| [Tenant Removal](tenant-removal/) | None: the Deevnet API and the log store | A tenant delete leaves nothing behind |
| [CaribouLite SDR](cariboulite-sdr/) | Pi 4 8GB + CaribouLite HAT | Software-defined radio receiver |

---

## What "complete" means

**A project is complete when it can be rebuilt, works where it runs, and is written down.** The same
five conditions hold for a device on its own hardware and for a change to the site's software:

1. **It rebuilds from code** — its image, configuration or release is reproducible from its
   repositories (for Pi projects, `deevnet-image-factory`)
2. **It proves itself** — its checks pass where it runs: on its own hardware for a device, on the
   live site for a change to the substrate or its software
3. **It is in service** — a device runs on its own hardware, not on a shared bank or a borrowed
   workload; a change to the site is deployed through its change records, and they are closed
4. **It is documented here** — what it is for, how it is built and how to validate it; for a device,
   also its hardware, network position and configuration
5. **Its project plan is closed** — every task done or explicitly dropped, the plan moved from
   beneath its roadmap item to the [archive](/projects/archive/) with its roadmap item's waypoints, its roadmap item
   removed, and an entry here linking to it

## The path for Pi projects

{{< mermaid >}}
graph LR
    A[Image Factory<br>Build image] --> B[Pi Lab<br>Test & tune] --> C[Dedicated hardware<br>Deploy] --> D[Completed Projects<br>Document]
{{< /mermaid >}}

1. **Image Factory** — build the image with packages, configuration and test scripts
2. **[Pi Lab](/docs/runbook/tenant/pi-lab/)** — flash a bank Pi, boot, validate, iterate until it works
3. **Dedicated hardware** — buy the Pi (and HATs) for the role, move the finished card to it, and
   return the bank Pi to the pool
4. **Document** — add the project's page to this section
