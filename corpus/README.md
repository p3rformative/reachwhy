# corpus

Casos sinteticos de "repro de red": cada carpeta tiene `snapshot.json`, `expected.json` y `SOURCE.md`.
Todo es 100 % sintetico y debe pasar `python scripts/ci/check_hygiene.py corpus`.
Formato, reglas de procedencia y cómo agregar un caso: ver [docs/design.md](../docs/design.md#corpus) y [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-corpus-case). Hoy: `demo-basic-01` y 8 casos `synthetic-*` de la fase 1. Se ejecutan con `python -m pytest` (ver [CONTRIBUTING.md](../CONTRIBUTING.md)).
