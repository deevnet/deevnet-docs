---
title: "Undo"
weight: 9
---

# CHG-0013: Undo

Written before the change ran. Each phase is reversible on its own, and the order here is the
reverse of the order they run in.

| Phase | Reversal | Leaves behind |
|---|---|---|
| 5. Device | Reflash the stand's previous configuration | Nothing depends on the stand |
| 4. Tenant | `terraform destroy -target=deevnet_iot_wifi_key.devices`, or remove the block and apply | The key is revoked at the controller |
| 3. API | Redeploy `deevnet_api_version: v0.2.6`; delete any test key from the profile | Unsetting `deevnet_api_omada_url` alone stops key issuance without a rollback |
| 2. Substrate | Controller UI: delete the SSID `DVNTM-IOT`, then the PPSK profile `DVNTM-IOT`. `git revert` the inventory commit, restoring `deevnet_wifi_psk.iot`, then `make vault` | The VLAN 30 network object may stay; it is harmless and every other segment has one |
| 1. Recon | None — nothing was written | |

## What cannot be undone

**A revoked key.** Once a tenant's key is deleted and a new one issued, every device flashed with
the old one needs a physical visit. Reversing phases 3 and 4 in the order above avoids this: destroy
the Terraform resource, which revokes one key deliberately, rather than rolling the API back and
leaving keys stranded in a profile nothing manages.

**An association that dropped during phase 2.** If clients dropped off `DVNTM` while the WLAN group
re-applied, they will have reconnected by themselves; there is nothing to undo, only to notice.

## The order matters

Do **not** roll the API back before destroying the tenant's key. The registry row would go with the
rollback while the key stayed in the controller's profile — a credential belonging to nobody that
still admits a device to the IoT segment. Phase 4's undo first, then phase 3's.
