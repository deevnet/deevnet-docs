---
title: "MaBell Bluetooth Gateway: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/mabell/
  - /projects/mabell/
weight: 17
tasks_completed: 21
tasks_in_progress: 2
tasks_planned: 23
---

# MaBell Bluetooth Gateway: Project Plan

Bluetooth Phone Gateway for vintage telephone integration.

*Project implemented in a separate repository.*

- **GitHub:** https://github.com/cdeever/esp32-ma-bell-gateway
- **Documentation:** https://cdeever.github.io/esp32-ma-bell-gateway/

**Roadmap item:** [MaBell Bluetooth Gateway](/docs/roadmap/mabell/)

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
- Manufacturing and selling units: MaBell is built once, for one home

---

## Requirements & Constraints ✅

Define what success means before building.

- ✅ User scenarios (incoming/outgoing calls, edge cases)
- ✅ Functional requirements (FR-xxx)
- ✅ Non-functional requirements (latency, audio quality, reliability)
- ✅ Electrical & mechanical constraints
- ✅ Acceptance criteria for each requirement
- ✅ Risk register (top technical risks + mitigations)

---

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

---

## Firmware Development 🔄

The ESP32 firmware, built first so the prototypes have something to talk to the hardware.

- ✅ ESP32 base firmware & build system
- ✅ Bluetooth HFP profile implementation
- ✅ Call state machine implementation
- ✅ Tone generation (dial tone, ringback, busy, reorder and the other call-progress tones)
- ✅ Configuration storage (NVS schema)
- ✅ Logging & diagnostics
- ✅ Deevnet tenant: gateway state over MQTT, events in the central log store, a Grafana dashboard
- 🔄 Firmware versioning & release tagging

---

## How MaBell is built

MaBell is one unit, built for one home, so it is prototyped in stages rather than through a
manufacturing lifecycle. **Each stage proves every functional section of the gateway** before the
next stage starts: call tones, ringing, hook detection, rotary and touch-tone (DTMF) detection,
call audio, and the indicators. Dial tone, for example, is first heard on a speaker, then injected
into a phone's earpiece and judged for authenticity. Ringing is first an LED and an electronic ring
on the speaker, then a real bell.

The gateway **detects** dialing; it never generates it. The phone, or a stand-in on the bench,
makes the rotary pulses and DTMF tones. The gateway decodes them and asks the cell phone to dial
over Bluetooth HFP.

Each stage is a version. The line interface for the circuit board, the AG1171 SLIC module or the
discrete HC-5504B SLIC, is chosen at the end of the line-voltage stage (v3), with what the
prototypes taught. The decision and the options considered go in the project's design docs.

---

## Versions

### v1, the MVP (current)

The gateway works on the bench with stand-ins: a Bluetooth call runs end to end through a speaker
and microphone, dialed with a bare rotary dial or DTMF from a phone app, and rung with an LED and an
electronic ring.

**Done when:**

- [ ] Each functional section works on the bench with stand-ins: call tones, ringing, hook, rotary detection, DTMF detection, call audio and indicators.
- [ ] The firmware detects rotary pulses and DTMF digits, and dials the collected number over HFP.
- [ ] Dial tone and the call-progress tones are measured against the North American frequencies and cadences, and sound authentic by ear.
- [ ] A full call works: dial out (rotary and DTMF), ring in and answer, talk, hang up.
- [ ] The bench build is written up: a build guide in the gateway repository, and the tone results in the project's design docs.

**Not in v1:** a real phone (v2), line voltage or a real bell (v3), the circuit board (v4).

### v2 (next)

A real phone on a low-voltage loop: a cheap corded phone on a 5V DC loop
([low-voltage build guide](https://github.com/cdeever/esp32-ma-bell-gateway/blob/main/impl/low-voltage-test-rig.md)).
Tones in a real earpiece, the phone's own hook switch, rotary pulses and DTMF detected through the
loop, and handset audio, including the echo the loop brings.

### v3

Line voltage and a real bell: the AG1171/KS0835F SLIC module
([SLIC module build guide](https://github.com/cdeever/esp32-ma-bell-gateway/blob/main/impl/slic-module-build-guide.md)),
with the phone side on screw terminals or a protoboard, so a vintage rotary phone rings and works.
The firmware inverts the module's hook signal and toggles F/R at 20 Hz to ring, with ring-trip on
answer. A discrete HC-5504B SLIC and LT1684 ring generator build is optional. The version closes
with the line-interface decision for the board.

### v4

MaBell boxed and installed: KiCad schematic and layout, circuit board revisions (Rev A, B…) until
one is electrically verified, the enclosure, and the unit installed at home and in daily use.

### Later

- The rarer tones (SIT, stutter dial tone, call waiting), if no earlier version needs them
- Field diagnostics beyond the MQTT state and the event log

---

## v1: Bench Setup ⏳

Sub-Assembly A from the
[prototyping build guide](https://github.com/cdeever/esp32-ma-bell-gateway/blob/main/impl/prototyping-build-guide.md),
with a speaker, microphone, LEDs, buttons and a bare rotary dial as stand-ins for the phone.

- ⏳ Order the parts: Sub-A, speaker amplifier and speaker, electret microphone, LEDs, buttons, a bare rotary dial
- ⏳ Build Sub-A (ESP32 + PCM5100 DAC + PCM1808 ADC on I2S) and pass its test points
- ⏳ Wire the speaker to the DAC and the microphone to the ADC
- ⏳ Resolve the GPIO 21 clash in the firmware's pin map (I2C SDA and an AEC line)

---

## v1: Call Tones ⏳

- ⏳ Dial tone plays on the speaker when the hook stand-in goes off-hook
- ⏳ Each call-progress tone measured (frequencies, cadence) against the North American values
- ⏳ Each tone judged authentic by ear

---

## v1: Ringing ⏳

- ⏳ An incoming Bluetooth call flashes the ring LED and plays an electronic ring on the speaker, 2s on / 4s off
- ⏳ Going off-hook during ringing stops the ring and answers the call

---

## v1: Hook Detection ⏳

- ⏳ A toggle switch on GPIO 32 stands in for the hook switch, debounced in firmware
- ⏳ Hook state shows in the web interface and the event log

---

## v1: Rotary Dial Detection ⏳

- ⏳ Firmware pulse decoder: counts loop breaks, splits digits on the inter-digit gap, debounces
- ⏳ A bare rotary dial on GPIO 34 decodes every digit, 1 through 0

---

## v1: Touch-Tone (DTMF) Detection ⏳

- ⏳ Firmware Goertzel DTMF detector on the ADC audio
- ⏳ DTMF from a phone app into the microphone decodes 0–9, * and #

---

## v1: Dialing to a Call ⏳

- ⏳ End-of-dialing timeout, then the collected number is dialed over HFP
- ⏳ Ringback plays until the far end answers, then the call connects
- ⏳ Digits dialed during a call are passed to the cell phone (`esp_hf_client_send_dtmf`)

---

## v1: Call Audio ⏳

- ⏳ Two-way Bluetooth call audio through the speaker and microphone

---

## v1: Indicators ⏳

- ⏳ Dial lamp LED (GPIO 27), status LED (GPIO 2), UI LED (GPIO 18)
- ⏳ User button (GPIO 4) triggers its action

---

## v1: Documentation ⏳

- ⏳ Bench build guide in the gateway repository (`impl/`), drawing on Sub-A, the speaker-and-microphone option and the stand-in modules in the low-voltage guide
- ⏳ Tone results in the project's design docs
