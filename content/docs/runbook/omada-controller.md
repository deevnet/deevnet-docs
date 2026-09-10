---
title: "Omada Controller"
weight: 7
---

# Omada Controller

Upgrading the Omada controller on the builder, and the two ways back if an upgrade goes wrong.

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
on the current data is therefore not a way back. Both the fallback and the last resort start
from the snapshot taken before the 6.3 upgrade, and **anything configured on 6.3 since then is
lost**: adoptions, networks, SSIDs, accounts.

The fallback is cheap while 6.3 is new and has had little configured on it. It gets more
expensive with every change. If 6.3 is going to be abandoned, decide early — ideally during
the first adoptions, not months later.
{{< /hint >}}

Do **not** use `playbooks/upgrade-omada.yml` in the builder collection for any of this. It
hard-codes a fresh install and deletes the data directories.

---

## Upgrade in place

This is how 6.1.0.19 became 6.3.0.45. It keeps the data and replaces only the container.

### 1. Stage the image

Declare it in `artifacts_podman_images` (`group_vars/artifact_servers.yml`) and pull it while
the controller is still running, so the outage covers only the swap:

```bash
sudo podman pull docker.io/mbentley/omada-controller:<tag>
```

### 2. Record, stop, snapshot

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

### 3. Recreate the container on the new image

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

### 4. Verify

`/api/info` should report the new `controllerVer` with the **same** `omadacId` and
`configured: true`. The first start upgrades the database, which took under a minute from 6.1.
`logs/server.log` should show `Database upgraded` and then `Omada Network Application started`.

Then confirm automation still works: the `a_autoprov` account logging in over
`/{omadacId}/api/v2/login` and listing the site is the path every deevnet playbook takes. The
browser may show blank pages or 404s after an upgrade; force-reload or clear the cache.

Finally, set `omada_image_tag` in `group_vars/network_controllers/vars.yml` to match. Until then,
a playbook run would put the old tag back.

---

## Fall back to 6.2.14.11

Use this if 6.3 misbehaves. 6.2 is the mature line (July 2026), and it is what the SG2218's
1.20.24 firmware was built against.

**Rehearsed 2026-09-10:** 6.2.14.11 was started on a copy of the snapshot, in a separate
container on a loopback-only port where no device could reach it. It upgraded the database in
under a minute, kept the `dvntm` site and the `omadacId`, and `a_autoprov` logged in over the
API.

```bash
sudo systemctl stop omada-controller
sudo mv /opt/omada-controller /opt/omada-controller.6.3-$(date +%F)    # set aside, not deleted
sudo tar --selinux --xattrs --acls -xzpf \
  /opt/omada-controller-backup/omada-6.1.0.19-data-2026-09-10.tar.gz -C /opt
sudo restorecon -R /opt/omada-controller
```

Then run [step 3](#3-recreate-the-container-on-the-new-image) with tag `6.2.14.11`, and
[step 4](#4-verify). The image is already loaded on the builder. If it is not, load it with
`sudo podman load -i /srv/deevnet-http/container-images/omada-controller/omada-controller-6.2.14.11.tar`.

Afterwards, point inventory at 6.2: set `omada_image_tag`, and move the `omada-controller`
entry's image and `latest_symlink` to 6.2.14.11. If you skip that, the next playbook run brings
6.3 back and upgrades the database again.

Devices adopted on 6.3 are not in the snapshot. They show as pending, or as managed by another
controller, and have to be adopted again.

## Roll back to 6.1.0.19

Use this only if 6.2 fails too. It is the same procedure as the fallback, with tag `6.1`.
