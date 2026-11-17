#!/usr/bin/env python3
"""Higiene de datos sintéticos para corpus/, schemas/ y docs/.

Solo higiene estructural: no contiene listas de palabras de empresas ni de personas.
Uso: python scripts/ci/check_hygiene.py <archivo-o-carpeta> [...]
"""
import ipaddress
import json
import re
import sys
from pathlib import Path

ALLOWED_NETS = [ipaddress.ip_network(n) for n in
                ("10.20.0.0/16", "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
SYNTH_GUID = re.compile(r"^0{8}-0{4}-0{4}-0{4}-0{10}[0-9a-f]{2}$")  # convención del repo (más estricta que gitleaks)
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
HOST = re.compile(r"(?<![\w.-])[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+(?![\w-])", re.I)
TLDS = {"net", "com", "io", "org", "ms", "us", "cn", "de", "uk"}
ALLOWED_SUFFIXES = ("core.windows.net", "vault.azure.net", "database.windows.net")
CANONICAL_ZONES = {  # nombres públicos de zona privatelink: constantes, no datos de un entorno
    "privatelink.blob.core.windows.net", "privatelink.file.core.windows.net",
    "privatelink.queue.core.windows.net", "privatelink.table.core.windows.net",
    "privatelink.dfs.core.windows.net", "privatelink.vaultcore.azure.net",
    "privatelink.database.windows.net", "privatelink.monitor.azure.com",
}
DOC_HOSTS = {"learn.microsoft.com", "github.com", "www.reddit.com"}  # solo en source.url y en *.md
ARM_ID = re.compile(r"/resourcegroups/([^/\"\s]+)(?:/providers/([^/\"\s]+)((?:/[^/\"\s]+)+))?", re.I)
FORBIDDEN_PATH = re.compile(r"(\.raw\.json$)|(^|/)snapshots/")


def has_marker(s: str) -> bool:
    s = s.lower()
    return "demo" in s or "example" in s


def check_text(text: str, mode: str) -> list[str]:
    errs: list[str] = []
    for g in sorted(set(GUID.findall(text))):
        if not SYNTH_GUID.match(g.lower()):
            errs.append(f"GUID no sintético: {g}")
    if mode == "docs":          # docs/: solo GUID (los ejemplos de documentación citan constantes públicas)
        return errs
    for ip in sorted(set(IPV4.findall(text))):
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if not any(addr in n for n in ALLOWED_NETS):
            errs.append(f"IP fuera de los rangos permitidos: {ip}")
    for host in sorted({h.lower() for h in HOST.findall(text)}):
        if host.rsplit(".", 1)[-1] not in TLDS:
            continue
        if host in CANONICAL_ZONES:
            continue
        if not host.endswith(tuple("." + s for s in ALLOWED_SUFFIXES)):
            errs.append(f"dominio fuera de la allowlist: {host}")
        elif not has_marker(host.split(".", 1)[0]):
            errs.append(f"FQDN sin nombre demo/example: {host}")
    for m in ARM_ID.finditer(text):
        rg, _ns, rest = m.group(1), m.group(2), m.group(3)
        if not has_marker(rg):
            errs.append(f"resource group sin demo/example: {rg}")
        segs = [s for s in (rest or "").split("/") if s]
        for i in range(0, len(segs) - 1, 2):
            rtype, name = segs[i].lower(), segs[i + 1]
            if rtype == "roleassignments":
                continue
            if not has_marker(name) and name.lower() not in CANONICAL_ZONES:
                errs.append(f"nombre de recurso sin demo/example: {name}")
    return errs


def check_names(doc: object) -> list[str]:
    """Nombres propios de recursos, subredes y registros (no solo los que aparecen dentro de ids)."""
    errs: list[str] = []
    for r in (doc.get("resources", []) if isinstance(doc, dict) else []):
        names = [(r.get("name"), r.get("type", ""))]
        props = r.get("properties", {}) or {}
        names += [(s.get("name"), "subnet") for s in props.get("subnets", []) or []]
        names += [(x.get("name"), "record") for x in r.get("recordSets", []) or []]
        for name, kind in names:
            if isinstance(name, str) and name.lower() not in CANONICAL_ZONES and not has_marker(name):
                errs.append(f"nombre sin demo/example ({kind}): {name}")
    if isinstance(doc, dict) and doc.get("synthetic") is not True and "resources" in doc:
        errs.append("falta synthetic=true")
    return errs


def strip_source_urls(doc: object) -> object:
    if isinstance(doc, dict):
        out = {k: strip_source_urls(v) for k, v in doc.items() if k != "$schema"}  # URL del metaesquema, no es dato
        if isinstance(out.get("source"), dict):
            out["source"] = {k: v for k, v in out["source"].items() if k != "url"}
        return out
    if isinstance(doc, list):
        return [strip_source_urls(x) for x in doc]
    return doc


def check_file(path: Path) -> list[str]:
    rel = path.as_posix()
    if FORBIDDEN_PATH.search(rel):
        return ["archivo prohibido en el repo (*.raw.json o snapshots/)"]
    mode = "docs" if rel.startswith("docs/") or "/docs/" in rel else "data"
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        doc = json.loads(text)
        errs = check_text(json.dumps(strip_source_urls(doc), ensure_ascii=False), mode)
        return errs + (check_names(doc) if mode == "data" else [])
    # markdown: quitar enlaces a hosts de documentación pública
    text = re.sub(r"https?://(?:%s)/\S*" % "|".join(re.escape(h) for h in DOC_HOSTS), "", text)
    return check_text(text, mode)


def main(argv: list[str]) -> int:
    files: list[Path] = []
    for a in argv:
        p = Path(a)
        files += [x for x in p.rglob("*") if x.suffix in (".json", ".md")] if p.is_dir() else [p]
    bad = {f: e for f in files if (e := check_file(f))}
    for f, e in bad.items():
        print(f.as_posix(), *e, sep="\n  - ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
