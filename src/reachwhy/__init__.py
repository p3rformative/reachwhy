"""reachwhy: read-only, hop-by-hop diagnosis of Azure PaaS reachability.

Prototype. This package only analyzes a local JSON snapshot (see schemas/snapshot.schema.json).
It never calls Azure and never reads credentials.
"""

RULESET_VERSION = "0.1.0"

from .engine import analyze  # noqa: E402,F401
