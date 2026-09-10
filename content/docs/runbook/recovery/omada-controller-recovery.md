---
title: "Omada Controller Recovery"
weight: 2
aliases:
  - /docs/runbook/omada-controller/
---

# Omada Controller Recovery

Getting the Omada controller on the builder back when an upgrade goes wrong or its data is
damaged. Everything here restores from a data snapshot. How snapshots are taken, and how
upgrades are done, is in [Omada Controller Upgrade](/docs/runbook/lifecycle/omada-controller-upgrade/).

| | |
|---|---|
| Runs as | `mbentley/omada-controller` under podman, `omada-controller.service`, on `dv00bld001p01` |
| Data | `/opt/omada-controller` (`data`, `work`, `logs`) |
| Current | `6.3.0.45` since 2026-09-10. TP-Link released it on 2026-09-04. |
| Fallback | `6.2.14.11`, staged and rehearsed |
| Last resort | `6.1.0.19`, what ran before |
| Snapshot | `/opt/omada-controller-backup/omada-6.1.0.19-data-2026-09-10.tar.gz` |
| Web UI | `https://10.20.99.95:8043/independent/index.html#login` (6.3 moved it from `/login`) |

{{< hint danger >}}
**A controller cannot open a database that a newer one has upgraded.** Starting an older image
on the current data is therefore not a way back. Every path here starts from a snapshot, and
**anything configured since that snapshot was taken is lost**: adoptions, networks, SSIDs,
accounts.

Today's only snapshot predates the 6.3 upgrade. Falling back is cheap while 6.3 is new and has
had little configured on it, and it gets more expensive with every change. If 6.3 is going to be
abandoned, decide early — ideally during the first adoptions, not months later.
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
([upgrade step 3](/docs/runbook/lifecycle/omada-controller-upgrade/#3-recreate-the-container-on-the-new-image))
and verify it
([upgrade step 4](/docs/runbook/lifecycle/omada-controller-upgrade/#4-verify)). If the image is
not already loaded on the builder, load it from the artifact server:

```bash
sudo podman load -i /srv/deevnet-http/container-images/omada-controller/<image>.tar
```

Afterwards, point inventory at the version now running
([upgrade step 5](/docs/runbook/lifecycle/omada-controller-upgrade/#5-pin-inventory-to-the-new-version)).
If you skip that, the next playbook run brings back the version you just left, and upgrades the
database again.

Devices adopted after the snapshot was taken are not in it. They show as pending, or as managed
by another controller, and have to be adopted again. The
[AP](/docs/runbook/recovery/console-recovery/wireless-ap/) and
[access switch](/docs/runbook/recovery/console-recovery/access-switch/) console-recovery pages
cover re-adoption.

## Fall back to 6.2.14.11

Use this if 6.3 misbehaves. 6.2 is the mature line (July 2026), and it is what the SG2218's
1.20.24 firmware was built against.

Restore `omada-6.1.0.19-data-2026-09-10.tar.gz` as above, and recreate the container with tag
`6.2.14.11`.

**Rehearsed 2026-09-10:** 6.2.14.11 was started on a copy of that snapshot, in a separate
container on a loopback-only port where no device could reach it. It upgraded the database in
under a minute, kept the `dvntm` site and the `omadacId`, and `a_autoprov` logged in over the
API.

## Roll back to 6.1.0.19

Use this only if 6.2 fails too. It is the same restore, with tag `6.1`.

---

## History

On 2026-09-10 the controller was upgraded in place from 6.1.0.19 to 6.3.0.45. The snapshot
above was taken first, and 6.2.14.11 was staged and rehearsed as the fallback. That upgrade
will be written up as a [change record](/docs/changes/) together with the network firmware
change, and this note will move there.
