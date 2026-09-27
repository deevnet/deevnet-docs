---
title: "Recovery"
weight: 7
bookCollapseSection: true
---

# Recovery

Getting your tenant back when something is lost — on your side, or on the site's. The site's own
recovery (hypervisors, the router, the Builder) is the operator's, and is in
[Substrate Operations](/docs/runbook/substrate/recovery/). These pages are what **you** do.

Two facts do most of the work:

- **Your Terraform state proves who your tenant is.** It holds your index and every secret you were
  issued. Applying it against a site that lost track of you brings you back with the same index and
  the same keys ([Terraform provider → Restore instead of recreate](/docs/platforms/deevnet-software/terraform-provider/#restore-instead-of-recreate)).
- **The site keeps a copy of most of your secrets**, sealed, and the operator can hand them back.
  It does not keep your API token.

| What happened | Page |
|---|---|
| The site was rebuilt, or lost part of itself | [After a site rebuild](after-a-site-rebuild/) |
| You lost your state, or the credentials to reach it | [Lost state or credentials](lost-credentials/) |
