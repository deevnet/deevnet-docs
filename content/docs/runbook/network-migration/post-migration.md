---
title: "Post-Migration"
weight: 6
---

# Post-Migration

After all steps complete and connectivity is verified:

1. **Run automated post-migration validation:**
   ```bash
   cd ansible-collection-deevnet.net
   make postcheck
   ```
   Validates OPNsense VLANs, switch database/trunk, device reachability, gateway IPs, and builder state. All checks should show `[PASS]`.

2. **Run DNS and DHCP roles** (must run before vault encryption):
   ```bash
   cd ansible-collection-deevnet.net
   make dns
   make dhcp
   ```

3. **Re-encrypt vault files:**
   ```bash
   cd ansible-inventory-deevnet
   make vault
   ```

4. **Remove old network config:**
   - Delete old 192.168.10.0/23 Kea DHCP subnet (if not already removed)
   - Remove temp VLAN 99 DHCP pool (if not already removed)
   - Remove old 192.168.10.0 LAN interface from OPNsense (Interfaces → LAN → clear IP or reassign)
   - Remove any old static routes referencing 192.168.10.x

5. **Ongoing switch management** — use the `switch` target for day-2 operations:
   ```bash
   make switch
   ```

6. **Reconfigure devices still on old static IPs:**

   Devices on VLAN 99 ports that still have old 192.168.10.x static IPs are on the same L2 segment as the builder but on a different subnet. Use a temporary secondary IP on the builder to reach them.

   **Proxmox hypervisor (hv01) — `192.168.10.21` → `10.20.99.21`:**

   From the builder:
   ```bash
   # Add temp IP on old subnet (same VLAN 99 L2)
   sudo ip addr add 192.168.10.95/24 dev enp4s0

   # Verify HV is reachable
   ping -c 1 192.168.10.21

   # SSH to Proxmox and reconfigure
   ssh root@192.168.10.21
   ```

   On the Proxmox host, edit the network config:
   ```bash
   # Edit /etc/network/interfaces (Proxmox/Debian)
   vi /etc/network/interfaces
   ```

   Change the `vmbr0` bridge IP from `192.168.10.21` to the target:
   ```
   auto vmbr0
   iface vmbr0 inet static
       address 10.20.99.21/24
       gateway 10.20.99.1
       bridge-ports enp0s31f6
       bridge-stp off
       bridge-fd 0
   ```

   Apply (this will drop the SSH session):
   ```bash
   ifreload -a
   ```

   Back on the builder, clean up and verify:
   ```bash
   # Remove temp IP
   sudo ip addr del 192.168.10.95/24 dev enp4s0

   # Verify HV at new IP
   ping -c 2 10.20.99.21

   # SSH to verify
   ssh root@10.20.99.21
   ```

   Repeat this pattern for any other devices on management ports with old static IPs.

7. **Update documentation** — verify network-reference.md reflects the new state

---

## Management Access via SSH Tunnels

The management VLAN (99) is not accessible from wireless clients. To reach management web UIs from a desktop, use SSH port forwarding through the builder's transit interface (`enp1s0`, DHCP on upstream network).

The builder's transit IP can be found with: `ip -4 addr show enp1s0` on the builder.

| Service | Target | SSH Tunnel Command | Browser URL |
|---------|--------|-------------------|-------------|
| OPNsense GUI | 10.20.99.1:443 | `ssh -L 8443:10.20.99.1:443 a_autoprov@<builder-transit-ip>` | `https://localhost:8443` |
| Omada Controller | 10.20.99.95:8043 | `ssh -L 8043:10.20.99.95:8043 a_autoprov@<builder-transit-ip>` | `https://localhost:8043` |
| Proxmox GUI | 10.20.99.21:8006 | `ssh -L 8006:10.20.99.21:8006 a_autoprov@<builder-transit-ip>` | `https://localhost:8006` |
| AP Standalone UI | 10.20.99.9:80 | `ssh -L 8080:10.20.99.9:80 a_autoprov@<builder-transit-ip>` | `http://localhost:8080` |
| Switch SSH | 10.20.99.10:22 | `ssh -L 2222:10.20.99.10:22 a_autoprov@<builder-transit-ip>` | `ssh -p 2222 <switch_user>@localhost` |

{{< hint info >}}
**Switch SSH quirks:** The SG2218 requires legacy SSH options: `-o PubkeyAuthentication=no -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa -o RequiredRSASize=0 -o StrictHostKeyChecking=no`
{{< /hint >}}

{{< hint info >}}
**Future improvement:** Replace SSH tunnels with a management jumphost VM on VLAN 99 with a desktop environment or web proxy.
{{< /hint >}}
