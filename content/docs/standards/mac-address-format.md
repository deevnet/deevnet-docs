---
title: "MAC Address Format"
weight: 4
---

# MAC Address Format Standard

## Rule

All MAC addresses in Deevnet inventory and configuration MUST use:
- **lowercase** hex digits (a-f, not A-F)
- **Colon separators** (`:`, not `-`)

## Examples

**Correct:**
```yaml
mac: "bc:24:11:2e:26:4e"
mac: "dc:a6:32:c3:b4:bc"
```

**Incorrect:**
```yaml
mac: "BC:24:11:2E:26:4E"  # uppercase
mac: "bc-24-11-2e-26-4e"  # dashes
```

## Rationale

Deevnet uses lowercase to match Unix tooling conventions:
- `ifconfig`, `ip link`, and most Linux utilities display MAC addresses in lowercase
- Copy-paste from system output works without transformation
- Consistent with what operators see when troubleshooting

IEEE 802 and RFC 7042 documentation examples use uppercase, but this is a
documentation convention rather than a technical requirement. We prioritize
practical alignment with the Unix ecosystem over formal documentation style.

## Runtime Normalization

Some downstream systems expect specific formats:
- The OPNsense DHCP role normalizes to uppercase at runtime (`| upper`)
- PXE/TFTP infrastructure generates both upper and lowercase GRUB config
  filenames to handle firmware variations

These transformations happen automatically. The source of truth in inventory
remains lowercase.

## Location

MAC addresses belong in `infrastructure.interfaces.<name>.mac` as part
of host identity per the [Identity vs Intent](../identity-vs-intent/) standard.

## Related Standards

- [MAC Namespace Specification](../mac-naming/) - Defines the semantic structure
  of MAC addresses (environment, role, instance encoding)

This document defines **how** MAC addresses are formatted. The namespace
specification defines **what** values they contain.
