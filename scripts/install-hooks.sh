#!/bin/sh
# Activa los hooks versionados del repo (solo configuracion local; no toca el remoto).
set -eu
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit 2>/dev/null || true
echo "core.hooksPath = $(git config core.hooksPath)"
