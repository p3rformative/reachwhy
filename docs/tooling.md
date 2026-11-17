# Herramientas y verificación local

## gitleaks: versión fija

- **Versión fija: 8.30.1** (archivo `.gitleaks-version`).
- Binario oficial `gitleaks_8.30.1_linux_x64.tar.gz`, SHA-256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` (de `gitleaks_8.30.1_checksums.txt` de la release v8.30.1 del proyecto gitleaks).
- Instalación manual: descargar de las releases oficiales, comprobar el SHA-256 y poner el binario en el PATH. Para otras plataformas, usar el checksum de la misma release.
- El SHA-256 fijado vive en `.gitleaks-sha256`; el CI lo usa para verificar la descarga (no descarga un checksum en la corrida). Al cambiar de versión se actualizan `.gitleaks-version`, `.gitleaks-sha256` y este documento.
- El hook avisa si la versión instalada difiere de la fija. Se puede apuntar a un binario concreto con `GITLEAKS_BIN`.
- Las rutas de la allowlist de `.gitleaks.toml` usan `(^|/)corpus/`, `(^|/)schemas/` y `(^|/)docs/`, así que funcionan tanto desde la raíz del repo como pasando la ruta absoluta del repo desde otra carpeta. Efecto secundario conocido: también eximen una carpeta con ese nombre a cualquier profundidad (p. ej. `scripts/docs/`); solo para el GUID sintético de ceros.

Desde la raíz del repo (bash o PowerShell):

```sh
gitleaks dir --no-banner --redact --config .gitleaks.toml .     # árbol de trabajo
gitleaks git --no-banner --redact --config .gitleaks.toml .     # historial git
```

Desde otra carpeta, con ruta absoluta (bash):

```sh
repo=/ruta/a/reachwhy
gitleaks dir --no-banner --redact --config "$repo/.gitleaks.toml" "$repo"
gitleaks git --no-banner --redact --config "$repo/.gitleaks.toml" "$repo"
```

PowerShell:

```powershell
$repo = 'C:\ruta\a\reachwhy'
gitleaks dir --no-banner --redact --config "$repo\.gitleaks.toml" $repo
gitleaks git --no-banner --redact --config "$repo\.gitleaks.toml" $repo
```

## Allowlist del GUID de suscripción

La regla `subscription-guid` dispara con un GUID precedido de contexto de suscripción. La allowlist exime únicamente `^0{8}-0{4}-0{4}-0{4}-[0-9a-f]{12}$` y solo en `corpus/`, `schemas/` y `docs/`.

- `condition = "AND"` es obligatorio: con el valor por defecto (`OR`) el regex exime el GUID de ceros en cualquier carpeta.
- Comportamiento verificado con gitleaks 8.30.1: GUID de ceros en `corpus/` → sin hallazgo; el mismo fuera de esas carpetas → hallazgo; una clave tipo AWS falsa en `corpus/` → hallazgo (la allowlist es solo de la regla del GUID).
- La convención más estricta del repo (sufijo `0000000000NN`) la hace cumplir `scripts/ci/check_hygiene.py`, no gitleaks.

## Hook pre-commit de higiene

```sh
git config core.hooksPath .githooks
```

Equivalentes: `scripts/install-hooks.sh` y `scripts/install-hooks.ps1`. El hook:

1. Ejecuta `scripts/ci/check_hygiene.py` sobre los `.json`/`.md` preparados en `corpus/`, `schemas/` y `docs/`, y rechaza cualquier `*.raw.json` o carpeta `snapshots/`.
2. Ejecuta `gitleaks git --pre-commit --staged` si gitleaks está instalado.

Solo hace higiene estructural: no contiene listas de nombres de empresas ni de personas. Lee el árbol de trabajo de los archivos preparados.

## Tests y comprobaciones

```sh
python -m unittest discover -s scripts/ci/tests
python scripts/ci/check_hygiene.py corpus schemas docs
```

## actionlint (opcional)

Para revisar `.github/workflows/*.yml` en local. No se versiona ningún binario ni paquete en el repo (`*.tar.gz` está en `.gitignore`); se instala desde PyPI ([actionlint-py](https://github.com/Mateusz-Grzelinski/actionlint-py), empaqueta [actionlint](https://github.com/rhysd/actionlint)):

```sh
python -m pip install actionlint-py==1.7.12.25
actionlint .github/workflows/ci.yml
```
