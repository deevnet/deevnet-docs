---
title: "SDR Platform"
weight: 2
tasks_completed: 7
tasks_in_progress: 1
tasks_planned: 1
---

# Pi-SDR Project

Hardware adoption of the CaribouLite SDR HAT — software-defined radio on Raspberry Pi.

Part of `deevnet-image-factory`.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Adopt the CaribouLite SDR HAT hardware and deploy a software-defined radio platform on Raspberry Pi for RF signal monitoring and experimentation.

**In Scope**
- CaribouLite SDR hardware integration
- Remote SDR access via network streaming
- Client software for tuning and visualization
- Baked image via deevnet-image-factory

**Out of Scope**
- Transmit capability
- Signal decoding/demodulation pipelines

---

{{% details "Requirements — Complete" %}}
## Requirements ✅

- ✅ Define supported frequency ranges
- ✅ Define network streaming protocol
{{% /details %}}

---

{{% details "CaribouLite Backend — Complete" %}}
## CaribouLite Backend ✅

Get CaribouLite SDR hardware working on Raspberry Pi.

- ✅ Base Pi image with ansible support
- ✅ CaribouLite driver installation
- ✅ Post-image configuration tweaks
{{% /details %}}

---

## SDR Client 🔄

Configure remote client to tune Pi SDR.

- 🔄 GQRX or alternative front-end setup
- ✅ Network streaming configuration

---

## Documentation ✅

- ✅ Build documentation
- ⏳ Client documentation
