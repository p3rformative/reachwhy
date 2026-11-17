# Roadmap

Everything below is **planned**. None of it exists yet unless it is listed under "Done". Order can change; there are no dates.

## Done

- JSON Schemas for the snapshot and for the expected verdict (`schemas/`, v1.0.0), including the optional `evidence.runtime` field.
- First synthetic corpus case: `corpus/demo-basic-01` (DNS zone not linked to the integration VNet, no data role).
- Synthetic-data hygiene check with tests, pre-commit hook and pinned gitleaks, enforced in CI.

## Next: first usable version

Scope: Azure only, 3 origins × 3 targets (see [docs/design.md](docs/design.md)).

- [ ] Rule engine in Rust as a pure function over a snapshot, with the hop rules and codes from the design.
- [ ] Corpus tests: run the engine over every case and compare with `expected.json`.
- [ ] At least 8 synthetic corpus cases reconstructed from public troubleshooting articles, each with a green twin.
- [ ] Read-only collector using the user's `az login` (Resource Graph and ARM GETs only), writing snapshots outside any git repository.
- [ ] Desktop UI (Tauri) with a demo mode on synthetic data, no Azure session needed.
- [ ] Demo recording made from synthetic data only.
- [ ] CI for Rust and JavaScript dependencies and corpus tests (see [docs/pending-ci.md](docs/pending-ci.md)).

## Later

- [ ] Import runtime evidence from probes run inside the workload (`evidence.runtime` adapters).
- [ ] DNS chain engine: Azure DNS Private Resolver rulesets and loop detection, Azure Firewall DNS proxy, Virtual WAN, declared hybrid forwarders.
- [ ] Azure Monitor private link scope case (`privatelink.monitor.azure.com`).
- [ ] Read-only extension points, design first: a PR check for infrastructure-as-code DNS regressions, a NAT egress cost annotation, a read-only MCP server over the engine.
- [ ] Other clouds.
