---
title: "Build the Builder"
weight: -1
---

# Build the Builder

**The Builder is the site's Ansible control node, and everything else is built from it.** It serves
the artifacts, network boot and DHCP that every other host installs from, and it runs the automation
that configures them. This page makes one from a bare machine, with nothing on the site to help:
the starting point when the Builder is lost without warning, or when a site is built for the first
time. When the Builder is still there to help, [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/)
is the gentler path.

**This page is assembled from the automation as it stands and has not yet been run from a bare
machine end to end.** Each step names the code it relies on.

---

## What you need

**Gather these before you start; the Builder needs the internet until it has staged its artifacts:**

| Item | Notes |
|---|---|
| **The machine** | The Builder's hardware, or a replacement |
| **Fedora installation media** | A Fedora USB stick, from Fedora's own downloads |
| **Internet access** | To install packages, clone the repositories and stage artifacts |
| **The automation key** | The `a_autoprov` private key, to reach the rest of the site afterwards |
| **The vault password** | To decrypt the inventory's vault |
| **The machine's interface MAC addresses** | The `base` role finds each interface by its MAC ([Seed Inventory](/docs/runbook/substrate/building-recovery/inventory-setup/)) |

---

## 1. Install Fedora by hand

**This is the one manual install on the site.** Every other host installs from the Builder over the
network; the Builder can't, because nothing is serving yet.

Install Fedora from the USB stick, with a local administrator account. Connect it to the internet.

## 2. Point the inventory at this machine

**The Builder is `dv00bld001p01` in the inventory, and its configuration follows its MAC
addresses.** If this is replacement hardware, update the interfaces in the Builder's `host_vars` to
the new MACs first: `roles/base/tasks/configure_interfaces.yml` matches each declared interface by
MAC and leaves any it can't find alone.

## 3. Install Git and Ansible

```bash
sudo dnf install -y git ansible-core make
```

The `base` role installs Ansible again later, as part of the Builder's own baseline.

## 4. Clone the repositories

**Every repository lives under `/srv/dvnt`,** which the collections' `ansible.cfg` files assume:
each points its inventory at `../ansible-inventory-deevnet/mobile`.

```bash
sudo install -d -o "$USER" /srv/dvnt && cd /srv/dvnt
for r in ansible-inventory-deevnet ansible-collection-deevnet.builder \
         ansible-collection-deevnet.net ansible-collection-deevnet.mgmt \
         deevnet-image-factory deevnet-container-image-factory deevnet-tenant-fabric \
         deevnet-provisioning-api terraform-provider-deevnet deevnet-log-bridge deevnet-docs; do
  git clone "https://github.com/deevnet/$r.git"
done
```

## 5. Unlock the vault

```bash
cd /srv/dvnt/ansible-inventory-deevnet
make install-hooks
make unvault        # asks for the vault password
```

See [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/). Re-encrypt
with `make vault` when the build is done.

## 6. Build the Builder from itself

**The Builder runs its own roles against itself, locally, so it needs no SSH to reach itself:**

```bash
cd /srv/dvnt/ansible-collection-deevnet.builder
make rebuild        # collection dependencies, then the collection itself
ansible-playbook playbooks/site.yml --limit dv00bld001p01 \
  -e ansible_connection=local --ask-become-pass
```

`site.yml` applies the roles for every group the Builder is in:

| Role | What it gives the Builder |
|---|---|
| `base` | Hostname, baseline packages, Ansible, its interfaces |
| `site_trust` | The Deevnet Root CA in the OS trust store |
| `workstation` | The control node's tools: users, development tools, Terraform and Packer, image-build prerequisites |
| `artifacts` | The artifact server, and the artifacts it stages: install trees, ISOs, the `a_autoprov` public key, container images |
| `bootstrap` | Network boot (TFTP) and its dnsmasq |

The `artifacts` role is the same step as [Stage Artifacts](/docs/runbook/substrate/building-recovery/online-preparation/),
which is the next page.

## 7. Load the automation key

**From here the Builder reaches the rest of the site as `a_autoprov`.** Load the private key into
your agent on the computer you connect from, as
[Operator Access](/docs/runbook/substrate/network/operator-access/) describes, and check one host:

```bash
ssh a_autoprov@dv02hyp001p01.mobile.deevnet.net true
```

---

## What doesn't come back

**A few things lived only on the old Builder.** A new one starts without them:

| Lost with the Builder | How it comes back |
|---|---|
| Locally built container images (the Deevnet API, VerneMQ) | Rebuilt from their tagged source by `deevnet-container-image-factory` |
| Copies of the core router's configuration | Exported from the router again |
| The cold-fallback Omada controller and its snapshot | Not recoverable; see [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/) |

Next: [Stage Artifacts](/docs/runbook/substrate/building-recovery/online-preparation/).
