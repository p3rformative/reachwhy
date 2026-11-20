import copy
import json
from pathlib import Path

import pytest

from reachwhy import analyze

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
SUBRESOURCE = "blob"


CASES = sorted(p.name for p in CORPUS.iterdir() if (p / "snapshot.json").exists())


def load_case(case_id: str) -> tuple[dict, dict]:
    d = CORPUS / case_id
    return (json.loads((d / "snapshot.json").read_text(encoding="utf-8")),
            json.loads((d / "expected.json").read_text(encoding="utf-8")))


def run(snapshot: dict, expected: dict) -> dict:
    pair = expected["pair"]
    return analyze(snapshot, pair["origin"], pair["target"], pair.get("targetSubresource", SUBRESOURCE))


def hop(verdict: dict, hop_id: str) -> dict:
    return next(h for h in verdict["hops"] if h["id"] == hop_id)


def resource(snapshot: dict, rtype: str, name: str | None = None) -> dict:
    return next(r for r in snapshot["resources"]
                if r["type"] == rtype and (name is None or r["name"] == name))


@pytest.fixture
def hub_case():
    """Mutable copy of the hub case: zone, link and A record in another subscription, all OK."""
    snap, exp = load_case("synthetic-dns-hub-zone-01")
    return copy.deepcopy(snap), exp


@pytest.fixture
def demo_case():
    snap, exp = load_case("demo-basic-01")
    return copy.deepcopy(snap), exp
