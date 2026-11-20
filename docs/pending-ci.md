# Estado de CI

## Activo (`.github/workflows/ci.yml`)

Disparadores: `push` a `main` y `pull_request`. Permisos: `contents: read` a nivel de workflow y nada más. Sin secretos, sin `pull_request_target`, solo acciones de `actions/` fijadas por SHA completo (versión en comentario).

| Job | Qué hace |
|---|---|
| `gitleaks` | Checkout con `fetch-depth: 0`; descarga gitleaks de la versión fija (`.gitleaks-version`, hoy 8.30.1) del release oficial, verifica el SHA-256 contra el valor fijado en el repo (`.gitleaks-sha256`, no contra uno descargado en la corrida) y ejecuta `gitleaks git` con `.gitleaks.toml` sobre todo el historial. |
| `hygiene` | `setup-python` y luego `scripts/ci/check_hygiene.py corpus schemas docs` y los tests de `scripts/ci/tests`. |

Acciones fijadas: `actions/checkout` v7.0.1 y `actions/setup-python` v7.1.0 (SHA completos en el workflow). Al actualizar gitleaks hay que cambiar a la vez `.gitleaks-version`, `.gitleaks-sha256` y `docs/tooling.md`, con el checksum de la release oficial.

## Pendiente (no incluido; un workflow nuevo o modificado requiere aprobación del mantenedor)

Previsto en [ROADMAP.md](../ROADMAP.md):

| Workflow / job | Qué haría |
|---|---|
| `pr-review` | Workflow de PR que agrupa `secret-scan` (gitleaks sobre el rango del PR y luego el historial) y los jobs de abajo. |
| `dependency-review` | Revisión de dependencias del PR (requiere activar el Dependency graph en el repo). |
| `rust-advisories` | `cargo deny` y `cargo audit` con baseline vacío (cuando exista código Rust). |
| `javascript-audit` | `pnpm audit` con baseline (cuando exista la UI). |
| `corpus` | Tests de corpus contra el motor y validación de `schemas/*.json`. Ya existe el prototipo en Python (`python -m pytest`, 77 tests en `tests/`), pero el CI activo no lo ejecuta: agregarlo es un cambio de workflow y requiere aprobación del mantenedor. |
| Dependabot | Mensual (npm, cargo, github-actions), límite de 2 PR abiertos. |

Antes de activarlos: volver a verificar versiones y SHA de acciones y herramientas contra las fuentes oficiales.
