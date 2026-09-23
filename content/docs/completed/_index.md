---
title: "🏁 Completed Projects"
weight: 9
bookCollapseSection: true
aliases:
  - /docs/platforms/tenant-compute/pi-production/
---

# Completed Projects

Projects that have left the [Roadmap](/docs/roadmap/) because they are **done**: built, running on
their own hardware, and documented well enough to rebuild. Each entry records what the project is,
how it is built and checked, and the plan it was delivered against.

The Deevnet side of each project is here; write-ups of these and other projects are on
[my projects page](https://cdeever.github.io/projects/).

---

## Projects

| Project | Hardware | Purpose |
|---------|----------|---------|
| [CaribouLite SDR](cariboulite-sdr/) | Pi 4 8GB + CaribouLite HAT | Software-defined radio receiver |

---

## What "complete" means

A project is complete when:

1. **It rebuilds from code** — its image or configuration is reproducible from its repository
   (for Pi projects, `deevnet-image-factory`)
2. **It proves itself** — its test scripts pass on the hardware it runs on
3. **It runs on its own hardware** — not on a shared bank or a borrowed workload
4. **It is documented here** — hardware, purpose, network position, configuration, and how to
   validate it
5. **Its roadmap page is closed** — every task done or explicitly dropped, and the plan folded into
   its entry here

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
