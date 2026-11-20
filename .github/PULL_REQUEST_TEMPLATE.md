## What and why

## Checklist

- [ ] Only synthetic data (no real ids, names, IPs or tokens).
- [ ] `python -m unittest discover -s scripts/ci/tests -v` passes.
- [ ] `python -m pytest` passes (if you touched `src/`, `tests/` or `corpus/`).
- [ ] `python scripts/ci/check_hygiene.py corpus schemas docs` passes.
- [ ] Docs describe only what exists; planned work is labeled as planned.
- [ ] If this touches `.github/workflows/`: justification included.
