"""Read-only helpers over a snapshot dict. No I/O besides optional file loading."""
from __future__ import annotations

import json
from pathlib import Path

LINKS = "microsoft.network/privatednszones/virtualnetworklinks"
ZONES = "microsoft.network/privatednszones"
ZONE_A = "microsoft.network/privatednszones/a"


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def norm(s: str | None) -> str:
    return (s or "").lower()


def vnet_of_subnet(subnet_id: str | None) -> str | None:
    """Id of the VNet that owns a subnet id (ARM ids are case-insensitive)."""
    if not subnet_id:
        return None
    i = subnet_id.lower().find("/subnets/")
    return subnet_id[:i] if i > 0 else None


class Snapshot:
    def __init__(self, data: dict):
        self.data = data
        self.resources: list[dict] = data.get("resources", [])
        self._by_id = {norm(r.get("id")): r for r in self.resources}

    def get(self, rid: str | None) -> dict | None:
        return self._by_id.get(norm(rid))

    def of_type(self, rtype: str) -> list[dict]:
        return [r for r in self.resources if norm(r.get("type")) == rtype]

    @property
    def has_unreadable_scope(self) -> bool:
        vis = self.data.get("visibility") or {}
        if vis.get("unreadable"):
            return True
        return any(not s.get("readable", True) for s in vis.get("subscriptions", []))
