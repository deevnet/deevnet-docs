---
title: "Omada Controller Recovery"
weight: 2
aliases:
  - /docs/runbook/recovery/omada-controller-recovery/
  - /docs/runbook/omada-controller/
---

# Omada Controller Recovery

The site's Omada controller runs on `dv02nms001v01`. Its settings are backed up, vault-encrypted, into
the inventory after every change. The Builder keeps a stopped, empty controller as a cold fallback,
and a copy of a whole-data snapshot of the live controller. How upgrades are done, and how snapshots
are taken, is in
[Omada Controller Upgrade](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/).

| | Live controller | Builder's cold copy |
|---|---|---|
| Host | `dv02nms001v01`, 10.20.99.40 | `dv00bld001p01`, 10.20.99.95 |
| Runs as | `omada-controller` container (`mbentley/omada-controller:6.3.0.45`), `deevnet.mgmt` role `omada_controller` | The same container name, stopped |
| Data | `/opt/omada-controller` (`data`, `work`, `logs`) | `/opt/omada-controller`, empty: a fresh, never-configured install |
| Settings backup | `backups/mobile/dv02nms001v01/omada-backup.cfg.vault` in the inventory, written by `make wireless APPLY=1` and `make backup-wireless` in `ansible-collection-deevnet.net` | The same, from any clone of the inventory |
| Data snapshot | `/opt/omada-controller-backup/omada-6.3.0.45-data-2026-10-06.tar.gz`, taken by hand | The same file, copied, with its `.sha256` |
| Web UI | `https://omada.mobile.deevnet.net:8043/` | Only while it is started |

**The settings backup is the one to restore.** It holds the site, its networks, SSIDs, PPSK profiles
with the tenants' keys, and the AP, as of the last change, and it is in the inventory, so it survives
losing both hosts. It leaves out most client and statistics history. Wi-Fi keys the Deevnet API issued
after it was taken are not in it; each tenant's next apply puts them back. The data snapshot keeps
everything but is one hand-taken copy from 2026-10-06; use it only to go back to that day.

{{< hint danger >}}
**A controller cannot open a database that a newer one has upgraded.** The snapshot is on
6.3.0.45, so it restores onto 6.3.0.45 or newer, never onto 6.2 or 6.1. Every path here starts
from a snapshot, and **anything configured since that snapshot was taken is lost**: adoptions,
networks, SSIDs, accounts, and tenant Wi-Fi keys, which a tenant's next `terraform apply` puts back.
{{< /hint >}}

Do **not** use `playbooks/upgrade-omada.yml` in the builder collection for any of this. It
hard-codes a fresh install and deletes the data directories.

---

## Restore the settings backup

Proven on the Builder's cold controller in
[CHG-0062](/docs/changes/2026/0062-device-backups-after-change/). It works onto any controller of the
same version or newer that has never been configured.

1. **Decrypt the backup** on the computer whose browser does the restore. The plaintext holds the
   tenants' Wi-Fi keys: delete it once the controller has taken it.

   ```bash
   cd ansible-inventory-deevnet
   ansible-vault decrypt --output ~/omada-backup.cfg backups/mobile/dv02nms001v01/omada-backup.cfg.vault
   ```

2. **Start the empty controller** and open its web UI in a private window. A browser that has used
   the same address before can land on an old login page instead of the setup wizard.
3. **Create a local account in the setup wizard.** The wizard has no restore option; a throwaway
   account and the defaults are enough to get past it.
4. **Restore** under **Settings → Maintenance → Backup & Restore**, from `~/omada-backup.cfg`. The
   controller keeps its own `omadacId`; automation reads it from `/api/info` on every run.
5. **Log in** and check the site, its SSIDs and PPSK profiles. The account made in step 3 still works
   afterwards.

The AP comes back as a known device that is not connected. It reports to the address of the
controller that adopted it, so on another host it has to be adopted again (untested on a rebuild at
the same address).

## Restore from a snapshot

A snapshot can be started on the version it was taken from, or on any newer version, which
upgrades it. It cannot be started on an older one.

```bash
sudo systemctl stop omada-controller
sudo mv /opt/omada-controller /opt/omada-controller.failed-$(date +%F)    # set aside, not deleted
sudo tar --selinux --xattrs --acls -xzpf /opt/omada-controller-backup/<snapshot>.tar.gz -C /opt
sudo restorecon -R /opt/omada-controller
```

Then recreate the container on the chosen image
([upgrade step 3](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/#3-recreate-the-container-on-the-new-image))
and verify it
([upgrade step 4](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/#4-verify)). If the image is
not already loaded on the builder, load it from the artifact server:

```bash
sudo podman load -i /srv/deevnet-http/container-images/omada-controller/<image>.tar
```

Afterwards, point inventory at the version now running
([upgrade step 5](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/#5-pin-inventory-to-the-new-version)).
If you skip that, the next playbook run brings back the version you just left, and upgrades the
database again.

Devices adopted after the snapshot was taken are not in it. They show as pending, or as managed
by another controller, and have to be adopted again. The
[AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/) and
[access switch](/docs/runbook/substrate/recovery/console-recovery/access-switch/) console-recovery pages
cover re-adoption.
