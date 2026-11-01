---
title: "Now Playing"
weight: 2
milestones:
  - title: "Each music source reports on one message bus, and a now-playing service picks what is current (EdS ADR-0006, ADR-0007, ADR-0008)"
    group: "Drivers"
    status: done
    date: "2026-10-10"
  - title: "iTunes added as a now-playing source, by remote pairing (EdS ADR-0011)"
    group: "Drivers"
    status: done
    date: "2026-10-10"
  - title: "Spotify added as a now-playing source and controlled, switched on and off from the EdS console (EdS ADR-0031, ADR-0032, ADR-0051)"
    group: "Drivers"
    status: done
    date: "2026-10-29"
  - title: "The record on the turntable heard through a sound card and identified by a song recognition service (EdS ADR-0021)"
    group: "Drivers"
    status: done
    date: "2026-10-11"
  - title: "Now playing handles gaps between tracks and long pauses, and shows no controls for a turntable (EdS ADR-0024, ADR-0025, ADR-0026)"
    group: "Drivers"
    status: done
    date: "2026-10-12"
  - title: "The turntable's audio captured on both stereo channels (EdS ADR-0048, INC-0004)"
    group: "Drivers"
    status: planned
  - title: "MusicBee added as a now-playing source (EdS ADR-0013)"
    group: "Drivers"
    status: planned
  - title: "TIDAL added as a now-playing source, through Last.fm (EdS ADR-0014)"
    group: "Drivers"
    status: planned
  - title: "The record playing named from the owner's Discogs collection (EdS ADR-0022)"
    group: "Naming the record"
    status: done
    date: "2026-10-12"
  - title: "A track's original album chosen by what is on it, with the song recognition service's album weighed as an original (EdS ADR-0038, CHG-0043)"
    group: "Naming the record"
    status: done
    date: "2026-10-29"
  - title: "Now playing's calls to outside services counted per minute (EdS ADR-0027)"
    group: "Telemetry"
    status: done
    date: "2026-10-12"
  - title: "One line per track recording how its album and cover were found (EdS ADR-0050)"
    group: "Telemetry"
    status: done
    date: "2026-10-27"
---
# Now Playing

Drivers report what each player is doing; nowplayd picks what is current, names its album and finds its cover.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

One contract on the bus for every source, and a record named by what is on it and what the owner owns.

**In Scope**
- Drivers for iTunes, Spotify and the turntable
- Naming the album and finding its cover
- Counting what is asked of outside services

**Out of Scope**
- Holding the owner's music: EdS Music Inventory

---

## Drivers 🔄

{{< milestones group="Drivers" >}}

---

## Naming the record ✅

{{< milestones group="Naming the record" >}}

---

## Telemetry ✅

{{< milestones group="Telemetry" >}}
