---
title: "MaBell Bluetooth Gateway: Project Plan"
linkTitle: "Project Plan"
bookCollapseSection: true
aliases:
  - /docs/projects/mabell/
  - /projects/mabell/
weight: 17
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

Each stage is a version, on its own page. A version's definition of done and its tasks are written
when it becomes current; until then its page sketches its scope. The line interface for the circuit
board, the AG1171 SLIC module or the discrete HC-5504B SLIC, is chosen at the end of v3, with what
the prototypes taught, and recorded with the options considered in the project's design docs.

---

## Versions

| Version | Goal | Status |
|---|---|---|
| [v0: Foundation](/docs/roadmap/mabell/plan/v0/) | Requirements, design and the first firmware: the base every prototype builds on | Done |
| [v1: On the bench](/docs/roadmap/mabell/plan/v1/) | Every functional section proven on a breadboard, with stand-ins for the phone | Current |
| [v2: A low-voltage phone](/docs/roadmap/mabell/plan/v2/) | A real telephone on a 5V loop | Next |
| [v3: Line voltage and a real bell](/docs/roadmap/mabell/plan/v3/) | A vintage rotary phone at line voltage; the board's line interface chosen | Planned |
| [v4: Boxed and installed](/docs/roadmap/mabell/plan/v4/) | The gateway on its own circuit board, in an enclosure, installed at home | Planned |

---

## Vision & Scope

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

## Later

Ideas kept for after v4, or for whichever version needs them:

- The rarer tones (SIT, stutter dial tone, call waiting)
- Field diagnostics beyond the MQTT state and the event log
