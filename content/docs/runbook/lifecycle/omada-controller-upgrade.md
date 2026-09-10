---
title: "Omada Controller Upgrade"
weight: 3
---

# Omada Controller Upgrade

How the Omada controller on the builder is upgraded to a new version in place, keeping its
data. Each upgrade is a change: open a [change record](/docs/runbook/change-management/change-record-template/)
of type **Upgrade**. Its steps are the ones below.

If an upgrade goes wrong, or the controller's data is damaged, see
[Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/).

| | |
|---|---|
| Runs as | `mbentley/omada-controller` under podman, `omada-controller.service`, on `dv00bld001p01` |
| Data | `/opt/omada-controller` (`data`, `work`, `logs`) |
| Snapshots | `/opt/omada-controller-backup/` |
| Images | Tarballs on the artifact server, declared in `artifacts_podman_images` (`group_vars/artifact_servers.yml`) |
| Version pin | `omada_image_tag` in `group_vars/network_controllers/vars.yml` |

{{< hint danger >}}
**An upgrade is one-way.** The first start on a new version upgrades the database, and an
older controller cannot open it afterwards. The only way back is the snapshot taken in
[step 2](#2-record-stop-snapshot), so that step is not optional.

Do **not** use `playbooks/upgrade-omada.yml` in the builder collection. It hard-codes a fresh
install and deletes the data directories.
{{< /hint >}}

---

## Choosing the version

- **Pin the build, not a tag family.** Use the exact version tag (for example `6.3.0.45`), not
  `6.3` and never `latest`, so a rebuild restores what was verified.
- **Check what the devices need.** Switch and AP release notes name a recommended controller
  version. Read them before choosing a target.
- **A controller major version can bring a MongoDB major upgrade.** Controller 5 to 6 did, and
  the image documents a separate migration for it. This procedure covers upgrades within a
  MongoDB major version only. Compare `mongod --version` in the old and new images first.
- **A new release is a risk of its own.** When the target is only days old, stage the
  previous mature release as a fallback as well, so the way back does not have to be fetched
  on the day.

---

## 1. Stage the image

Declare the image in `artifacts_podman_images` and pull it while the controller is still
running, so the outage covers only the swap:

```bash
sudo podman pull docker.io/mbentley/omada-controller:<tag>
```

## 2. Record, stop, snapshot

```bash
curl -k https://localhost:8043/api/info     # controllerVer and omadacId, to compare after
sudo systemctl stop omada-controller
```

The unit stops with `podman stop -t 120`, giving MongoDB time to shut down cleanly. systemd
then reports the unit as **failed**, because podman exits 143 on SIGTERM. That is expected.
What matters is that `/opt/omada-controller/logs/mongod.log` ends with
`mongod shutdown complete`. Confirm that before archiving:

```bash
sudo tar --selinux --xattrs --acls -czpf \
  /opt/omada-controller-backup/omada-<current-version>-data-<date>.tar.gz -C /opt omada-controller
```

## 3. Recreate the container on the new image

The arguments are the same ones the `omada_controller` role uses. Only the image changes:

```bash
sudo podman rm -f omada-controller
sudo podman create --name omada-controller --hostname omada-controller --network host \
  -v /opt/omada-controller/data:/opt/tplink/EAPController/data \
  -v /opt/omada-controller/work:/opt/tplink/EAPController/work \
  -v /opt/omada-controller/logs:/opt/tplink/EAPController/logs \
  -e TZ=America/New_York -e MANAGE_HTTP_PORT=8088 -e MANAGE_HTTPS_PORT=8043 \
  -e PORTAL_HTTP_PORT=8088 -e PORTAL_HTTPS_PORT=8843 \
  -e SHOW_SERVER_LOGS=true -e SHOW_MONGODB_LOGS=false \
  --restart=no docker.io/mbentley/omada-controller:<tag>
sudo systemctl reset-failed omada-controller
sudo systemctl start omada-controller
```

If the role's arguments have changed since this was written,
`sudo podman inspect omada-controller --format '{{.Config.CreateCommand}}'` run before the
`rm` prints the set in use.

## 4. Verify

`/api/info` should report the new `controllerVer` with the **same** `omadacId` and
`configured: true`. The first start upgrades the database; from 6.1 to 6.3 that took under a
minute. `logs/server.log` should show `Database upgraded`, then
`Omada Network Application started`.

Then confirm that automation still works. The `a_autoprov` account logging in over
`/{omadacId}/api/v2/login` and listing the site is the path every deevnet playbook takes. The
browser may show blank pages or 404s after an upgrade; force-reload or clear the cache.

## 5. Pin inventory to the new version

Set `omada_image_tag` to the new tag. Point the `omada-controller` entry in
`artifacts_podman_images`, and its `latest_symlink`, at the new image. Keep the previous image
declared as the fallback.

Until this is done, the next playbook run puts the old tag back, on data the new version has
already upgraded.
