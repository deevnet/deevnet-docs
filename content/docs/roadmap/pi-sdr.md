---
title: "Pi-SDR"
weight: 2
tasks_completed: 7
tasks_in_progress: 1
tasks_planned: 1
---

# Pi-SDR Project

Software Defined Radio on Raspberry Pi with CaribouLite support.

Part of `deevnet-image-factory`.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Scope

Deploy a software-defined radio platform using CaribouLite HAT on Raspberry Pi for RF signal monitoring and experimentation.

**In Scope**
- CaribouLite SDR hardware integration
- Remote SDR access via network streaming
- Client software for tuning and visualization
- Baked image via deevnet-image-factory

**Out of Scope**
- Transmit capability
- Signal decoding/demodulation pipelines

---

## Requirements ✅

- ✅ Define supported frequency ranges
- ✅ Define network streaming protocol

---

## CaribouLite Backend ✅

Get CaribouLite SDR hardware working on Raspberry Pi.

- ✅ Base Pi image with ansible support
- ✅ CaribouLite driver installation
- ✅ Post-image configuration tweaks
- ✅ Build documentation

---

## SDR Client 🔄

Configure remote client to tune Pi SDR.

- 🔄 GQRX or alternative front-end setup
- ✅ Network streaming configuration
- ⏳ Client documentation
