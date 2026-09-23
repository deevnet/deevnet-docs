---
title: "Operator Access"
weight: 2
aliases:
  - /docs/runbook/network/operator-access/
---

# Operator Access

Reaching the builder and the management web UIs from an operator laptop, through the travel
router rather than through the site network.

The management segment (VLAN 99) is not reachable from wireless clients. The builder is on it,
and it also has a second interface, `enp1s0`, on the travel router's LAN. A laptop on the travel
router's network (its wireless, or a LAN port) can SSH to the builder there and tunnel every
management UI through that one session.

**This path does not go through the access switch.** It is the one to use for work that takes
the switch down, such as [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/):
the session stays up while the switch reboots. The tunnels themselves do not, because the
builder reaches VLAN 99 through the switch. They start working again when the switch returns.

| | |
|---|---|
| Laptop | On `192.168.8.0/24`, from the travel router `dv02edg001p01` (`192.168.8.1`) |
| Builder | `enp1s0`, DHCP from the travel router, `192.168.8.159` on 2026-09-16 |
| Login | Your own user on the builder, not `a_autoprov` |

The builder's `enp1s0` address comes from DHCP. If it has changed, read it on the builder with
`ip -4 addr show enp1s0`, or from the travel router's client list at `http://192.168.8.1`.

---

## SSH config

On the laptop, in `~/.ssh/config`:

```sshconfig
Host builder-mgmt
    HostName 192.168.8.159
    User cdeever

    ServerAliveInterval 30
    ServerAliveCountMax 3

    IdentityFile ~/.ssh/<github>
    IdentityFile ~/.ssh/<automation>
    ForwardAgent yes

    LocalForward 8441 10.20.99.1:443      # OPNsense
    LocalForward 8442 10.20.99.9:443      # wireless AP, standalone UI
    LocalForward 8443 10.20.99.10:443     # access switch
    LocalForward 8444 10.20.99.21:8006    # Proxmox, management hypervisor
    LocalForward 8445 10.20.99.22:8006    # Proxmox, tenant hypervisor
    LocalForward 8043 10.20.99.40:8043    # Omada controller
    LocalForward 8080 10.20.99.95:80      # artifact server
```

`<github>` is the key you use for GitHub. `<automation>` is the key for the `a_autoprov`
automation user. Then connect with:

```bash
ssh builder-mgmt
```

- **Proxmox listens on `8006`**, not `443`. Nothing answers on `10.20.99.21:443` or
  `10.20.99.22:443`.
- **Each local port can be used once.** If two `LocalForward` lines share a port, SSH binds the
  first, warns about the second, and connects anyway, so the second UI just isn't there.
- **The Omada controller uses the same port on both ends** (`8043`), so any link the controller
  builds with its own port still works through the tunnel.

## Agent forwarding

`ForwardAgent yes` lets commands on the builder use the laptop's keys, for example to SSH on to
hosts as `a_autoprov` or to reach GitHub. The private keys stay on the laptop, as
[Secure Identity](/docs/standards/secure-identity/) requires. Forward the agent only to the
builder, not to hosts in general.

The keys have to be loaded in the laptop's agent. `IdentityFile` alone doesn't load them.

```bash
ssh-add ~/.ssh/<github> ~/.ssh/<automation>    # on the laptop
ssh-add -l                                     # on the builder: both keys should be listed
```

## Web UIs through the tunnel

| Service | Browse | Target |
|---|---|---|
| OPNsense | `https://localhost:8441` | `10.20.99.1:443` |
| Wireless AP | `https://localhost:8442` | `10.20.99.9:443` |
| Access switch | `https://localhost:8443` | `10.20.99.10:443` |
| Proxmox, management hypervisor | `https://localhost:8444` | `10.20.99.21:8006` |
| Proxmox, tenant hypervisor | `https://localhost:8445` | `10.20.99.22:8006` |
| Omada controller | `https://localhost:8043/independent/index.html#login` | `10.20.99.40:8043` |
| Artifact server | `http://localhost:8080` | `10.20.99.95:80` |

Every target answered from the builder on 2026-09-16. The devices present their own certificates,
which won't match `localhost`, so expect a certificate warning. For the rest of the site's
endpoints, see [Important URLs](/docs/runbook/substrate/network/important-urls/).

---

## Backup: the operator port

If the travel router or the builder's `enp1s0` is the problem, go in by wire instead. Plug the
laptop into `gigabitEthernet 1/0/2` on the access switch. That port is untagged VLAN 99 and is
kept free for this. The laptop is then on the management segment itself, so it needs no
tunnels: browse the IPs in [Important URLs](/docs/runbook/substrate/network/important-urls/) directly, and
SSH to the builder at `10.20.99.95`.

The full procedure, including which port and why no other free port will do, is in
[Wireless AP → Get onto the management network by wire](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/#1-get-onto-the-management-network-by-wire).
OPNsense's Kea DHCP serves VLAN 99, and inventory declares the pool as `10.20.99.200–230`, so
the laptop should get a lease. If it doesn't, set an address by hand, as in
[Address the laptop](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/#address-the-laptop).

**This path goes through the access switch.** It's the right backup for everyday work and for
AP recovery. It is not a way to stay connected while the switch itself is rebooted or reset.
