---
title: "Omada Controller Recovery"
weight: 2
aliases:
  - /docs/runbook/recovery/omada-controller-recovery/
  - /docs/runbook/omada-controller/
---

# Omada Controller Recovery

The site's Omada controller runs on `dv02nms001v01`. The Builder keeps a stopped, empty controller
as a cold fallback, and a copy of the live controller's snapshot to restore into it. How upgrades are done, and how snapshots are taken, is in
[Omada Controller Upgrade](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/).

| | Live controller | Builder's cold copy |
|---|---|---|
| Host | `dv02nms001v01`, 10.20.99.40 | `dv00bld001p01`, 10.20.99.95 |
| Runs as | `omada-controller` container (`mbentley/omada-controller:6.3.0.45`), `deevnet.mgmt` role `omada_controller` | The same container name, stopped |
| Data | `/opt/omada-controller` (`data`, `work`, `logs`) | `/opt/omada-controller`, empty: a fresh, never-configured install |
| Snapshots | `/opt/omada-controller-backup/omada-6.3.0.45-data-2026-10-06.tar.gz` | The same file, copied, with its `.sha256` |
| Web UI | `https://omada.mobile.deevnet.net:8043/` | Only while it is started |

{{< hint warning >}}
**There is one snapshot, taken by hand on 2026-10-06, and nothing takes them routinely.** It is
the live controller's data on 6.3.0.45, with a copy on the Builder so it survives the management
hypervisor. Restore it on either host. Taking snapshots routinely is on the
[roadmap](/docs/roadmap/infrastructure/mobile/management-plane/).
{{< /hint >}}

{{< hint danger >}}
**A controller cannot open a database that a newer one has upgraded.** The snapshot is on
6.3.0.45, so it restores onto 6.3.0.45 or newer, never onto 6.2 or 6.1. Every path here starts
from a snapshot, and **anything configured since that snapshot was taken is lost**: adoptions,
networks, SSIDs, accounts, and tenant Wi-Fi keys, which a tenant's next `terraform apply` puts back.
{{< /hint >}}

Do **not** use `playbooks/upgrade-omada.yml` in the builder collection for any of this. It
hard-codes a fresh install and deletes the data directories.

---

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
