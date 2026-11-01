---
title: "Now Playing"
weight: 2
tasks_completed: 9
tasks_in_progress: 0
tasks_planned: 3
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

- ✅ One bus of drivers, one agent; nowplayd arbitrates (EdS ADR-0006, ADR-0007, ADR-0008)
- ✅ iTunes by remote pairing (EdS ADR-0011)
- ✅ Spotify shown and controlled, switched on and off from the console (EdS ADR-0031, ADR-0032, ADR-0051)
- ✅ The turntable, heard through a sound card and named by a recognizer (EdS ADR-0021)
- ✅ Gaps between tracks; paused long enough is idle; a turntable shows no controls (EdS ADR-0024, ADR-0025, ADR-0026)
- ⏳ The turntable heard on both channels (EdS ADR-0048, INC-0004)
- ⏳ MusicBee (EdS ADR-0013)
- ⏳ TIDAL, through Last.fm (EdS ADR-0014)

---

## Naming the record ✅

- ✅ The owner's Discogs collection names the record (EdS ADR-0022)
- ✅ The original album by what is on it; the recognizer's album weighed as an original (EdS ADR-0038, CHG-0043)

---

## Telemetry ✅

- ✅ Calls to outside services counted, a minute at a time (EdS ADR-0027)
- ✅ How each track's album and cover were found, one line a track (EdS ADR-0050)
