# reachwhy design

> **Status: design only.** Nothing in this document is implemented yet, except the JSON Schemas in `schemas/`, the synthetic case in `corpus/` and the hygiene tooling in `scripts/ci/`. Property names marked *to verify* must be checked against the Azure documentation when each rule is implemented.

## Goal

A **read-only** desktop app (planned stack: Tauri 2 + Rust) that takes two Azure resources, an origin and a target behind a private endpoint, and shows the path **hop by hop**, each hop with a state and an **exact cause**.

Positioning: control-plane diagnosis with an exact cause per hop for PaaS origins.

## Scope of the first version

| Area | Included |
|---|---|
| Cloud | Azure public cloud only. |
| Origins (3) | Function App (`Microsoft.Web/sites`, kind `functionapp*`), App Service (`Microsoft.Web/sites`, kind `app*`), Container App (`Microsoft.App/containerApps` and its managed environment). |
| Targets (3) | Storage (`blob`, `file`, `queue`, `table`, `dfs`), Key Vault (`vault`), Azure SQL Database (`sqlServer`), all **behind a private endpoint**. |
| Hops | origin (VNet integration) → dns → route (UDR, peering) → nsg → pe → target-net → rbac. |
| States | green, red, amber (with the reason it could not be verified). |
| Input | Two resources (by id or picked from a list) over a snapshot. |
| Output | Overall verdict plus a list of hops with cause, evidence (ARM path and the value read) and a suggested fix as text. Nothing is executed. |
| Collector | The user's own `az login`; read-only Resource Graph / ARM queries; local JSON snapshot. |

## Out of scope

- AWS and other clouds; Azure Government and Azure China (zone names differ).
- **Any write to Azure.** A "fix" is text and an example command that the user runs.
- Active tests from the origin (tcpping, name resolution through Kudu, running commands in the app): they need data-plane access and credentials.
- Real DNS resolution from inside the VNet: it is inferred from configuration; what cannot be inferred is amber.
- Advanced DNS chains (Private Resolver rulesets, Azure Firewall DNS proxy, Virtual WAN, hybrid forwarders): a custom DNS server on the VNet is amber with an explanation. See [ROADMAP.md](../ROADMAP.md).
- Azure Firewall / NVA rule evaluation: amber ("there is an NVA or firewall in the route; its rules are not evaluated").
- Data content (blobs, secrets, SQL tables) and the data plane in general.
- SQL contained users (`CREATE USER ... FROM EXTERNAL PROVIDER`): that is a T-SQL check, so the SQL data-role hop is always amber.
- Multi-tenant at once, snapshot editing, telemetry, auto-update, signed installers.

## Architecture

```
 az login (user)
        │
        ▼
 ┌──────────────┐  local JSON   ┌──────────────┐  verdict   ┌───────────────────────────┐
 │ Collector    │──────────────▶│  Snapshot    │───────────▶│ UI (webview, no network,  │
 │ (read-only)  │  (versioned)  │  .json       │            │ no filesystem access)     │
 └──────────────┘               └──────┬───────┘            └─────────────▲─────────────┘
   az rest → Resource Graph /          ▼                                  │
   ARM GET                       ┌──────────────┐                         │
                                 │ Rule engine  │─────────────────────────┘
                                 │ (pure fn)    │
                                 └──────────────┘
```

- **Collector:** runs `az` as a child process with fixed argument arrays (no shell, no interpolation of user text). It only issues (a) Resource Graph queries embedded in the code and (b) GETs to specific ARM paths; a test fails if any other verb or URL appears. The code never handles a token: `az` does.
- **Snapshot:** pruned JSON (only the properties the rules use) with `schemaVersion` and a `synthetic` flag. Real snapshots live in the user's app data directory, never in a git work tree; the collector rejects an output path inside a git repository. A "sanitize" option (hashed subscription and tenant ids, stable renaming, reassigned IPs) is planned before anything is shared.
- **Engine:** `analyze(snapshot, pair, ruleset) -> verdict`. No I/O, no clock, no network: deterministic, which is what makes the corpus usable as a regression suite.
- **UI:** the webview has no network or filesystem access and can only call a closed list of commands (`load_snapshot`, `analyze`, `list_resources`, `collect`).

## Planned permissions

| Need | Permission | Note |
|---|---|---|
| List resources and properties (sites, container apps, managed environments, storage, key vaults, SQL servers, private endpoints, VNets, NSGs, route tables, private DNS zones and links) | **Reader** on each relevant subscription or resource group | Resource Graph only returns what the user can read. |
| Read role assignments and role definitions | Included in Reader (*to verify* against the built-in role definition) | Read through the `authorizationresources` table of Resource Graph. |
| Private zones in a hub / connectivity subscription | Reader there too | If not visible, the hop is **amber** ("zone not visible"), never red. |
| Anything else | none | No Contributor, no `list keys`, no `POST .../config/appsettings/list`, no data plane. |

App settings are deliberately not read: they can contain secrets and reading them needs more permissions. Settings that are not visible in `siteConfig` therefore lead to amber.

Resource Graph caveats from its documentation: queries are throttled, data is not strongly consistent (indexed with a short delay), and some properties may be missing because it uses the latest non-preview API of each provider.

## Data model

### Snapshot

Defined in [`schemas/snapshot.schema.json`](../schemas/snapshot.schema.json). Top-level fields: `schemaVersion`, `kind` (`reachwhy.snapshot`), `id`, `synthetic`, `collectedAt`, `collector`, `visibility` (readable and unreadable subscriptions), `resources`, `roleAssignments`, `roleDefinitions`, `declared` (user-declared facts such as DNS forwarders) and the optional `evidence`.

Example: [`corpus/demo-basic-01/snapshot.json`](../corpus/demo-basic-01/snapshot.json).

### Verdict (planned output)

```jsonc
{
  "pair": { "origin": "<id>", "target": "<id>", "targetSubresource": "blob" },
  "overall": "red",            // red if any hop is red; amber if no red and some amber; green only if all green
  "firstRedHop": "dns",
  "hops": [
    { "id": "dns", "state": "red", "code": "DNS_ZONE_NOT_LINKED",
      "cause": "Zone privatelink.blob.core.windows.net is not linked to vnet-demo (integration VNet of func-demo).",
      "evidence": [ { "kind": "arm", "resource": "<zone id>", "path": "virtualNetworkLinks", "value": "[]" } ],
      "fixHint": "Link the zone to vnet-demo (run by the user).",
      "sources": [ "<official documentation URL>" ] }
  ],
  "annotations": []
}
```

### Runtime evidence (`evidence.runtime`, optional)

Observations the **user** adds to a snapshot, for example the output of a probe run inside the workload. reachwhy never runs probes itself; it only imports them. Rules:

1. Runtime evidence never creates green or red on its own for control-plane hops. It can resolve an amber (for example a custom DNS server whose answer matches the private endpoint IP, observed from the origin).
2. HTTP 401/403 with working TCP/TLS suggests the private path works and the problem is identity or data role: amber hint, never red by itself.
3. A contradiction with the control plane is amber `EVIDENCE_CONFLICT`, showing both pieces of evidence.
4. `observedAt` and `observedFrom` are mandatory; stale observations are amber `EVIDENCE_STALE`.

## Hop rules

Every rule has a **stable code** and returns a state plus evidence (ARM path and value). Green needs positive evidence; a missing property or an unreadable scope is amber; red needs direct evidence of the failure. All hops are evaluated and `firstRedHop` is reported in hop order.

| Hop | What is read | Red codes | Amber codes |
|---|---|---|---|
| origin (Function / App Service) | `virtualNetworkSubnetId`, subnet delegation, `vnetRouteAllEnabled` | `ORIGIN_NO_VNET_INTEGRATION` (target is private-only), `ORIGIN_SUBNET_NOT_DELEGATED` | `ORIGIN_ROUTE_ALL_OFF` |
| origin (Container App) | managed environment `vnetConfiguration.infrastructureSubnetId` | `ORIGIN_ENV_NOT_IN_VNET` | |
| dns | expected `privatelink.*` zone for the endpoint's group id, zone links to the integration VNet, A record vs endpoint IP, VNet DNS servers | `DNS_ZONE_MISSING`, `DNS_ZONE_NOT_LINKED`, `DNS_RECORD_MISSING`, `DNS_RECORD_STALE_IP`, `DNS_ZONE_EMPTY_NO_FALLBACK` | `DNS_ZONE_NOT_VISIBLE`, `DNS_CUSTOM_SERVER` |
| route | route table on the integration subnet, peerings | `ROUTE_BLACKHOLE`, `ROUTE_NO_PEERING`, `ROUTE_PEERING_NOT_CONNECTED` | `ROUTE_VIA_NVA`, `ROUTE_PE_SLASH32_BYPASS` (informational) |
| nsg | outbound rules on the integration subnet; inbound rules on the endpoint subnet when network policies apply | `NSG_OUTBOUND_DENY`, `NSG_INBOUND_DENY_PE_SUBNET` | `NSG_UNRESOLVED_TAG` |
| pe | connection state and provisioning state, seen from both sides | `PE_PENDING_APPROVAL`, `PE_REJECTED`, `PE_DISCONNECTED`, `PE_PROVISIONING_FAILED` | `PE_ONE_WAY` |
| target-net | `publicNetworkAccess`, `networkAcls` | `TARGET_PUBLIC_DISABLED_DNS_PUBLIC` (derived from a red DNS hop) | |
| rbac | origin managed identity; role assignments resolved by role **name**; Key Vault RBAC mode or access policies | `RBAC_NO_IDENTITY`, `RBAC_NO_DATA_ROLE`, `RBAC_CONTROL_PLANE_ONLY`, `KV_ACCESS_POLICY_MISSING` | `RBAC_SQL_CONTAINED_USER_UNVERIFIABLE` (always, for SQL), `RBAC_CONDITION_PRESENT` |

Overall verdict: `green` requires every hop green. With any amber the result is `amber` and is shown as "no failure found, but N hops could not be verified", never as "OK". Each amber carries `whyUnverifiable` and `howToVerify`, for example a command the user can run from a VM inside the integration VNet:

```powershell
Resolve-DnsName stdemo001.blob.core.windows.net -Type A | Select-Object Name, IPAddress
# Expected: a 10.x private endpoint IP, not a public IP.
```

## Corpus

`corpus/` is a set of synthetic "network repro" cases. Each folder has:

1. `snapshot.json`: the synthetic environment;
2. `expected.json`: expected overall verdict, first red hop and the state of the hops that matter (schema: [`schemas/expected.schema.json`](../schemas/expected.schema.json));
3. `SOURCE.md`: where the scenario comes from, read date and reviewer.

Rules:

- **Provenance:** cases are reconstructed only from public material (official troubleshooting articles, public threads) or written from scratch, always with our own synthetic data. A case never starts from a real environment, not even anonymized. No text is copied from articles.
- **Naming:** `<source>-<topic>-<variant>-<NN>`, where source is `ms` (official documentation), `ms-qa` (community Q&A) or `synthetic`. Folder name equals `snapshot.id`. The existing `demo-basic-01` predates this convention.
- **`expected.json`:** `hops` only asserts what matters; `any` means "not asserted". Amber cases are welcome: they document what the engine cannot know. A case without human review (`reviewedBy`) is not marked as official.
- **Versioning:** `schemaVersion` is semver. Minor = new optional fields; major = breaking change with a migration script that rewrites every case and updates `corpus/_meta/schema-version`. `minRulesetVersion` says from which engine version a case is valid. Any change to an expected verdict needs an entry in `corpus/CHANGELOG.md` with the reason and a second reviewer.
- **Hygiene:** every case must pass `python scripts/ci/check_hygiene.py corpus`.

Planned tests (need the engine): run `analyze` over every case and compare `overall`, `firstRedHop` and asserted hops; fail if a `mustNotBeGreen` hop comes out green; require every rule code to appear in at least one red or amber case and one matching green case.

## Planned improvements

> **Planned, not implemented.** Ordered by phase. Effort: S (small), M (medium), L (large). Every item keeps the read-only promise: reachwhy itself needs only **Reader**. Where a fact is only visible in app settings (which Reader cannot list) the item says so and relies on user-declared input or user-supplied runtime evidence, never on broader permissions. Property names marked *to verify* must be checked when implemented (including whether Resource Graph exposes them or an ARM GET is needed).

### Phase 1: control-plane reads that remove ambers (Reader only)

| # | Improvement | Hops / codes | Effort | Source |
|---|---|---|---|---|
| 1 | **Fallback to internet on zone links.** Read `resolutionPolicy` (`Default` or `NxDomainRedirect`) on `privateDnsZones/virtualNetworkLinks`. With `NxDomainRedirect`, a missing record falls back to public resolution instead of NXDOMAIN. Also detect a linked `privatelink.*` zone that has no record for the target: without fallback, it answers NXDOMAIN for every resource of that type that is not in the zone. | dns: refines `DNS_ZONE_EMPTY_NO_FALLBACK`; with fallback, the result depends on the target's public network access (`target-net`) | S | [Fallback to internet for Azure Private DNS zones](https://learn.microsoft.com/en-us/azure/dns/private-dns-fallback) |
| 2 | **Site DNS and routing properties.** Read `dnsConfiguration.dnsServers` (overrides the VNet DNS servers for that app) and `outboundVnetRouting` (`allTraffic`, `applicationTraffic`, `contentShareTraffic`), plus the legacy `vnetRouteAllEnabled`. Site properties override the equivalent app settings (`WEBSITE_DNS_SERVER`, `WEBSITE_VNET_ROUTE_ALL`), but those app settings are not readable with Reader: when the properties are absent the hop stays amber. | origin: `ORIGIN_ROUTE_ALL_OFF`; dns: `DNS_CUSTOM_SERVER` | S–M | [Name resolution in App Service](https://learn.microsoft.com/en-us/azure/app-service/overview-name-resolution), [Configure virtual network integration routing](https://learn.microsoft.com/en-us/azure/app-service/configure-vnet-integration-routing) |
| 3 | **Zones and records in another subscription.** Query private DNS records through the Resource Graph `dnsresources` table and zone links through `resources`, across every subscription the user can read (for example a hub subscription). Without Reader on the hub, the result stays amber `DNS_ZONE_NOT_VISIBLE`, never red. | dns: `DNS_ZONE_MISSING`, `DNS_ZONE_NOT_VISIBLE`, `DNS_RECORD_MISSING`, `DNS_RECORD_STALE_IP` | S | [Private DNS information in Azure Resource Graph](https://learn.microsoft.com/en-us/azure/dns/private-dns-arg) |

### Phase 2: the Functions host storage account

The host storage account is named in the `AzureWebJobsStorage` app setting, which Reader cannot list. These items therefore need the user to declare which account is the host storage (a new optional field under `declared`, schema minor version) or to supply it as runtime evidence (item 6).

| # | Improvement | Hops / codes | Effort | Source |
|---|---|---|---|---|
| 4 | **Host data roles.** For an identity-based host connection, check *Storage Blob Data Owner* (minimum for `AzureWebJobsStorage`) and *Storage Table Data Contributor* (diagnostic events; without it the docs describe log warnings, so amber or informational rather than red). Blob triggers also need *Storage Queue Data Contributor* for poison blobs; Durable Functions needs Blob, Queue and Table data roles. Which triggers an app uses is not visible from the control plane, so trigger-dependent roles are declared by the user or stay amber. | rbac: `RBAC_NO_DATA_ROLE`, `RBAC_CONTROL_PLANE_ONLY` (new host-specific codes *to define*) | M | [Define connections: required permissions](https://learn.microsoft.com/en-us/azure/azure-functions/manage-connections) |
| 5 | **Host storage over the network.** Private endpoints for the `blob`, `file` and `table` subresources (plus `queue` for Durable Functions); content share routing (`outboundVnetRouting.contentShareTraffic`, legacy `vnetContentShareEnabled`; the `WEBSITE_CONTENTOVERVNET` app setting is not readable); and NSG/firewall rules on the integration subnet that allow ports 443 **and 445**. | pe, dns, nsg (`NSG_OUTBOUND_DENY` extended to port 445), origin | M | [Restrict your storage account to a virtual network](https://learn.microsoft.com/en-us/azure/azure-functions/configure-networking-how-to), [Configure virtual network integration routing](https://learn.microsoft.com/en-us/azure/app-service/configure-vnet-integration-routing) |

### Phase 3: user-run evidence script

| # | Improvement | Hops / codes | Effort | Source |
|---|---|---|---|---|
| 6 | **Evidence script the user runs.** Published as plain PowerShell and bash that the user reads and runs inside the workload (for example the Kudu or SSH console), producing a JSON file that matches `evidence.runtime`. reachwhy never runs it. Rules: read-only (DNS lookup, TCP connect, optional TLS handshake); no tokens, no secret values, no app setting values (at most a list of setting *names* the user chooses to include); writes only to stdout or a file the user names; output is short, human-readable JSON the user reviews before importing. Opening a console inside the workload needs more than Reader; that is the user's own action, outside reachwhy. | all hops through `evidence.runtime` (see [Runtime evidence](#runtime-evidence-evidenceruntime-optional)) | M | [Azure Functions networking options: troubleshooting](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options) |

### Phase 4: more origins

| # | Improvement | Hops / codes | Effort | Source |
|---|---|---|---|---|
| 7a | **Container Apps with custom DNS.** When the environment's VNet uses a custom DNS server, the docs require forwarding unresolved queries to `168.63.129.16`; that forwarder chain is not visible from the control plane, so it stays amber unless declared or shown by runtime evidence. | origin, dns: `DNS_CUSTOM_SERVER` | L | [Private endpoints and DNS in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/private-endpoints-with-dns) |
| 7b | **Flex Consumption as an origin.** Flex Consumption requires the subnet delegation `Microsoft.App/environments`, unlike Elastic Premium and Dedicated plans. Until Flex is supported, the origin rule must not report `ORIGIN_SUBNET_NOT_DELEGATED` for a Flex app; it reports amber instead. | origin: `ORIGIN_SUBNET_NOT_DELEGATED` | M | [Azure Functions networking options](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options) |

## Related tools

Read on 2026-11-12; not exhaustive, and to be re-checked before any release. Azure Network Watcher (Connection Troubleshoot, Connection Monitor) and Azure Virtual Network Manager's Network Verifier did not list Function Apps, Container Apps or App Service as sources in their documentation at that date. Community tools such as [azlinks](https://github.com/bmw99x/azlinks) map topology and some findings, and runtime probes such as [azpe](https://github.com/nukabo/azpe) observe DNS/TCP/TLS from inside the workload; the latter is complementary and could feed `evidence.runtime`.
