# Contributing to reachwhy

Thanks for your interest. reachwhy is **pre-alpha**: there is no application code yet, so the most useful contributions today are on the design, the schemas and the synthetic corpus.

## Ground rules

- **Synthetic data only.** Never commit real Azure data: no real subscription or tenant ids, resource names, IPs, hostnames or tokens, not even anonymized. Use the conventions below.
- **Read-only by design.** Proposals that make reachwhy write to Azure, read app settings or use the data plane are out of scope (see [docs/design.md](docs/design.md#out-of-scope)).
- **No invented behavior.** Docs describe what exists; planned work is labeled as planned.
- Be kind. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting set up

bash:

```sh
scripts/install-hooks.sh
python -m unittest discover -s scripts/ci/tests -v
python scripts/ci/check_hygiene.py corpus schemas docs
python -m pip install pytest jsonschema   # prototype tests
python -m pytest
```

PowerShell:

```powershell
./scripts/install-hooks.ps1
python -m unittest discover -s scripts/ci/tests -v
python scripts/ci/check_hygiene.py corpus schemas docs
python -m pip install pytest jsonschema   # prototype tests
python -m pytest
```

Installing [gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 is recommended; the hook runs it when present. See [docs/tooling.md](docs/tooling.md).

## Synthetic data conventions

Enforced by `scripts/ci/check_hygiene.py`:

- IPv4 only in `10.20.0.0/16` or the documentation ranges `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`.
- Resource groups, resource names, subnets and record names contain `demo` or `example`.
- GUIDs are all zeros, optionally with a two-hex-digit suffix (`00000000-0000-0000-0000-0000000000a1`).
- Hostnames only under the allowed Azure suffixes, with a `demo`/`example` label, or canonical `privatelink.*` zone names.
- Snapshots set `"synthetic": true`. Files named `*.raw.json` or under `snapshots/` are rejected.

## Adding a corpus case

1. Pick a public troubleshooting scenario (or write one from scratch). Do not copy text from the article.
2. Create `corpus/<source>-<topic>-<variant>-<NN>/` with `snapshot.json`, `expected.json` and `SOURCE.md` (link, title, section, read date, reviewer). See [docs/design.md](docs/design.md#corpus) for the format.
3. In `expected.json`, assert only the hops that matter (`any` = not asserted). Add a green twin if the rule does not have one.
4. Run `python scripts/ci/check_hygiene.py corpus/<id>` and add an entry to `corpus/CHANGELOG.md`.

## Pull requests

- One topic per PR, with a clear description of what changes and why.
- CI (`gitleaks` and `hygiene`) must pass.
- Changes to `.github/workflows/` need a justification in the PR and a maintainer review.
- Report security issues privately, not in a PR or issue: see [SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
