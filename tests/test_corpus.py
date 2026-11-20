"""Runs the engine over every corpus case and compares it with expected.json.

The engine is partial (origin and dns hops only), so hops it does not implement are skipped.
`overall` is compared as the engine reports it: over the evaluated hops, and never green while
`complete` is false (see docs/design.md, Corpus)."""
import json

import pytest

from conftest import CORPUS, load_case, run
from reachwhy.engine import IMPLEMENTED

CASES = sorted(p.name for p in CORPUS.iterdir() if (p / "snapshot.json").exists())


def test_corpus_not_empty():
    assert len(CASES) >= 11


@pytest.mark.parametrize("case", CASES)
def test_case_matches_expected(case):
    snap, exp = load_case(case)
    assert snap["id"] == exp["caseId"] == case
    verdict = run(snap, exp)
    want = exp["expected"]
    got = {h["id"]: h for h in verdict["hops"]}

    asserted = {k: v for k, v in want["hops"].items() if k in IMPLEMENTED and v["state"] != "any"}
    for hop_id, w in asserted.items():
        assert got[hop_id]["state"] == w["state"], f"{case}: hop {hop_id}"
        if "code" in w:
            assert got[hop_id]["code"] == w["code"], f"{case}: hop {hop_id}"
    for hop_id in want.get("mustNotBeGreen", []):
        if hop_id in got:
            assert got[hop_id]["state"] != "green", f"{case}: {hop_id} must not be green"
    assert verdict["overall"] == want["overall"], case
    assert verdict["firstRedHop"] == want.get("firstRedHop"), case


@pytest.mark.parametrize("case", CASES)
def test_every_amber_hop_explains_itself(case):
    snap, exp = load_case(case)
    for h in run(snap, exp)["hops"]:
        assert h["sources"] or h["state"] == "green"
        if h["state"] == "amber":
            assert h["whyUnverifiable"] and h["howToVerify"]


def test_every_rule_code_has_a_corpus_case():
    """Each phase 1 code that corpus cases can express appears in at least one expected.json."""
    seen = set()
    for case in CASES:
        _, exp = load_case(case)
        seen |= {h.get("code") for h in exp["expected"]["hops"].values()}
    for code in ("DNS_ZONE_NOT_LINKED", "DNS_ZONE_MISSING", "DNS_ZONE_NOT_VISIBLE", "DNS_ZONE_EMPTY_NO_FALLBACK",
                 "DNS_FALLBACK_TO_PUBLIC", "DNS_CUSTOM_SERVER", "ORIGIN_ROUTE_ALL_OFF"):
        assert code in seen, code


def test_schema_validation_if_available():
    jsonschema = pytest.importorskip("jsonschema")
    root = CORPUS.parent / "schemas"
    s_snap = json.loads((root / "snapshot.schema.json").read_text(encoding="utf-8"))
    s_exp = json.loads((root / "expected.schema.json").read_text(encoding="utf-8"))
    for case in CASES:
        snap, exp = load_case(case)
        jsonschema.validate(snap, s_snap)
        jsonschema.validate(exp, s_exp)


def test_cli_prints_the_verdict_of_a_case(capsys):
    from reachwhy.__main__ import main
    assert main(["--case", str(CORPUS / "synthetic-dns-fallback-01")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["overall"] == "amber" and out["complete"] is False
    assert main(["--case", str(CORPUS / "demo-basic-01")]) == 1
