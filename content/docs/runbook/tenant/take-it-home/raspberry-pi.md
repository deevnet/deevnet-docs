---
title: "On a Raspberry Pi"
weight: 2
---

# On a Raspberry Pi

**The backend comes as an image you flash to a microSD card, and the card's boot partition carries
your settings.** You need a Raspberry Pi 3, 4, 5 or Zero 2 W (64-bit; a Pi 4 or 5 if you want
dashboards), a card of 8 GB or more, and the Pi image tools in
[Before You Start](/docs/runbook/tenant/getting-started/before-you-start/#tools). At the site, the
image and Pi Imager are in the
[tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#tenant-downloads) `pi/`
and `tools/`; check the image against its `.sha256` before flashing.

## Flash the card

1. In **Raspberry Pi Imager** choose *Use custom* and pick `raspios-bookworm-mobile-pi-backend.img.xz`
   (from the tenant downloads' `pi/`). **Imager 2.x offers no OS customization for a custom image**,
   so skip it: the boot partition does the same job in step 3.
2. Write the card, and leave it in the reader. The boot partition (`bootfs`) opens on your computer.
   **`README.txt`** there is this guide's short version, and stays on the card.
3. **On the boot partition:**
   - **Name your tenant** in `backend.txt`:

     ```
     tenant=bench1
     index=4
     ```

     Use your Deevnet tenant's name and index. With the same index, `LOG_DEVICE_PARTITION` doesn't
     change either. Left empty, the tenant is `pi` with index 1.
   - **Name the card, and give it Wi-Fi** if it won't be on a cable, in the same file:

     ```
     hostname=bench1
     wifi_ssid=YourNetwork
     wifi_psk=YourPassword
     wifi_country=US
     ```

     The card becomes `bench1.local`, and its certificate names it. Set a name at a meetup: two
     cards left unnamed both answer to `raspberrypi.local`. Wi-Fi needs all three lines; the Pi
     keeps its radio off until it has a country. The Wi-Fi password is removed from
     `backend.txt` once it has been applied, because anyone holding the card can read that
     partition.
   - **Create your login, and turn on SSH:**

     ```bash
     cd /Volumes/bootfs                      # macOS; on Linux, wherever bootfs mounted
     touch ssh                               # enables SSH on first boot
     echo "you:$(openssl passwd -6)" > userconf.txt    # asks for the password twice
     ```

     `userconf.txt` is one line, `username:password-hash`. Raspberry Pi OS creates that user on first
     boot and deletes the file. The username is yours to choose, and the image has no user of its
     own. **macOS's own `openssl` can't make that hash** (LibreSSL has no `-6`). Use Homebrew's
     (`brew install openssl`, then `$(brew --prefix openssl)/bin/openssl passwd -6`), or run the
     command on any Linux machine and paste the result.

     **On Windows** the card's `bootfs` appears as a drive, say `E:`. Git for Windows' `openssl` can
     make the hash. In PowerShell, write the file as ASCII, because 5.1's default is UTF-16:

     ```powershell
     New-Item E:\ssh -ItemType File                                   # enables SSH on first boot
     $h = & 'C:\Program Files\Git\usr\bin\openssl.exe' passwd -6     # asks for the password twice
     Set-Content -Encoding Ascii -NoNewline E:\userconf.txt "you:$h`n"
     ```

## How you sign in

**Every option works from the same `userconf.txt` user.** Pick whichever you like:

| | Set up | Signing in |
|---|---|---|
| **Password only** | nothing more | `ssh you@<pi>`, then type the password |
| **A key you already have** | once, after first boot: `ssh-copy-id -i ~/.ssh/id_ed25519.pub you@<pi>` | no password |
| **A new key, just for this Pi** | `ssh-keygen -t ed25519 -f ~/.ssh/my-pi`, then `ssh-copy-id -i ~/.ssh/my-pi.pub you@<pi>` | `ssh -i ~/.ssh/my-pi you@<pi>` |

`ssh-copy-id` asks for the password once, and installs the **public** key for that user on the Pi.
The name at the end of a public key is only a label, so a key made as `alice` works for a Pi user
called `bench1`. Password sign-in stays on in every case. Turning it off
(`PasswordAuthentication no`) is your call once a key works.

If your version of Imager does offer OS customization for the image, you can use it instead of
`userconf.txt`, `ssh` and the Wi-Fi lines. Both routes end the same way.

## First boot

**Boot the Pi where it will live, on a cable or with the Wi-Fi lines above.** This is your own Pi on
your own network; Deevnet's tenant networks themselves are Wi-Fi only. First boot creates your
user, grows the file system and reboots once. Then `tenant2backend` sets the host name, joins the
Wi-Fi, and makes the backend, as on every medium ([Check the backend](/docs/runbook/tenant/take-it-home/check-the-backend/)).

The card is `<hostname>.local` from a computer on the same network (`raspberrypi.local` if you left
`hostname=` empty), or find its address on your router's client list. Each card makes its own SSH
host keys on first boot, so your computer will ask you to accept it once. On a network where the
Pi's MAC has a DHCP reservation, the first boot can still land on a pool address if an older OS on
the same Pi holds the reserved lease. It moves once that lease expires.

## What is different on a Pi

- **Your app's container is built for arm64:** `podman build --platform linux/arm64`.
- **The clock is `fake-hwclock`**, seeded with the build's time, until the network gives the Pi
  the time.
- **Memory.** Grafana wants about 512 MB, and metrics and alerting a few hundred more. With
  everything running, the bucket store included, a Pi uses about 815 MB: a Pi with 2 GB or more
  runs everything, and the bucket store runs only once you add a bucket. On a 512 MB Zero 2 W, run
  MQTT and logs only:
  `sudo systemctl disable --now grafana backend-dashboards vmstorage vminsert vmselect alertmanager ntfy backend-alerting`.

{{< hint info >}}
**On a real Pi, 2026-11-16.** An 8 GB Pi flashed with this image, set up with `userconf.txt` and
`ssh` as above, passed every self-test check. An alert rule exported from Terraform fired and
resolved, read back from ntfy with the phone's login; a bucket key wrote and read its bucket and was
refused another. Not yet tried on hardware: alerts arriving on a phone, Android resolving
`<hostname>.local` (use the Pi's address if it doesn't), and `cert install` on a Deevnet backend.
{{< /hint >}}

Next: [Check the backend](/docs/runbook/tenant/take-it-home/check-the-backend/).
