---
title: "ESP32 Ma Bell Bluetooth Gateway"
weight: 4
tasks_completed: 19
tasks_in_progress: 7
tasks_planned: 50
---

# Ma Bell Project

Bluetooth Phone Gateway for vintage telephone integration.

*Project implemented in a separate repository.*

- **GitHub:** https://github.com/cdeever/esp32-ma-bell-gateway
- **Documentation:** https://cdeever.github.io/esp32-ma-bell-gateway/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope 🔄

Restore full, authentic use of vintage analog telephones by bridging them to modern Bluetooth cell phones — preserving rotary dialing, ringing behavior, tones, and user experience.

**In Scope**
- Rotary dial pulse detection
- Authentic ring, dial tone, busy/reorder tones
- Bluetooth HFP call handling
- Use of original phone and ringer hardware

**Out of Scope**
- VoIP provider integration
- Multi-line PBX features
- Smartphone UI replacement

---

{{% details "Requirements & Constraints — Complete" %}}
## Requirements & Constraints ✅

Define what success means before building.

- ✅ User scenarios (incoming/outgoing calls, edge cases)
- ✅ Functional requirements (FR-xxx)
- ✅ Non-functional requirements (latency, audio quality, reliability)
- ✅ Electrical & mechanical constraints
- ✅ Acceptance criteria for each requirement
- ✅ Risk register (top technical risks + mitigations)
{{% /details %}}

---

{{% details "Architecture & Design — Complete" %}}
## Architecture & Design ✅

Translate requirements into a complete system design.

- ✅ System block diagram
- ✅ Power architecture & protection strategy
- ✅ Audio signal chain & gain staging plan
- ✅ Hook switch, dial pulse, and ring detection design
- ✅ Bluetooth integration architecture
- ✅ Firmware architecture & state machine definition
- ✅ Interface specifications (electrical, audio, software)
- ✅ Verification & test plan (requirements → tests mapping)
{{% /details %}}

---

## Low-Voltage Test Rig (EVT-1) 🔄

Safe, breadboard-based simulator for firmware development — no line voltage required.

📄 **Build guide:** [`impl/low-voltage-test-rig.md`](https://github.com/cdeever/esp32-ma-bell-gateway/blob/main/impl/low-voltage-test-rig.md)

- 🔄 Order & collect low-voltage components
- ⏳ Breadboard ESP32 + PCM5100 DAC + PCM1808 ADC
- ⏳ Hook switch simulator (GPIO 32)
- ⏳ Pulse dial simulator (NE555 timer)
- ⏳ Ring indicator & ring detect feedback
- ⏳ Audio I/O validation (I2S wiring)
- ⏳ DTMF tone generator for touch-tone dial simulation
- ⏳ LED & button wiring
- ⏳ Full 24-feature firmware test matrix pass

---

## Firmware Development 🔄

ESP32 firmware implementing telephony behavior and system control.

- ✅ ESP32 base firmware & build system
- ✅ Bluetooth HFP profile implementation
- ✅ Call state machine implementation
- 🔄 Dial tone, ring, busy, reorder tone generation
- 🔄 Rotary pulse detection & validation
- ⏳ DTMF detection (touch-tone phone support)
- ✅ Configuration storage (NVS schema)
- ✅ Logging & diagnostics
- 🔄 Firmware versioning & release tagging
- ⏳ Validate firmware against low-voltage test rig


---

## Full-Voltage Prototype (EVT-2) ⏳

Production-representative prototype with SLIC, ring generator, and real telephone.
Using **KS0835F SLIC module** (AG1171/AG1170 compatible) for the line interface.

📄 **Build guide:** [`impl/prototyping-build-guide.md`](https://github.com/cdeever/esp32-ma-bell-gateway/blob/main/impl/prototyping-build-guide.md)

- ⏳ Sub-A: ESP32 + codec breadboard (3.3V)
- ⏳ Sub-B: KS0835F SLIC module + line interface (mixed voltage)
- ⏳ Sub-C: Ring generator (48V→90V AC)
- ⏳ Power sequencing & safety validation
- ⏳ Integration of all sub-assemblies
- ⏳ Audio path measurements (levels, noise, echo)

---

## Firmware Adjustment (EVT-2 Integration) ⏳

Validate and tune firmware on the full-voltage prototype. Should be largely compatible from EVT-1 testing.

- ⏳ Re-run test matrix against full-voltage hardware
- ⏳ Tune audio gain staging for SLIC signal path
- ⏳ Validate ring-trip and hook detection with real phone

---

## Custom PCB (DVT) ⏳

Transition from prototype to a reproducible hardware design.

- ⏳ Schematic capture
- ⏳ BOM with alternates
- ⏳ PCB layout & DFM/DFA review
- ⏳ Test points & programming header
- ⏳ Fabrication
- ⏳ Assembly
- ⏳ Hardware bring-up checklist
- ⏳ Electrical verification against requirements

---

## Enclosure & Mechanical Integration ⏳

Package the device for real-world use.

- ⏳ Enclosure requirements & constraints
- ⏳ Connector placement & strain relief
- ⏳ Enclosure design (3D print or fabrication)
- ⏳ Thermal and safety considerations
- ⏳ Final mechanical assembly

---

## Verification & Validation ⏳

Prove the system meets its requirements.

- ⏳ Requirements → test traceability
- ⏳ Functional test execution
- ⏳ Audio quality & latency validation
- ⏳ Long-duration stability testing
- ⏳ Regression testing after changes
- ⏳ Issue tracking & resolution

---

## Production Readiness (PVT) ⏳

Prepare the design for repeatable builds.

- ⏳ Assembly documentation
- ⏳ Manufacturing test procedure
- ⏳ Test fixtures / jigs
- ⏳ Calibration & setup process
- ⏳ Revision control (Rev A, Rev B, etc.)

---

## Documentation 🔄

Create durable documentation for users and future builders.

- 🔄 Build instructions
- 🔄 Installation & wiring guide
- 🔄 User guide
- ⏳ Troubleshooting guide
- ⏳ Design notes & lessons learned

---

## Deployment & Operations ⏳

Put the system into real use.

- ⏳ Final integration testing
- ⏳ Installation procedure
- ⏳ Field diagnostics workflow
- ⏳ Release notes
- ⏳ Ongoing maintenance plan
