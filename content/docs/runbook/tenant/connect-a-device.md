---
title: "Connect a Device to the IoT SSID"
weight: 6
aliases: ["/docs/runbook/tenant/project-kits/"]
---

# Connect a Device to the IoT SSID

Any Wi-Fi board you flash, such as a Pico W or an ESP32, joins the site's **IoT SSID** with your
tenant's Wi-Fi key. It makes no difference whether the device is your own or a pre-wired kit
borrowed at a meetup (CARPE keeps those on its
[Example Project Kits](https://carpe-tech.org/hands-on/project-kits/) page): once your key is on
it, it is one of your devices.

This page covers only getting the device onto the network. Talking to the broker comes after, in
[Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/), and the
[walkthrough](/docs/runbook/tenant/walkthrough-mqtt-device/) does both end to end.

## Where the device lands

| | At the mobile site |
|---|---|
| SSID | `DVNTM-IOT`, on 2.4 GHz and 5 GHz; a 2.4 GHz-only board such as the Pico W or ESP32 joins on 2.4 |
| Network | the IoT network, VLAN 30, `10.20.30.0/24` |
| Address | DHCP, from `10.20.30.100` to `10.20.30.200` |
| Can reach | the MQTT broker and the internet, nothing else |

The SSID is shared by every tenant. The **key** is yours, and it is what makes the device one of
yours ([Wi-Fi Keys](/docs/runbook/tenant/services/wifi-keys/)).

## 1. Get your tenant's key

One key per tenant covers all your devices. If you already have one, reuse it.

```hcl
resource "deevnet_iot_wifi_key" "devices" {
  tenant      = deevnet_tenant.this.name
  name        = "devices"
  trust_class = "iot"
}

output "device_wifi" {
  value     = { ssid = deevnet_iot_wifi_key.devices.ssid, psk = deevnet_iot_wifi_key.devices.psk }
  sensitive = true
}
```

```bash
terraform apply
terraform output -json device_wifi
```

Take the SSID from the output too, rather than typing `DVNTM-IOT`: another site names its IoT SSID
differently.

## 2. Put it on the device

Keep the key in a file of its own beside your code, and keep that file out of git.

**Pico W, MicroPython.** A `secrets.py` on the board:

```python
SSID = "<device_wifi.ssid>"
PSK  = "<device_wifi.psk>"
```

and in `main.py`:

```python
import network, time
from secrets import SSID, PSK

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PSK)
while not wlan.isconnected():
    time.sleep(0.5)
print("on Wi-Fi:", wlan.ifconfig()[0])
```

**ESP32, Arduino.** A `secrets.h` beside the sketch:

```cpp
#define WIFI_SSID "<device_wifi.ssid>"
#define WIFI_PSK  "<device_wifi.psk>"
```

and in the sketch:

```cpp
#include <WiFi.h>
#include "secrets.h"

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PSK);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.print("on Wi-Fi: ");
  Serial.println(WiFi.localIP());
}

void loop() {}
```

A borrowed kit's own instructions say where its firmware expects the key. The idea is the same.

## 3. Check it joined

Watch the serial console. The device should print an address between `10.20.30.100` and
`10.20.30.200`. If it does, the device is on your tenant's key, and the next step is a broker
account: [Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/).

## When it doesn't join

- **It never connects.** The key or SSID is wrong. Copy both from `terraform output` again, and
  check nothing was trimmed or quoted twice
- **The board has no Wi-Fi.** A plain Pico, like the one in CARPE's starter kit, has no radio;
  only a Pico W (or another Wi-Fi board) can join
- **It joins but can't reach the broker.** That's past Wi-Fi: the broker needs its own account,
  and TLS needs the site CA ([Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/))
- **It stopped working after a key rotation.** Rotating the key drops **every** device holding the
  old one, until each is reflashed ([Wi-Fi Keys](/docs/runbook/tenant/services/wifi-keys/#rotating-it))

## Handing back a borrowed device

Your Wi-Fi key is shared by all your devices, so don't rotate it to return one kit. Instead:

1. **Wipe the key** from the device: delete `secrets.py`, or reflash the kit's reference firmware
2. **Remove its broker account** from your Terraform and `terraform apply`, if you gave it one

Removing the broker account blocks the device's *next* connection, not the one already open, so
power-cycle it too.
