# Security policy

## Supported versions

reachwhy is pre-alpha and has no releases yet. Security fixes go to the `main` branch.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub Security Advisories: open the repository's **Security** tab and choose **Report a vulnerability**. Include what you found, how to reproduce it and the impact you expect.

Do not include real Azure data in a report (subscription or tenant ids, resource names, IPs, tokens). Use synthetic values such as those in `corpus/`.

## Scope

In scope: anything in this repository, including the hygiene tooling, the CI workflow and, once it exists, the collector, engine and UI. Examples: a way to make the collector issue a non-read request, to leak a token or a real snapshot into the repo, or to bypass the hygiene checks.

Out of scope: vulnerabilities in Azure itself or in third-party tools; report those to their owners.

## Design principles

- Read-only: the planned collector only issues read requests to Azure Resource Graph and ARM, through the user's own `az login`. The code never handles a token.
- Real snapshots stay outside any git work tree. Raw or real data (`*.raw.json`, `*.real.json`, `snapshots/`) is git-ignored and rejected by the pre-commit hook.
- CI runs with `contents: read`, no secrets and actions pinned by full SHA. gitleaks scans the full history on every push and pull request.
