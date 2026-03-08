---
title: "Core Services"
weight: 3
---

# Core Services Implementation

How each substrate implements the DNS authority model defined in [Core Services Architecture](/docs/architecture/substrate/management-plane/core-services/).

---

## dvntm (Mobile Lab)

### Production Mode

- OPNsense Core Router is DNS/DHCP authority
- Provisioner's dnsmasq is disabled
- Provisioner uses reserved IP at low end of management subnet (e.g., `192.168.10.95`)

DNS records held in Core Router:
```
provisioner-01.mgmt.deevnet.net  A     192.168.10.95
artifacts.mgmt.deevnet.net       CNAME provisioner-01.mgmt.deevnet.net
pxe.mgmt.deevnet.net             CNAME provisioner-01.mgmt.deevnet.net
tftp.mgmt.deevnet.net            CNAME provisioner-01.mgmt.deevnet.net
```

### Bootstrap Mode

- Provisioner's dnsmasq is DNS/DHCP/gateway authority
- Provisioner uses gateway IP (e.g., `192.168.10.1`)
- Core Router may not exist

DNS records held in provisioner dnsmasq:
```
provisioner-01.mgmt.deevnet.net  A     192.168.10.1
artifacts.mgmt.deevnet.net       CNAME provisioner-01.mgmt.deevnet.net
pxe.mgmt.deevnet.net             CNAME provisioner-01.mgmt.deevnet.net
tftp.mgmt.deevnet.net            CNAME provisioner-01.mgmt.deevnet.net
```

---

## dvnt (Production)

_Placeholder — implementation details to be documented when dvnt substrate is built._
