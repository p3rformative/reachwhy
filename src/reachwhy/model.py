"""Verdict model: one Hop per rule outcome (see docs/design.md, "Verdict")."""
from __future__ import annotations

from dataclasses import dataclass, field

GREEN, AMBER, RED = "green", "amber", "red"
HOP_ORDER = ("origin", "dns", "route", "nsg", "pe", "target-net", "rbac")


@dataclass
class Hop:
    id: str
    state: str
    code: str | None
    cause: str
    evidence: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    why_unverifiable: str | None = None
    how_to_verify: str | None = None

    def __post_init__(self) -> None:
        if self.code is not None and not self.sources:
            raise ValueError(f"verdict code {self.code} must cite at least one source")

    def to_dict(self) -> dict:
        d: dict = {"id": self.id, "state": self.state, "code": self.code, "cause": self.cause,
                   "evidence": self.evidence, "sources": self.sources}
        if self.caveats:
            d["caveats"] = self.caveats
        if self.state == AMBER:
            d["whyUnverifiable"] = self.why_unverifiable
            d["howToVerify"] = self.how_to_verify
        return d


def evidence(resource: str, path: str, value: object, kind: str = "arm") -> dict:
    return {"kind": kind, "resource": resource, "path": path, "value": value}
