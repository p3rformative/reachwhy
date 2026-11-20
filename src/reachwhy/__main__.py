"""python -m reachwhy --case corpus/<case>
python -m reachwhy <snapshot.json> --origin ID --target ID --subresource blob

Reads local files and prints the verdict as JSON. Read-only: no network, no Azure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import analyze
from .snapshot import load


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="reachwhy", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("snapshot", nargs="?", help="snapshot JSON file")
    p.add_argument("--case", help="corpus folder: uses its snapshot.json and the pair in its expected.json")
    p.add_argument("--origin")
    p.add_argument("--target")
    p.add_argument("--subresource")
    a = p.parse_args(argv)
    if a.case:
        folder = Path(a.case)
        snapshot = load(folder / "snapshot.json")
        pair = load(folder / "expected.json")["pair"]
        origin, target, sub = pair["origin"], pair["target"], pair.get("targetSubresource", "")
    elif a.snapshot and a.origin and a.target and a.subresource:
        snapshot, origin, target, sub = load(a.snapshot), a.origin, a.target, a.subresource
    else:
        p.error("use --case DIR, or a snapshot with --origin, --target and --subresource")
    v = analyze(snapshot, origin, target, sub)
    json.dump(v, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 1 if v["overall"] == "red" else 0


if __name__ == "__main__":
    raise SystemExit(main())
