---
title: "Walkthrough: Device to Backend"
weight: 2
---

# Walkthrough: a Pico W or ESP32 Talking to a Backend

The whole path, end to end: a microcontroller on your bench publishes readings over MQTT, a backend
on a workload receives them and can send commands back, and the device's own log lines land in your
log store.

```
 Pico W / ESP32 ──Wi-Fi (your key)──▶ IoT network ──TLS 8883──▶ MQTT broker ◀──TLS 8883── backend workload
      │                                                             │                     (your tenant network)
      └── publishes bench1/log/<device> ───────────────────────────▶ log bridge ──▶ your log partition (index, 2)
```

The tenant in this walkthrough is called **`bench1`**. Use your own name everywhere you see it.

{{< hint info >}}
**Assumed done:** [admission](/docs/runbook/tenant/getting-started/admission/) and a
[first apply](/docs/runbook/tenant/getting-started/first-apply/), so you have a tenant and
`DEEVNET_API_TOKEN` is your tenant token. You are applying from `DVNTM-TD`
([why](/docs/runbook/tenant/getting-started/before-you-start/#where-you-need-to-sit-on-the-network)).
{{< /hint >}}

---

## 1. Declare it all

Add this to the `main.tf` that already has your `deevnet_tenant.this`:

```hcl
locals {
  devices = ["pico-1", "esp32-1"]
}

# One Wi-Fi key for all of your devices.
resource "deevnet_iot_wifi_key" "devices" {
  tenant      = deevnet_tenant.this.name
  name        = "devices"
  trust_class = "iot"
}

# Each device: an entry in your registry, and a broker account of its own.
resource "deevnet_iot_device" "dev" {
  for_each    = toset(local.devices)
  tenant      = deevnet_tenant.this.name
  name        = each.key
  trust_class = "iot"
}

resource "deevnet_iot_broker_account" "dev" {
  for_each  = toset(local.devices)
  tenant    = deevnet_tenant.this.name
  name      = each.key
  device    = deevnet_iot_device.dev[each.key].name
  publish   = ["sensors/${each.key}/telemetry", "log/${each.key}"]
  subscribe = ["sensors/${each.key}/command"]
}

# The backend: a workload, and its broker account.
resource "deevnet_workload" "backend" {
  tenant = deevnet_tenant.this.name
  name   = "backend"
}

resource "deevnet_iot_broker_account" "backend" {
  tenant    = deevnet_tenant.this.name
  name      = "backend"
  subscribe = ["sensors/+/telemetry"]
  publish   = ["sensors/+/command"]
}

# What you flash, and what the backend needs.
output "flash" {
  sensitive = true
  value = {
    wifi = { ssid = deevnet_iot_wifi_key.devices.ssid, psk = deevnet_iot_wifi_key.devices.psk }
    mqtt = { for d, a in deevnet_iot_broker_account.dev :
      d => { user = a.username, pass = a.password, publish = a.granted_publish } }
  }
}

output "backend" {
  sensitive = true
  value = {
    address = deevnet_workload.backend.address
    user    = deevnet_iot_broker_account.backend.username
    pass    = deevnet_iot_broker_account.backend.password
  }
}
```

```bash
terraform apply
terraform output -json flash
```

Note the **granted** topics in the output: `bench1/sensors/pico-1/telemetry`, not
`sensors/pico-1/telemetry`. The API prefixed your tenant name, and devices publish to the full
topic.

If you only want the device half — say your backend runs somewhere else — drop the workload and the
backend account. A device-only tenant is normal.

## 2. Prepare the CA

Both boards verify the broker's certificate against the site CA:

```bash
# Pico W (MicroPython) wants DER
openssl x509 -in site-ca.pem -outform DER -out site-ca.der
```

The ESP32 takes the PEM text as-is.

---

## 3a. Pico W — MicroPython

Needs MicroPython 1.23 or later (for `ssl.SSLContext`; the site's
[tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#tenant-downloads) has the
Pico W firmware: hold BOOTSEL, plug in, and copy the `.uf2` onto the drive that appears), and
`umqtt.simple` from `mip`:

```python
import mip; mip.install("umqtt.simple")      # once, while on any network with internet
```

Copy `site-ca.der` and this `main.py` to the board, from your laptop with
[`mpremote`](/docs/runbook/tenant/getting-started/before-you-start/#tools) (or Thonny's Files pane):

```bash
mpremote cp site-ca.der main.py :      # then: mpremote reset
```

The `main.py`:

```python
import machine, network, ssl, time, json
from umqtt.simple import MQTTClient

TENANT, DEVICE = "bench1", "pico-1"
SSID, PSK      = "DVNTM-IOT", "<flash.wifi.psk>"
USER, PASS     = "bench1-pico-1", "<flash.mqtt.pico-1.pass>"
BROKER         = "mqtt.mobile.deevnet.net"

wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect(SSID, PSK)
while not wlan.isconnected():
    time.sleep(0.5)

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_verify_locations(cadata=open("site-ca.der", "rb").read())

def on_command(topic, msg):
    print("command:", msg)

c = MQTTClient(f"{TENANT}-{DEVICE}", BROKER, port=8883, user=USER, password=PASS,
               keepalive=60, ssl=ctx)
c.set_callback(on_command)
c.connect()
c.subscribe(f"{TENANT}/sensors/{DEVICE}/command")
c.publish(f"{TENANT}/log/{DEVICE}", json.dumps({"level": "info", "msg": "boot ok"}))

sensor = machine.ADC(4)                        # the RP2040's on-chip temperature sensor
while True:
    volts = sensor.read_u16() * 3.3 / 65535
    temp_c = 27 - (volts - 0.706) / 0.001721
    c.publish(f"{TENANT}/sensors/{DEVICE}/telemetry", json.dumps({"temp_c": round(temp_c, 1)}))
    c.check_msg()                              # deliver any command that arrived
    time.sleep(10)
```

## 3b. ESP32 — Arduino

Needs the ESP32 board package and the **PubSubClient** library (Library Manager). Put the
credentials and the CA in `secrets.h`, beside the sketch, and keep it out of git:

```cpp
// secrets.h
#define WIFI_SSID  "DVNTM-IOT"
#define WIFI_PSK   "<flash.wifi.psk>"
#define MQTT_USER  "bench1-esp32-1"
#define MQTT_PASS  "<flash.mqtt.esp32-1.pass>"
static const char SITE_CA[] = R"PEM(
-----BEGIN CERTIFICATE-----
...paste site-ca.pem here...
-----END CERTIFICATE-----
)PEM";
```

```cpp
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "secrets.h"

const char* TENANT = "bench1";
const char* DEVICE = "esp32-1";
WiFiClientSecure net;
PubSubClient mqtt(net);
String topic(const char* kind) { return String(TENANT) + "/" + kind; }

void onCommand(char* t, byte* payload, unsigned int len) {
  Serial.printf("command: %.*s\n", (int)len, (char*)payload);
}

void connectMqtt() {
  String id = String(TENANT) + "-" + DEVICE;
  while (!mqtt.connect(id.c_str(), MQTT_USER, MQTT_PASS)) {
    Serial.printf("mqtt connect failed, state %d\n", mqtt.state());
    delay(5000);
  }
  mqtt.subscribe(topic("sensors/esp32-1/command").c_str());
  mqtt.publish(topic("log/esp32-1").c_str(), "{\"level\":\"info\",\"msg\":\"boot ok\"}");
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PSK);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  configTime(0, 0, "pool.ntp.org");     // a sane clock for certificate validity checks
  net.setCACert(SITE_CA);
  mqtt.setServer("mqtt.mobile.deevnet.net", 8883);
  mqtt.setCallback(onCommand);
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  static unsigned long last = 0;
  if (millis() - last > 10000) {
    last = millis();
    String body = "{\"rssi\":" + String(WiFi.RSSI()) + "}";
    mqtt.publish(topic("sensors/esp32-1/telemetry").c_str(), body.c_str());
  }
}
```

{{< hint warning >}}
**Both sketches are written against the platform's documented contract, not yet run on these
boards.** The broker, the TLS certificate chain, the topic confinement and the log path have each
been proven with other clients; these exact sketches have not. If one fails, the
[troubleshooting](/docs/runbook/tenant/operating/troubleshooting/#device-side) table is ordered by
how often each cause turns out to be the one — and please tell the operator, so this page can say
"tested".
{{< /hint >}}

---

## 4. The backend

The backend subscribes to every device's telemetry and can publish commands back. The quickest one
is `mosquitto_sub`, on the workload as below, or on your laptop on `DVNTM-TD` with the client tools
from [Tools](/docs/runbook/tenant/getting-started/before-you-start/#tools):

```bash
sudo dnf install -y mosquitto        # the client tools
mosquitto_sub -h mqtt.mobile.deevnet.net -p 8883 --cafile site-ca.pem \
  -u bench1-backend -P '<backend.pass>' -i bench1-backend \
  -t 'bench1/sensors/+/telemetry' -v
```

```text
bench1/sensors/pico-1/telemetry {"temp_c": 24.3}
bench1/sensors/esp32-1/telemetry {"rssi":-58}
```

And a command to one device:

```bash
mosquitto_pub -h mqtt.mobile.deevnet.net -p 8883 --cafile site-ca.pem \
  -u bench1-backend -P '<backend.pass>' -i bench1-backend-cli \
  -t 'bench1/sensors/pico-1/command' -m 'blink'
```

A real backend is the same thing in code — `paho-mqtt` in Python, with `tls_set("site-ca.pem")`,
`username_pw_set(...)`, and a subscription to `bench1/sensors/+/telemetry`.

{{< hint info >}}
**Getting the backend onto the workload goes through the operator today.** Workload SSH keys do not
work yet and code delivery is not built
([Coming soon](/docs/runbook/tenant/services/coming-soon/#code-delivery-to-workloads)). Until then,
the operator installs it for you — at a meetup, that is the `mosquitto_sub` above, run on your
workload by the operator while you watch.
{{< /hint >}}

---

## 5. Check the whole path

| Check | How | Expected |
|---|---|---|
| Device on Wi-Fi | serial console | an address in `10.20.30.0/24` |
| Device on the broker | serial console | no connect error; the backend sees telemetry every 10 s |
| Commands reach the device | `mosquitto_pub` above | the device prints `command: blink` |
| Confinement | change the device's topic to `other/…` | nothing arrives — the broker drops or disconnects an unauthorised publish |
| Device logs | read partition 2 ([Logs](/docs/runbook/tenant/services/logs/#reading-back)) | your `boot ok` line, attributed to the device |

That is a working tenant: a device, a backend, and logs, declared in one file and rebuildable from
it. From here: [Day 2](/docs/runbook/tenant/operating/day-2/).
