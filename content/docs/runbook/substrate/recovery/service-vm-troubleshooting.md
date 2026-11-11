---
title: "Troubleshoot a Service VM"
weight: 6
---

# Troubleshoot a Service VM

Finding what is wrong with one of the six
[substrate service VMs](/docs/platforms/management-plane/substrate-service-vms/) and getting it back:
a service that is down, a name that gets no TLS handshake, a VM that is off the network, and a disk
that is full or missing.

**Nothing raises an alarm for any of these yet.** They come to light when someone tries to use the
service ([How the plane is watched](/docs/architecture/substrate/management-plane/#how-the-plane-is-watched)).
Start from what failed for the user and work inward, in the order below: the network, the VM, the
service, the proxy, then the disk.

---

## How every service VM runs

**All six VMs are built the same way, so the same checks apply to each:**

- **Each service is a Podman container under its own systemd unit**, `/etc/systemd/system/<name>.service`.
  The unit and the container share a name.
- **A failed container is restarted every 10 seconds, indefinitely** (`Restart=always`,
  `RestartSec=10`). A service that keeps failing does not stay down. It loops, and nothing reports it.
- **Data lives under `/srv/<service>`.** Only `dv02obs001v01` has a separate data disk mounted at
  `/srv`. On the other five, `/srv` is on the OS disk. The Omada controller keeps its data under
  `/opt/omada-controller`.
- **Each host is rebuilt from code:** `make rebuild`, then `site.yml --limit <host>` in
  `deevnet.mgmt` ([Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/)).

| Host | Units |
|---|---|
| `dv02nms001v01` | `omada-controller` |
| `dv02col001v01` | none yet |
| `dv02prv001v01` | `deevnet-api`, `deevnet-api-db`, `minio`, `service-proxy` |
| `dv02idn001v01` | `openbao`, `pdns-auth` |
| `dv02obs001v01` | `victorialogs`, `vmauth`, `grafana`, `tenant-downloads`, `service-proxy` |
| `dv02msg001v01` | `vernemq`, `vernemq-db`, `deevnet-log-bridge` |

---

## VM unreachable

**Proxmox reporting `running` does not mean the VM is on the network.** In
[INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) the controller VM was `running`
while it answered nothing. Only the guest agent and the network showed the real state.

From the management hypervisor, `dv02hyp001p01`:

```bash
qm status <vmid>          # the process, nothing more
qm agent <vmid> ping      # the guest OS: every service VM runs the agent
ip neigh | grep <ip>      # INCOMPLETE: nothing on the bridge answers for that address
```

| What you see | Where the fault is |
|---|---|
| Agent answers and ARP resolves, but the service doesn't | Inside the guest, at the service: see [Service down](#service-down) |
| Agent silent, ARP `INCOMPLETE`, but other VMs on `vmbr0` answer | Inside the guest, below the service (a wedged OS or network stack) |
| Every VM on the hypervisor is silent | The hypervisor or its uplink, not this VM |
| Agent answers, but the VM is on an address other than its reservation | Its DHCP reservation: see below |

**Capture before you reboot.** For a wedged guest, open the noVNC console in the Proxmox UI and
record what is on the screen before you reboot. The service VMs have no serial port. A reboot
restores service and destroys the evidence. INC-0002's cause is still unknown for that reason.

### On the wrong address

**A VM on an address other than its own has taken a pool lease instead of its reservation.** Either the reservation is missing, or there are
two reservations for the address. A host rebuilt under a new MAC leaves its old reservation behind,
because `opnsense_dhcp` only adds and updates. It also skips, **without any message**, a host whose
MAC is empty, and a host whose `infrastructure` is set at group level rather than host level.

1. On the core router, find every reservation for the address, and delete any with a MAC other than
   the one in the host's `identity.yml`.
2. `make dhcp && make dns` in `deevnet.net`.
3. Reboot the guest, so it asks again.

---

## Service down

**On the VM, ask systemd first, then the container:**

```bash
systemctl status <unit>
journalctl -u <unit> -n 100 --no-pager
sudo podman ps -a                     # Up, or Exited with a code
sudo podman logs --tail 100 <unit>
```

| What you see | Meaning |
|---|---|
| `activating (auto-restart)`, a restart count that keeps rising | The service is crash-looping. The reason is in the container's own log, not systemd's |
| `active (running)`, but the service doesn't answer | It is up but not listening where callers expect. Behind the proxy, it listens on `127.0.0.1` only, so test it from the VM: `curl -sk https://127.0.0.1:<port>/` |
| Fails at `ExecStart` with no container log | The container doesn't exist, often after a failed play. Re-run the host's play |
| Starts, but finds no data | Its data directory is empty: see [Data disk missing](#data-disk-missing) |

**Re-running the play is the fix for drift.** The roles converge configuration, the unit and the
container. Run it with `--limit <host>`, using the project-local collections as
[Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/#build)
describes. A bare `ansible-playbook` silently runs the system-wide copy of the roles instead.

**A service that can't read its certificate or key resets every TLS handshake.** It looks like a
network fault. See
[Certificates → Troubleshooting](/docs/runbook/substrate/certificates/troubleshooting/).

Some services have their own recovery runbooks:

- The Omada controller: [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/)
- OpenBao: [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/)
- The API's database and the state store: [Backup and Restore](/docs/runbook/substrate/recovery/backup-and-restore/)

---

## Proxy refuses a name

On `dv02prv001v01` and `dv02obs001v01`, the
[service proxy](/docs/platforms/management-plane/substrate-service-vms/#the-service-proxy) is the
only listener on 443.

**A name the host doesn't serve gets no handshake at all.** The client sees the connection reset or
an alert during the handshake, never an HTTP error. So a refused handshake on 443 means the name is
not in the host's `service_proxy_vhosts`, or the client sent no name or a different one.

```bash
# From the client: does the host serve this name, and with which certificate?
openssl s_client -connect <host-ip>:443 -servername <name>.<site>.<root> </dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
```

| What you see | Cause and fix |
|---|---|
| Handshake refused for the name | Not in `service_proxy_vhosts` for this host, or the client dialed the wrong host. Add the vhost, which also needs the name as a DNS alias of the host, and re-run the play |
| Handshake works, `502 Bad Gateway` | The proxy is fine, and the service behind it is down or not on its loopback port: see [Service down](#service-down) |
| `502` only for the API | The proxy verifies the API's own certificate under the vhost name. The API's certificate is missing that name or has expired |
| Certificate name mismatch | The proxy's certificate predates the alias. Re-run the play: the certificate is reissued from inventory |
| Works on the old port, fails on 443 | The client uses the address, not the name. The old ports answer any name; 443 answers only by name |

---

## Disk full

**On five of the six VMs, all of the data is on the 32 GB OS disk.** When it fills up, the services
fail to write, and each fails in its own way.

```bash
df -h / /srv
sudo du -xh --max-depth=2 /srv /var/lib/containers | sort -h | tail
sudo podman system df
```

- **Old images:** `sudo podman image prune` removes the images no container uses. Each role loads its
  image from a tarball, so a pruned image comes back on the next run of the play.
- **The journal:** `sudo journalctl --vacuum-size=200M`.
- **Growing the OS disk:** set or raise `mgmt_vm.os_disk_size` in the host's `vars.yml` and re-run
  the play. PVE can grow a disk but not shrink one, and the role refuses a smaller size. Then check
  `df -h /` *inside the guest*. If PVE shows the new size but `df` doesn't, the root filesystem has
  not grown yet. Cloud-init's `growpart` extends it at boot.

`dv02obs001v01`'s logs are on its data disk. The log store's own retention and size cap keep it from
growing without limit.

---

## Data disk missing

**`dv02obs001v01` mounts its data disk at `/srv` with `nofail`**, so if the disk is missing, the host
still boots and is reachable for repair. The service units do not wait for the mount. As the units
are written, with the disk absent, the log store, Grafana and the downloads start on an empty `/srv`
on the OS disk. Data then appears to be lost, and new data goes to the wrong disk.

```bash
findmnt /srv                              # nothing: the data disk is not mounted
lsblk -o NAME,SIZE,SERIAL,MOUNTPOINT      # is a disk with serial deevnet-data present?
```

1. Stop the services that write under `/srv`, so nothing more lands on the OS disk.
2. If the disk is present but unmounted, re-run the play. The `data_disk` role finds the disk by its
   serial, refuses to touch the disk backing `/`, refuses to mount over a populated directory, and
   makes a filesystem only on a disk that doesn't have one.
3. If the disk is missing from the VM, check `qm config <vmid>` for `scsi1`. A re-run of the play
   attaches a disk that is declared but missing. Data on a destroyed volume is gone:
   `qm destroy` deletes every volume the VM owns.
4. Move anything written to the OS disk's `/srv` while the disk was missing aside, before the
   mount hides it.

---

Rebuilding the whole host instead is [Rebuild a Hypervisor](/docs/runbook/substrate/recovery/rebuild-hypervisor/#management-hypervisor-dv02hyp001p01)
for the hypervisor, and [What a failure takes with it](/docs/runbook/substrate/recovery/#what-a-failure-takes-with-it)
for what each VM loses.
