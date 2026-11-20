# Roadmap

Everything below is **planned**. None of it exists yet unless it is listed under "Done". Order can change; there are no dates.

## Done

- JSON Schemas for the snapshot and for the expected verdict (`schemas/`, v1.0.0), including the optional `evidence.runtime` field.
- First synthetic corpus case: `corpus/demo-basic-01` (DNS zone not linked to the integration VNet, no data role).
- Synthetic-data hygiene check with tests, pre-commit hook and pinned gitleaks, enforced in CI.
- Phase 1 prototype in Python (`src/reachwhy/`, `tests/`): dns hop (fallback to internet, site and VNet DNS servers, zones in other subscriptions) and origin application routing, over a local snapshot, with 10 more synthetic corpus cases. *In a pull request; not run against real Azure data (there is no collector yet).*

## Next: first usable version

Scope: Azure only, 3 origins × 3 targets (see [docs/design.md](docs/design.md)).

- [ ] Rule engine in Rust as a pure function over a snapshot, with the hop rules and codes from the design (the Python prototype is the executable reference; phase 1 rules only so far).
- [ ] Corpus tests for the full engine (the prototype already compares the origin and dns hops with `expected.json`).
- [ ] At least 8 synthetic corpus cases reconstructed from public troubleshooting articles, each with a green twin.
- [ ] Read-only collector using the user's `az login` (Resource Graph and ARM GETs only), writing snapshots outside any git repository.
- [ ] Desktop UI (Tauri) with a demo mode on synthetic data, no Azure session needed.
- [ ] Demo recording made from synthetic data only.
- [ ] CI for Rust and JavaScript dependencies and corpus tests (see [docs/pending-ci.md](docs/pending-ci.md)).

## Planned improvements (by phase)

Details, affected hops and public sources: [docs/design.md](docs/design.md#planned-improvements). All of them keep reachwhy at Reader only.

**Phase 1: control-plane reads (Reader only)** — prototype done, in a pull request
- [x] (S) Fallback to internet (`resolutionPolicy: NxDomainRedirect`) on private zone links, and linked `privatelink.*` zones that have no record for the target.
- [x] (S–M) Site properties `dnsConfiguration` and `outboundVnetRouting` / legacy `vnetRouteAllEnabled`.
- [x] (S) Private zones and records in other readable subscriptions through Resource Graph `dnsresources`.

**Phase 2: Functions host storage (needs a user-declared host storage account)**
- [ ] (M) Host data roles: Storage Blob Data Owner, Storage Table Data Contributor, and trigger-dependent roles.
- [ ] (M) Host storage network path: blob, file and table private endpoints (plus queue for Durable Functions), content share routing, ports 443 and 445.

**Phase 3: user-run evidence**
- [ ] (M) Read-only PowerShell and bash script that the user runs inside the workload to produce `evidence.runtime`; reachwhy never runs it.

**Phase 4: more origins**
- [ ] (L) Container Apps environments with custom DNS.
- [ ] (M) Flex Consumption as an origin (subnet delegation `Microsoft.App/environments`); until then, amber instead of a false red.

## Later

- [ ] Import runtime evidence from probes run inside the workload (`evidence.runtime` adapters).
- [ ] DNS chain engine: Azure DNS Private Resolver rulesets and loop detection, Azure Firewall DNS proxy, Virtual WAN, declared hybrid forwarders.
- [ ] Azure Monitor private link scope case (`privatelink.monitor.azure.com`).
- [ ] Read-only extension points, design first: a PR check for infrastructure-as-code DNS regressions, a NAT egress cost annotation, a read-only MCP server over the engine.
- [ ] Other clouds.
