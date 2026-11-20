"""Pure rule engine over a snapshot dict. No I/O, no clock, no network."""
from __future__ import annotations

from .model import AMBER, GREEN, HOP_ORDER, RED, Hop
from .rules_dns import check_dns
from .rules_origin import check_origin_routing
from .snapshot import Snapshot

IMPLEMENTED = ("origin", "dns")


def analyze(snapshot: dict, origin_id: str, target_id: str, subresource: str) -> dict:
    snap = Snapshot(snapshot)
    dns = check_dns(snap, origin_id, target_id, subresource)
    origin = check_origin_routing(snap, origin_id, dns)
    hops: list[Hop] = sorted([origin, dns], key=lambda h: HOP_ORDER.index(h.id))
    states = [h.state for h in hops]
    overall = RED if RED in states else AMBER if AMBER in states else GREEN
    first_red = next((h.id for h in hops if h.state == RED), None)
    return {
        "pair": {"origin": origin_id, "target": target_id, "targetSubresource": subresource},
        "overall": overall,
        "firstRedHop": first_red,
        "complete": False,
        "evaluatedHops": list(IMPLEMENTED),
        "notEvaluated": [h for h in HOP_ORDER if h not in IMPLEMENTED],
        "hops": [h.to_dict() for h in hops],
    }
