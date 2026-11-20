"""Every verdict code cites at least one source. The codes are discovered in the source code, so a new
code without a scenario here (or without a source) fails the suite."""
import copy
import re

import pytest

from conftest import CASES, ROOT, hop, load_case, resource, run

CODE = re.compile(r"\b((?:DNS|ORIGIN)_[A-Z_]+)\b")
SOURCE_CODES = {c for f in (ROOT / "src" / "reachwhy").glob("*.py") for c in CODE.findall(f.read_text(encoding="utf-8"))}


def _mutated(case, edit, expected_override=None):
    snap, exp = load_case(case)
    snap = copy.deepcopy(snap)
    edit(snap)
    return run(snap, expected_override or exp)


def _site(snap):
    return resource(snap, "microsoft.web/sites")["properties"]


def _link(snap):
    return resource(snap, "microsoft.network/privatednszones/virtualnetworklinks")


def _record(snap):
    return resource(snap, "microsoft.network/privatednszones/a")


def _rename_record(snap):
    r = _record(snap)
    r["name"] = "stother-demo"
    r["id"] = r["id"].rsplit("/", 1)[0] + "/stother-demo"


def _stale(snap):
    _record(snap)["properties"]["records"][0]["ipv4Address"] = "10.20.9.9"


def _no_policy(snap):
    snap["resources"].remove(_record(snap))
    del _link(snap)["properties"]["resolutionPolicy"]


def _conflict(snap):
    p = _site(snap)
    p["outboundVnetRouting"] = {"allTraffic": True}
    p["vnetRouteAllEnabled"] = False


def _unknown_routing(snap):
    p = _site(snap)
    p.pop("vnetRouteAllEnabled", None)
    p.pop("outboundVnetRouting", None)


def _no_integration(snap):
    del _site(snap)["virtualNetworkSubnetId"]


SCENARIOS = [
    ("synthetic-dns-hub-zone-01", _rename_record),
    ("synthetic-dns-hub-zone-01", _stale),
    ("synthetic-dns-hub-zone-01", _no_policy),
    ("synthetic-dns-hub-zone-01", _conflict),
    ("synthetic-dns-hub-zone-01", _unknown_routing),
    ("synthetic-dns-hub-zone-01", _no_integration),
    ("synthetic-dns-hub-zone-01", lambda s: s["resources"].clear()),
]


def _all_hops():
    hops = []
    for case in CASES:
        snap, exp = load_case(case)
        hops += run(snap, exp)["hops"]
    for case, edit in SCENARIOS:
        hops += _mutated(case, edit)["hops"]
    return hops


def test_codes_are_discovered_in_the_source():
    assert {"DNS_ZONE_NOT_LINKED", "ORIGIN_INPUT_INCOMPLETE", "DNS_INPUT_INCOMPLETE"} <= SOURCE_CODES


def test_every_code_in_the_source_is_exercised_here():
    seen = {h["code"] for h in _all_hops() if h["code"]}
    assert SOURCE_CODES <= seen, f"codes with no scenario: {sorted(SOURCE_CODES - seen)}"


def test_every_verdict_code_cites_at_least_one_source():
    for h in _all_hops():
        if h["code"]:
            assert h["sources"], h["code"]
            assert all(s.startswith("https://learn.microsoft.com/") for s in h["sources"]), h["code"]


def test_origin_input_incomplete_cites_the_overview_source():
    from reachwhy.rules_origin import SRC_OVERVIEW
    v = _mutated("synthetic-dns-hub-zone-01", lambda s: None,
                 {"pair": {"origin": "/subscriptions/none", "target": "x", "targetSubresource": "blob"}})
    h = hop(v, "origin")
    assert h["code"] == "ORIGIN_INPUT_INCOMPLETE" and SRC_OVERVIEW in h["sources"]


def test_a_hop_with_a_code_and_no_source_cannot_be_built():
    from reachwhy.model import Hop
    with pytest.raises(ValueError):
        Hop("dns", "red", "DNS_X", "no source")
