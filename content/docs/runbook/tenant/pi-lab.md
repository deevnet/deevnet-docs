---
title: "Pi Lab"
weight: 5
---

# Pi Lab

The **Raspberry Pi bank** is a shared workbench for projects that need a Pi rather than a VM: edge
compute, SDR, sensors, GPIO, clustering experiments. The hardware and why it was chosen are under
[Raspberry Pi](/docs/platforms/tenant-compute/raspberry-pi/) in Implementation & Tooling; this page
is how to use it.

The idea is **the SD card is the product**. You develop on a bank Pi; when the project works, the
card moves to dedicated hardware and the bank Pi returns to the pool.

---

## Image Factory Integration

All Pi projects start in the **deevnet-image-factory**. The goal is to bake as much configuration as possible into the image itself:

| Layer | What Gets Baked In |
|-------|-------------------|
| **Base image** | Raspberry Pi OS or Fedora ARM |
| **cloud-init** | Network config, users, SSH keys |
| **Packages** | All software dependencies |
| **Configuration** | Service configs, systemd units |
| **Test scripts** | Hardware/software validation scripts |
| **Post-startup scripts** | For hardware-dependent setup (SDR, GPIO, etc.) |

### Test Scripts

Each image includes validation scripts that proof the hardware and software are working as expected:

```
/opt/deevnet/tests/
├── test-network.sh      # Validate connectivity
├── test-services.sh     # Verify services running
├── test-hardware.sh     # Hardware-specific checks (SDR, GPIO)
└── run-all-tests.sh     # Execute full validation suite
```

Run after first boot to confirm the image deployed correctly.

### Post-Startup Scripts

Some configurations require hardware to complete (SDR tuning, GPIO initialization, device calibration). These run on first boot after hardware detection:

```
/opt/deevnet/post-startup/
├── init-sdr.sh          # SDR device initialization
├── init-gpio.sh         # GPIO pin configuration
└── init-sensors.sh      # Sensor calibration
```

---

## Experiments

The 4-Pi bank supports various experiment configurations:

| Configuration | Use Case |
|---------------|----------|
| **4-node K3s cluster** | Lightweight Kubernetes, distributed workloads |
| **3+1 cluster** | 3-node cluster + 1 control/monitoring node |
| **2+2 split** | Two separate 2-node experiments |
| **4 independent** | Four different single-node projects |

### Example Projects

| Project | Description |
|---------|-------------|
| **K3s cluster** | Lightweight Kubernetes for container orchestration |
| **SDR gateway** | Software-defined radio signal processing |
| **Sensor collection** | IoT sensor aggregation and forwarding |
| **Home automation** | Home Assistant or similar platforms |
| **Display/kiosk** | Information displays, dashboards |

SD cards can be swapped to reconfigure the bank for different experiments without rebuilding images.

---

## Workflow

### Development Cycle

1. **Create image** — Build project-specific image in deevnet-image-factory
2. **Bake configuration** — Include packages, configs, test scripts
3. **Flash SD card** — Write image to card
4. **Boot and validate** — Run test scripts to proof the build
5. **Iterate** — Fix issues in image factory, rebuild, re-test
6. **Finalize** — Working SD card is the deliverable

### Permanent Deployment

When a project graduates from the development bank:

1. **Document configuration** — Capture working setup in image factory
2. **Purchase Pi4** — Buy dedicated hardware for permanent role
3. **Transfer SD card** — Move finalized card to new hardware
4. **Reclaim bank slot** — Bank Pi returns to available pool

This model keeps the development bank available for new experiments while completed projects run on dedicated hardware.

---

## Graduating a project

When a project runs unattended on its own hardware, it leaves the bank and gets an entry under
[Completed Projects](/docs/completed/), which also lists what "complete" requires.

{{< hint info >}}
**Pis and tenants.** A bank Pi today sits on the IoT network like any other device, so a Pi project
that talks to a tenant's services does it the way a microcontroller does — a
[Wi-Fi key](/docs/runbook/tenant/services/wifi-keys/) or wired port on the IoT network, and a
[broker account](/docs/runbook/tenant/services/devices-and-mqtt/). Declaring a Pi as a tenant
resource of its own is not built.
{{< /hint >}}
