---
title: "Voice"
weight: 4
milestones:
  - title: "EdS's reSpeaker microphone runs its own firmware, listening on a button and then a wake word (EdS ADR-0043)"
    group: "Hearing"
    status: done
    date: "2026-10-24"
  - title: "A spoken request sent whole to EdS's workload, transcribed and made a command (EdS ADR-0042)"
    group: "Hearing"
    status: done
    date: "2026-10-24"
  - title: "Voice control acts only on words its transcription service is sure of (EdS INC-0001)"
    group: "Hearing"
    status: done
    date: "2026-10-24"
  - title: "The music turned down while a voice request is heard (EdS ADR-0044)"
    group: "Hearing"
    status: done
    date: "2026-10-24"
  - title: "Voice transcription tried with silence, noise and hum through the real model (EdS INC-0001)"
    group: "Hearing"
    status: planned
  - title: "An album asked for by voice, by name, plays from iTunes' library (EdS ADR-0040)"
    group: "Choosing the album"
    status: done
    date: "2026-10-23"
  - title: "A voice request for an artist's Nth album, counted in MusicBrainz, plays the next owned one if that one is not owned (EdS ADR-0041, ADR-0045)"
    group: "Choosing the album"
    status: done
    date: "2026-10-24"
  - title: "EdS's voice service asks the music inventory (EdS ADR-0047)"
    group: "Choosing the album"
    status: done
    date: "2026-10-24"
  - title: "Voice control takes discographies from the music inventory, and its old library index is removed (EdS CHG-0041)"
    group: "Choosing the album"
    status: planned
  - title: "EdS's voice service says at start whether it has an index (EdS INC-0003)"
    group: "Choosing the album"
    status: planned
  - title: "Spotify plays an album asked for by voice: a demo branch, not yet a decision"
    group: "Choosing the album"
    status: planned
  - title: "EdS's voice services and microphone moved to the Pi that runs its back end at home (EdS CHG-0042)"
    group: "Where it runs"
    status: planned
---
# Voice

"Hey Jarvis, play …": a reSpeaker hears the request, scribe writes it down, voiced makes it a command.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

A spoken request becomes an album playing, chosen from what the owner has.

**In Scope**
- The reSpeaker's firmware
- voiced and scribe
- Matching requests to the owner's music

**Out of Scope**
- Listening before the wake word: never

---

## Hearing 🔄

{{< milestones group="Hearing" >}}

---

## Choosing the album 🔄

{{< milestones group="Choosing the album" >}}

---

## Where it runs ⏳

{{< milestones group="Where it runs" >}}
