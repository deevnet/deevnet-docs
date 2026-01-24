---
title: "CaribouLite SDR"
weight: 1
---

# CaribouLite SDR

## Purpose

Software-defined radio (SDR) receiver for RF signal monitoring and experimentation. The CaribouLite HAT provides dual-channel SDR capability directly on the Pi's GPIO header.

---

## Hardware

| Component | Specification |
|-----------|---------------|
| **Compute** | Raspberry Pi 4 Model B, 8GB |
| **SDR HAT** | CaribouLite SDR |
| **Storage** | 32GB SD card (minimum) |
| **Antenna** | SMA connector, antenna per use case |

### CaribouLite Specifications

| Attribute | Value |
|-----------|-------|
| **Frequency range** | 30 MHz – 6 GHz (with gaps) |
| **Channels** | 2 (S1000: sub-1GHz, HiF: 30MHz-6GHz) |
| **ADC** | 13-bit |
| **Bandwidth** | Up to 2.5 MHz per channel |
| **Interface** | GPIO header (directly mounted) |

---

## Network Position

{{< mermaid >}}
graph LR
    A[Core Router] <--> B[Access Switch<br>IoT VLAN] <--> C[CaribouLite SDR<br>Pi4 + SDR HAT]
{{< /mermaid >}}

Deployed on the IoT VLAN for isolation from management traffic.

---

## Software Stack

| Layer | Component |
|-------|-----------|
| **OS** | Raspberry Pi OS (64-bit) |
| **SDR Driver** | CaribouLite kernel module |
| **SDR Framework** | SoapySDR |
| **Applications** | GNU Radio, SDR++ (optional GUI) |

---

## Configuration

### Kernel Module

The CaribouLite kernel module loads automatically via udev rules. Verify with:

```bash
lsmod | grep cariboulite
```

### SoapySDR Integration

CaribouLite integrates with SoapySDR for application compatibility:

```bash
SoapySDRUtil --find
SoapySDRUtil --probe="driver=Cariboulite"
```

---

## Test Scripts

Located at `/opt/deevnet/tests/`:

| Script | Purpose |
|--------|---------|
| `test-sdr-detect.sh` | Verify CaribouLite HAT detected |
| `test-sdr-channels.sh` | Confirm both SDR channels operational |
| `test-sdr-receive.sh` | Capture samples, verify data flow |

### Running Tests

```bash
sudo /opt/deevnet/tests/run-all-tests.sh
```

Expected output:
```
[PASS] Network connectivity
[PASS] CaribouLite HAT detected
[PASS] Kernel module loaded
[PASS] SoapySDR integration
[PASS] Channel S1000 operational
[PASS] Channel HiF operational
```

---

## Post-Startup Scripts

Located at `/opt/deevnet/post-startup/`:

| Script | Purpose |
|--------|---------|
| `init-sdr.sh` | Initialize SDR hardware, set default gains |

These run on first boot after the hardware is detected.

---

## Use Cases

| Application | Description |
|-------------|-------------|
| **ADS-B reception** | Aircraft tracking (1090 MHz) |
| **FM broadcast** | Local FM station monitoring |
| **Weather satellite** | NOAA APT reception (137 MHz) |
| **ISM band monitoring** | 433/868/915 MHz IoT traffic |
| **Amateur radio** | HF/VHF/UHF experimentation |

---

## Maintenance

| Task | Frequency | Procedure |
|------|-----------|-----------|
| **Firmware updates** | As released | Check CaribouLite GitHub for updates |
| **Test validation** | Monthly | Run test scripts, verify all pass |
| **Antenna inspection** | Quarterly | Check connections, replace worn cables |
