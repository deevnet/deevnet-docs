---
title: "Pi Production"
weight: 3
bookCollapseSection: true
---

# Pi Production

## Purpose

Pi Production contains **graduated projects**—Raspberry Pi deployments that have moved from development in the [Raspberry Pi Lab]({{< relref "../raspberry-pi-lab" >}}) to permanent, dedicated hardware.

Each production Pi:
- Runs a finalized, tested SD card image
- Has dedicated hardware purchased for its specific role
- Is documented with its configuration, purpose, and maintenance procedures

---

## Lifecycle

Projects follow this path from experiment to production:

{{< mermaid >}}
graph LR
    A[Image Factory<br>Build image] --> B[Pi Lab<br>Test & tune] --> C[Pi Production<br>Deploy]
{{< /mermaid >}}

1. **Image Factory** — Build the base image with packages, configs, and test scripts
2. **Pi Lab** — Flash to a bank Pi, boot, validate, iterate until working
3. **Pi Production** — Purchase dedicated Pi, transfer SD card, document deployment

---

## Production Deployments

| Project | Hardware | Purpose |
|---------|----------|---------|
| [CaribouLite SDR]({{< relref "cariboulite-sdr" >}}) | Pi 4 8GB + CaribouLite HAT | Software-defined radio receiver |

---

## Adding a Production Deployment

When graduating a project from the Lab:

1. **Document the image** — Ensure image factory has complete, reproducible build
2. **Run validation** — All test scripts pass on lab hardware
3. **Purchase hardware** — Buy dedicated Pi (and HATs/accessories if needed)
4. **Create documentation** — Add page to this section with:
   - Hardware specifications
   - Purpose and use case
   - Network position
   - Configuration details
   - Validation procedures
5. **Deploy** — Transfer SD card, verify in production location
