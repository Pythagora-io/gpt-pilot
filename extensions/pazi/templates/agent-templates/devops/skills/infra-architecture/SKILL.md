---
name: infra-architecture
description: Infrastructure architecture overview. Use BEFORE starting any infrastructure work to understand how services connect. Contains system topology, service locations, networking, and access paths. Does NOT contain procedures (see infra-deployment), issues (see infra-debugging), or monitoring details (see infra-monitoring). Triggers on architecture questions, system overview, "how does X connect to Y", or when starting unfamiliar infra work.
---

# Infrastructure Architecture

This skill is populated during onboarding and updated as you learn more about the infrastructure.

## Topology

<!-- Replace this section with the user's actual architecture diagram -->
<!-- Example format:

```
┌──────────── Cloud Provider ──────────────┐
│  Load Balancer → Web Servers             │
│  Database cluster                        │
│  Cache layer                             │
└──────────────────────────────────────────┘
```
-->

_Not yet configured. Run onboarding or describe your architecture to populate this._

## Services

<!-- List each service with: name, where it runs, port, source code location -->

| Service   | Where     | Port   | Source |
| --------- | --------- | ------ | ------ |
| _example_ | _AWS EC2_ | _3000_ | _api/_ |

## Databases

<!-- For each database: type, host, what it stores, access method -->

| Database  | Type      | Purpose    | Access                            |
| --------- | --------- | ---------- | --------------------------------- |
| _example_ | _MongoDB_ | _App data_ | _credentials in .credentials.env_ |

## Networking

<!-- How traffic flows: DNS → LB → services, internal networking, ports -->

_Not yet configured._

## Access Paths

<!-- How to reach each system — prefer Pipedream integrations where available -->

| System    | How to access                                           |
| --------- | ------------------------------------------------------- |
| _example_ | _Pipedream integration / API token in .credentials.env_ |

## Data Dependencies

<!-- Which service depends on which -->

| Service   | Depends on                      |
| --------- | ------------------------------- |
| _example_ | _Database, Cache, External API_ |

## Reference Files

- `references/servers.md` — Server inventory with IPs, roles, and SSH details
- `references/environment-vars.md` — Environment variables and config locations
