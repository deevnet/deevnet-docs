---
title: "Voice"
weight: 4
tasks_completed: 7
tasks_in_progress: 0
tasks_planned: 5
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

- ✅ The reSpeaker runs EdS's firmware; a button, then a wake word (EdS ADR-0043)
- ✅ A request sent whole to the workload, written down and made a command (EdS ADR-0042)
- ✅ Only words scribe is sure of are acted on (EdS INC-0001)
- ✅ The music turned down while a request is heard (EdS ADR-0044)
- ⏳ Silence, noise and hum tried through the real model (EdS INC-0001)

---

## Choosing the album 🔄

- ✅ An album asked for by name, played from iTunes' library (EdS ADR-0040)
- ✅ An artist's Nth album, counted in MusicBrainz, the next owned one if not (EdS ADR-0041, ADR-0045)
- ✅ voiced asks eds-inventory (EdS ADR-0047)
- ⏳ Discographies from eds-inventory, and the old library index removed (EdS CHG-0041)
- ⏳ voiced says at start whether it has an index (EdS INC-0003)
- ⏳ Spotify plays an album by name: a demo branch, not yet a decision

---

## Where it runs ⏳

- ⏳ voiced and scribe on the backend Pi, and the reSpeaker moved there (EdS CHG-0042)
