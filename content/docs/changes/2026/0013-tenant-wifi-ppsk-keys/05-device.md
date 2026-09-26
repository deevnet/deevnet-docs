---
title: "5. A client joins"
weight: 5
---

# Phase 5: A client joins with a tenant's key

**Needs someone at the site with a wireless client.** Everything before this is remote.

What this phase proves is narrow and worth stating: **that a tenant's key authenticates, and that
the key decides the VLAN.** Any wireless client does that. It does not have to be the device the
tenant will eventually run.

## Run

Get the credential from the tenant, not from the controller:

```bash
cd /srv/eds/infra/deevnet-tenant-eds
terraform output -json device_wifi     # ssid, psk, vlan
```

Then join `DVNTM-IOT` with it, from a laptop, a phone, or the LP stand:

```bash
# the stand, when one is to hand
cd /srv/eds/firmware/lp-stand
idf.py menuconfig     # LP jacket stand -> Network -> WiFi SSID / WiFi password
idf.py flash monitor
```

The firmware needs no code change: `CONFIG_LP_WIFI_SSID` already defaults to `DVNTM-IOT`.

## Verify

**From the network:**

1. The client associates with the tenant's key — and **only** with it. `DVNTM-IOT` has no shared
   key, so a wrong password is a clean failure.
2. It takes a lease in **`10.20.30.0/24`**. That is the per-key VLAN binding working, and it is the
   whole point of the phase: nothing about the SSID says VLAN 30 for this client, the key does.
3. The controller's client list shows it on `DVNTM-IOT`.

## Undo

Disconnect, or reflash the previous configuration. Nothing depends on the client.

---

## Outcome — 2026-09-18: PASSED, after a fight

A macOS client joined `DVNTM-IOT` with eds's key and took **`10.20.30.100`**, confirmed in the
controller's client list. That is the whole chain working: eds asked for a key in its own Terraform,
got back an SSID and a password, and a device flashed with them landed on the IoT segment — no
operator touching the controller, no tenant key in the substrate vault.

The client appeared as `EE-8A-79-8B-94-AC`, a **randomized MAC** (macOS private Wi-Fi address).
Worth knowing: that is a second, independent reason MAC binding would have been useless here — the
address you would bind to is not stable.

### It did not work on the first two attempts

Two different clients were rejected after a few seconds — the signature of a 4-way handshake
failing on the MIC, not an instant refusal. Ruled out, in order:

| Checked | Result |
|---|---|
| The key the tenant holds vs the key the controller holds | **identical** (sha256 compared), no ambiguous characters |
| SSID on the controller | `security: 4`, `vlanEnable`, `vlanId: 30`, correct `ppskProfileId`, enabled, broadcast |
| `pskSetting` values | `versionPsk: 2` (WPA2-PSK), `encryptionPsk: 3` (AES), identical to the three working SSIDs |
| `pmfMode` | `3` (Disable) — already the vendor's suggested workaround |
| `enable11r` | `false` — already the other vendor workaround |
| The AP's own view of the SSID | present, `security: 4`, VLAN 30, enabled, no shared password |
| Profile | `type: 0`, holding `eds-devices` bound to VLAN 30 |
| Controller event log | nothing — this controller logs device events only, never client associations |

What fixed it: **re-applying the SSID's security configuration in place**
(`update-basic-config` with `ppskSetting`) **while the profile held a key**, then force-provisioning
the AP. Both returned `Success`, and the AP never dropped off the controller.

**Which of the two did it is not known.** They were run together to save the operator a round trip,
and an earlier force-provision on its own had not helped — though the retry timing after that one
was not controlled. This is recorded as an unresolved attribution rather than dressed up as a clean
result.

## DEFECT: a profile that was empty when its SSID was created does not authenticate

This is the finding, and it matters more than the fix above.

`omada-wireless.yml` creates the PPSK profile **empty**, the SSID binds to it, and the API adds keys
afterwards. The AP evidently does not honor a key added to a profile that was empty when the SSID
was provisioned to it — until something re-pushes the SSID's security configuration. **So on a fresh
site the first tenant's key is dead on arrival**, which is exactly what happened here.

Note what this does to a conclusion recorded in phase 2. That page reports, correctly, that this
controller *accepts* `createPPSKProfile` with `{"ppsk": []}`. It does. But the AP then will not
authenticate against that profile, so **acceptance was never the question that mattered** — and
recording it as a settled, useful fact was a mistake worth naming.

The contrast with [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) phase 6 is
the evidence: that test created the profile **with two keys** and *then* created the SSID, and a
client joined first time.

**Two candidate fixes, neither built:**

1. **The API force-provisions the AP after a key write.** Correct by construction, but it makes the
   provisioning API re-push a network device on every key issuance, and it needs the
   *Site Device Manager Modify* permission on top of what it already holds.
2. **Never let the profile be empty when the SSID is created.** Have the play seed it with
   `DEEVNET-PLACEHOLDER-DO-NOT-USE` — the mechanism already exists, for the revocation case — so the
   SSID is always bound to a non-empty profile, matching the order CHG-0005 proved.

Option 2 is preferred for the same reason the placeholder was preferred over `modifyPPSKProfile`: a
one-off at profile creation beats a device write on every tenant action. **But the hypothesis is
untested.** The clean test is a fresh profile-and-SSID pair, which is what a rebuild does anyway, so
it should be proven there rather than by tearing down a working SSID now.

---

## What this phase does NOT prove, and one trap

**A device reaching a tenant's workload is not this test, and would pass for the wrong reason
today.** It is tempting to join `DVNTM-IOT` and then curl a tenant service — say
`services.eds.mobile.deevnet.net` on 10.20.130.10, which
[CHG-0012](/docs/changes/2026/0012-operator-access-to-tenants/) made reachable. That will work right
now, and it proves nothing good:

- It works because **[CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) has never run**, so
  the core router passes everything between zones. CHG-0012's declared rules let `management` and
  `trusted` use the tenant route — **not `iot`**. So the moment the zone policy is enforced, that
  same test fails, correctly.
- It is also not the intended path. Under
  [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) a device is
  *platform-attached*, not a member of its owner's fabric: it talks to the **broker** on IoT
  Backend, and the broker talks to the tenant's workloads. A device reaching a tenant VM directly
  crosses a boundary the model deliberately does not draw.

So if you run it, read the result as **a demonstration that the zone policy is still missing**,
which is CHG-0007's job, not as a Wi-Fi or tenant-isolation success. The Wi-Fi result is step 2
above: the lease in 10.20.30.0/24.

### Observed 2026-09-18, and it is the strongest evidence CHG-0007 has

From `10.20.30.100`, the operator reached **the Builder on the management segment**. That is not
supposed to be possible, and it works because the core router still carries the
`ansible:temp-allow-all-optN` rules and passes everything between zones (INC-0001).

The declared policy gives `iot` **exactly one** outbound path:

```
iot -> iot_backend    pass
```

No `iot -> management`. No `iot -> tenant_transit` either — so a device was never going to reach a
tenant's workloads directly even if the overlay had been reachable from the AP. Once CHG-0007 runs, a
device on VLAN 30 reaches the broker and nothing else, which is precisely the ADR-0011 model.

**So the two halves of the IoT story are in very different states.** The credential boundary works:
a tenant's key decides which VLAN its devices land on. The network boundary does not exist: that
VLAN then reaches everything. This was previously established by a read-only audit; it has now been
demonstrated from a client, which is better evidence.

### The expectation this corrected

The operator expected the device to land on **eds's own tenant network**. It does not, and cannot:
eds's network is an EVPN/VXLAN overlay inside hv02's SDN fabric, and it does not extend to the AP —
whose switch port trunks VLANs 10, 30, 31, 40 and 99. Under
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) a device is
*platform-attached*, not a fabric member: it attaches by **trust class**, and the key says **which
tenant owns it**, not which network it joins.

Putting devices on their tenant's own network is ADR-0011 **Option B, rejected** — it would need an
SSID per tenant (APs cap out around 8-16 per radio, and each beacon costs airtime) and a VLAN per
tenant, which the segmentation standard forbids outright: *"A tenant MUST NOT require a VLAN, a
switch change, or a core router change to create."*

That this needed explaining after the fact is a documentation finding, not just an operator one: the
pages an operator actually reads before a test should say it plainly.

**The end-to-end vertical is blocked elsewhere.** A joined stand has nothing to talk to — VerneMQ on
`dv02msg001v01` is built and empty. Packaging the eds services and standing up the broker are their
own effort, not this change.