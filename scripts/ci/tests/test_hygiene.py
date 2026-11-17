"""Tests de check_hygiene.py: un caso valido y uno invalido por regla. Ejecutar: python -m unittest discover -s scripts/ci/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_hygiene as h  # noqa: E402

# Se arma por partes para no disparar la regla de GUID de suscripcion de gitleaks fuera de corpus/, schemas/ y docs/.
SUB = "/" + "subscriptions" + "/" + "0" * 8 + "-0000-0000-0000-" + "0" * 12


def snap(**over):
    d = {
        "synthetic": True,
        "resources": [{"id": f"{SUB}/resourcegroups/rg-demo/providers/microsoft.storage/storageaccounts/stdemo001",
                       "type": "microsoft.storage/storageaccounts", "name": "stdemo001",
                       "properties": {"primaryEndpoints": {"blob": "https://stdemo001.blob.core.windows.net/"},
                                      "ip": "10.20.2.4"}}],
    }
    d.update(over)
    return d


def run(doc, rel="corpus/x/snapshot.json"):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc), encoding="utf-8")
        # check_file usa la ruta relativa para decidir el modo; se simula con un chdir implicito
        import os
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            return h.check_file(Path(rel))
        finally:
            os.chdir(cwd)


class Hygiene(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(run(snap()), [])

    def test_ip_outside_allowlist(self):
        d = snap(); d["resources"][0]["properties"]["ip"] = "10.1.2.3"
        self.assertTrue(any("IP" in e for e in run(d)))

    def test_documentation_ranges_allowed(self):
        d = snap(); d["resources"][0]["properties"]["ip"] = "203.0.113.7"
        self.assertEqual(run(d), [])

    def test_name_without_marker(self):
        d = snap(); d["resources"][0]["name"] = "prodstore"
        self.assertTrue(any("sin demo/example" in e for e in run(d)))

    def test_resource_group_without_marker(self):
        d = snap(); d["resources"][0]["id"] = d["resources"][0]["id"].replace("rg-demo", "rg-prod")
        self.assertTrue(any("resource group" in e for e in run(d)))

    def test_guid_not_synthetic(self):
        d = snap(note="3f2a9c1e-7b4d-4e68-9a15-c0d8e6b2f417")
        self.assertTrue(any("GUID" in e for e in run(d)))

    def test_domain_outside_allowlist(self):
        d = snap(note="https://stdemo001.example-corp.com/")
        self.assertTrue(any("dominio" in e for e in run(d)))

    def test_fqdn_without_marker(self):
        d = snap(note="kvsample.vault.azure.net")
        self.assertTrue(any("FQDN" in e for e in run(d)))

    def test_missing_synthetic_flag(self):
        d = snap(); d["synthetic"] = False
        self.assertTrue(any("synthetic" in e for e in run(d)))

    def test_forbidden_paths(self):
        self.assertTrue(run(snap(), "corpus/x/dump.raw.json"))
        self.assertTrue(run(snap(), "snapshots/a.json"))

    def test_docs_mode_only_guid(self):
        self.assertEqual(run({"note": "198.18.0.1 contoso.com"}, "docs/a.json"), [])
        self.assertTrue(run({"note": "3f2a9c1e-7b4d-4e68-9a15-c0d8e6b2f417"}, "docs/a.json"))

    def test_schema_meta_url_ignored(self):
        self.assertEqual(run({"$schema": "https://json-schema.org/draft/2020-12/schema"}, "schemas/a.json"), [])


if __name__ == "__main__":
    unittest.main()
