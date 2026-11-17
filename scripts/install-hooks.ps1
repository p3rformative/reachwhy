# Activa los hooks versionados del repo (solo configuracion local; no toca el remoto).
$ErrorActionPreference = 'Stop'
Set-Location (git rev-parse --show-toplevel)
git config core.hooksPath .githooks
"core.hooksPath = $(git config core.hooksPath)"
