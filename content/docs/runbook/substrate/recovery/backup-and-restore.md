---
title: "Backup and Restore"
weight: 3
---

# Backup and Restore

The site backs up two things, both on the provisioning VM `dv02prv001v01`: the Deevnet API's database
and the tenants' Terraform state bucket. Each backup is one encrypted archive on a USB drive attached
to the management hypervisor. Nothing else on the site is backed up.

| | |
|---|---|
| Backed up | The Deevnet API's database; the current objects in the `tf-state` bucket |
| Host | `dv02prv001v01`, by the `deevnet.mgmt` role `backup` |
| Drive | One USB drive on `dv02hyp001p01`, passed through to the VM; filesystem label `deevnet-backup` |
| Archive | `dv02prv001v01/deevnet-backup-dv02prv001v01-<UTC time>.tar.age` on the drive, about 70 kB |
| Encryption | `age`, to the site's backup key. The private half is `vault_backup_age_identity` in the inventory vault and on no host |
| When | Whenever the VM is up and the newest good backup is older than 24 hours; and on demand |
| Kept | The newest 30 archives on the drive |

{{< hint warning >}}
**A backup is a shortcut, not the recovery path.** Tenants rebuild from their own repositories without
one ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)). A restored backup
plus one reconcile brings every tenant back as it was, with the secrets it already had, which spares
its devices a visit.
{{< /hint >}}

{{< hint info >}}
**A restore has been rehearsed once**, on 2026-10-07: the provisioning VM was destroyed, rebuilt from its
roles, restored from the drive and reconciled, and came back identical
([CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/) step 3). [Restore](#restore) is that
procedure.
{{< /hint >}}

Every command on this page runs on the Builder, in `ansible-collection-deevnet.mgmt`, with the
inventory decrypted.

---

## What is backed up

**Each archive holds a database dump, a copy of the state bucket and a manifest, and nothing else.**

| In the archive | What it is | Taken how |
|---|---|---|
| `database.pgdump` | The whole `deevnet_api` database | `pg_dump`, custom format, inside the `deevnet-api-db` container |
| `state/` | Every current object in the `tf-state` bucket, under its own key | Read over S3 with the store's own client |
| `MANIFEST` | The host, the time, the object count, and a SHA-256 of every file above | Written by the job |

**The database is the Deevnet API's whole record of its tenants.**

| Table | Holds |
|---|---|
| `tenants` | Each tenant's name, index and status; the hash of its API token; its DNS update secret, state store secret, log tokens and dashboard password |
| `tenant_steps` | Which admission steps each tenant has completed |
| `tenant_workloads` | Each workload's ordinal, VMID, MAC, address, size and SSH keys |
| `tenant_devices` | Each registered device, its trust class and MAC |
| `tenant_device_addresses` | Each device's fixed address |
| `tenant_wifi_keys` | Each tenant Wi-Fi key and the MAC it is bound to |
| `tenant_broker_accounts` | Each MQTT account's password hash and topic permissions |
| `tenant_records` | The names and addresses the API recorded for a tenant |
| `admission_keys` | Wi-Fi keys issued at admission and not yet claimed |
| `audit_log` | Every action the API took, for whom |
| `schema_migrations` | The schema version |

The API stores tenant secrets sealed by OpenBao, so the dump carries them sealed. Reading them back
needs the OpenBao that sealed them, which is not in the backup.

**The state bucket holds one Terraform state file per tenant that keeps its state in the store.** Each is
`tenants/<name>/terraform.tfstate`. A tenant's state carries every secret the
substrate issued it.

## What is not backed up

**Everything outside those two is rebuilt from code, resupplied by tenants, or lost.**

| Not in the backup | On | What brings it back |
|---|---|---|
| OpenBao: its storage, the key that seals tenant secrets in the database, the Tenant Device CA key | `dv02idn001v01` | Nothing yet. A restored database's sealed values are readable only by the OpenBao that sealed them ([CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)) |
| The state store's users and access policies | `dv02prv001v01` | A reconcile, with the secrets tenants already hold |
| Earlier versions of a state file | `dv02prv001v01` | Nothing. The archives are the history: one copy per backup |
| Anything in the store outside `tf-state` | `dv02prv001v01` | Its owner |
| The API's and the store's certificates, configuration and container images | `dv02prv001v01` | Their roles, from the inventory |
| Tenants' DNS zones and records | `dv02idn001v01` | A reconcile restores zones and keys. Records don't come back until [CHG-0038](/docs/changes/2026/0038-reconcile-restores-everything/) |
| Broker accounts as the broker holds them | `dv02msg001v01` | Nothing yet (CHG-0038). The database holds what is needed to put them back |
| Tenant Wi-Fi keys as the controller holds them; the controller's own data | `dv02nms001v01` | [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/) for the controller. Nothing yet for the keys (CHG-0038); the database holds them |
| Logs, dashboards, tenant downloads | `dv02obs001v01` | A reconcile restores users and organizations; stored logs are lost |
| Tenants' workloads and their disks | `dv02hyp002p02` | Tenants, from their repositories ([After a Site Rebuild](/docs/runbook/tenant/recovery/after-a-site-rebuild/)) |
| The core router's configuration | `dv02cor002p01` | [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/) |
| The inventory and its vault | Git | Git. The vault holds the backup key, so without it no archive can be read |
| VM images, hypervisor guest definitions, the Builder | The hypervisors, the Builder | [Building Infrastructure](/docs/runbook/substrate/building-recovery/) |

## When a backup runs

**There is no set hour, because the kit is off most of the time.** A check runs ten minutes after the
provisioning VM boots and then every hour while it is up. The check takes a backup when the newest
good one is older than 24 hours, and otherwise does nothing.

A run finds the drive by its label, mounts it, writes the archive, removes archives beyond the newest
30, and unmounts it. The drive is mounted only for those seconds, so it can be pulled at any other
time.

A run fails, and writes nothing, when:

- no drive with the label is attached, or more than one is;
- the drive was not prepared for this site;
- the database or the state store does not answer;
- the number of objects copied differs from the number in the bucket.

## Check the backups

**`make backup-status` is the only place a failed backup shows.** Nothing alerts on one
([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)).

```bash
make backup-status
```

It prints the newest good archive, its age, and how many archives the drive holds. It fails when a
backup is due and the VM has been up two hours without taking one. Time the kit spent powered off is
not counted.

When it fails, the reason is on the VM:

```bash
sudo journalctl -u deevnet-backup.service | grep FAILED
```

## Back up now

**`make backup-now` takes a backup whatever the interval.** Use it before a change to the provisioning
VM, and before the kit is packed.

```bash
make backup-now
```

## Read a backup back

**`make backup-verify` proves the newest archive on the drive can be decrypted and is whole.** It
restores nothing and changes nothing.

```bash
make backup-verify
```

It decrypts the archive with the key from the vault, checks every file against the manifest, and
confirms the database dump is readable. The key is held in memory on the VM for the length of the check
and removed.

`make backup-dry-run` builds and encrypts an archive with no drive attached, and
`make backup-verify SOURCE=dry-run` reads that one back. Together they test the job on a site that has
no drive yet.

## Prepare a drive

**Preparing a drive erases it.** Do it once for each drive, with only that drive attached.

1. Attach the drive to `dv02hyp001p01`. Read its vendor and product ID there with `lsusb`.
2. Declare it on the VM, in `host_vars/dv02prv001v01/vars.yml`:

   ```yaml
   mgmt_vm:
     usb:
       - slot: usb0
         mapping: deevnet-backup
         id: "<vendor>:<product>"
   ```

3. Pass it through:

   ```bash
   ansible-playbook playbooks/vm-usb.yml --limit dv02prv001v01
   ```

   The first time, the play reports that the device waits for a cold start. Stop and start the VM from
   the hypervisor; a reboot from inside is not enough. The API and the state store are down for about a
   minute.

4. On the VM, read the drive's serial with `lsblk -o NAME,SIZE,TRAN,MODEL,SERIAL`, then:

   ```bash
   make backup-drive SERIAL=<serial>
   ```

   It asks for the serial again, refuses anything that is not exactly one unmounted USB disk with that
   serial, erases it, and labels it `deevnet-backup`.

5. `make backup-now`, then `make backup-verify`.

A second drive of the same model needs only steps 4 and 5. A different model changes `id` in step 2.

## Restore

**A restore fills a provisioning VM that its roles have just rebuilt, and a reconcile finishes it.** The
rehearsal took four and a half minutes from destroying the old VM to every tenant reconciled.

{{< hint danger >}}
**Rebuilding this VM the ordinary way can take the core router down.** A new clone downloads a full
package upgrade, and the roles push about 650 MB of container images, all through the router, which
has hard-hung twice under that ([INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/)).
The procedure below keeps all of it off the router. Until the router's driver is changed, do it with a
screen and keyboard on the router.
{{< /hint >}}

### 1. Stage what the VM needs, on its hypervisor

**The images and the `age` package reach the VM on an ISO, so nothing large crosses the router.** The
Builder and the management hypervisor are on the same segment.

On the Builder, collect the three image tarballs the VM's roles load (the state store's, PostgreSQL's
and the API's, from `/srv/deevnet-http/container-images/`) and the `age` package for the VM's Fedora
release:

```bash
dnf download --releasever=<release> --repo=fedora --arch=x86_64 age
sha256sum *.tar *.rpm > SHA256SUMS
```

Copy them to `dv02hyp001p01` and build the ISO there:

```bash
sudo genisoimage -quiet -J -r -V DVNT_IMAGES \
  -o /var/lib/vz/template/iso/deevnet-prv-images.iso <the directory>
```

### 2. Build the VM

`dv02prv001v01` declares `ciupgrade: false`, so the clone does not upgrade itself on first boot, and
its `mgmt_vm.usb` entry, so it comes up with the backup drive attached.

```bash
ssh-keygen -R dv02prv001v01.mobile.deevnet.net; ssh-keygen -R 10.20.25.20
ansible-playbook playbooks/site.yml --limit dv02prv001v01 --tags vms
```

A rebuilt VM has a new host key. The reconcile in step 5 reads its token over SSH by name and stops on
the old one.

### 3. Load the images from the ISO

On the hypervisor, with the VM stopped, since an IDE drive is not hot-plugged:

```bash
sudo qm shutdown 201
sudo qm set 201 --ide2 local:iso/deevnet-prv-images.iso,media=cdrom
sudo qm start 201
```

On the VM:

```bash
sudo mkdir /etc/yum.repos.d.off && sudo sh -c 'mv /etc/yum.repos.d/*.repo /etc/yum.repos.d.off/'
sudo mkdir /mnt/images && sudo mount -o ro /dev/disk/by-label/DVNT_IMAGES /mnt/images
(cd /mnt/images && sha256sum -c --quiet SHA256SUMS)
sudo rpm -i /mnt/images/age-*.rpm
for t in /mnt/images/*.tar; do sudo podman load -q -i "$t"; done
sudo umount /mnt/images
```

The package repositories are moved aside so that nothing in the next step fetches their metadata. The
roles find each image already loaded and push nothing.

### 4. Run the roles, then restore

```bash
ansible-playbook playbooks/site.yml --limit dv02prv001v01 --skip-tags vms
make backup-restore CONFIRM=dv02prv001v01
```

The roles leave an empty registry and an empty bucket. `make backup-restore` reads the newest archive
on the drive, or the one named with `ARCHIVE=`, checks it against its manifest, stops the API, replaces
the database, copies the state files into the bucket and starts the API. It refuses a host whose
registry holds tenants or whose bucket holds objects, so it cannot overwrite a live one.

Until it has been restored, the rebuilt VM does not back itself up: the job skips a registry with no
tenants, so an empty archive never becomes the newest.

### 5. Reconcile

```bash
make reconcile NAME=--all
```

The restore brings back what the API knows. The reconcile makes the rest agree with it: each tenant's
state store user, with the secret the tenant already holds, and its zone, key, network, log users and
dashboard organization. Before it runs, a tenant cannot read its own state.

### 6. Finish

On the VM, put the repositories back:

```bash
sudo sh -c 'mv /etc/yum.repos.d.off/*.repo /etc/yum.repos.d/ && rmdir /etc/yum.repos.d.off'
```

On the hypervisor, detach the ISO, which takes a stop and start, and delete it:

```bash
sudo qm set 201 --delete ide2 && sudo qm shutdown 201 && sudo qm start 201
sudo rm /var/lib/vz/template/iso/deevnet-prv-images.iso
```

Then `make backup-now` and `make backup-verify`, so the rebuilt VM has a backup of its own.

### What a restore does not bring back

- **Anything a tenant applied after the archive was taken.** The tenant's next apply resupplies it.
- **Earlier versions of a state file.** The bucket starts again with one version of each.
- **Tenant secrets, if OpenBao was lost too.** The restored database holds them sealed by the OpenBao
  that was running when the backup was taken
  ([CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)).

### Without the commands

An archive is an `age`-encrypted tar. Given the private key from the vault in a file, any machine with
`age` opens it:

```bash
age --decrypt --identity <key file> <archive> | tar -xf -
```

That yields `MANIFEST`, `database.pgdump` and `state/`. The dump restores with `pg_restore` into an
empty `deevnet_api` database of the same PostgreSQL major version, and the files under `state/` go back
into the `tf-state` bucket under the same keys with any S3 client.
