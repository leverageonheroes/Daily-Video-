#!/usr/bin/env python3
"""Install the 8-clip scripts for elders + cribcommittee WITHOUT changing episodes that were already made.

Episodes whose state is rendered / uploaded / published keep their original (5-clip) script, so the
weekly/monthly compilations still get correct chapter times. Everything else gets the new 8-clip version.
Usage: python tools/upgrades/merge_flow8.py <folder with the new channels/ from the add-on>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = Path(sys.argv[1]).resolve()
state = json.loads((ROOT / "state" / "state.json").read_text()) if (ROOT / "state" / "state.json").exists() else {"channels": {}}

for ch in ("elders", "cribcommittee"):
    recs = state["channels"].get(ch, {}).get("episodes", {})
    done = {k for k, r in recs.items() if r.get("status") in ("rendered", "uploaded", "published")}
    old = {}
    for f in sorted((ROOT / "channels" / ch / "episodes").glob("*.json")):
        for e in json.loads(f.read_text())["episodes"]:
            old[e["id"]] = e
    kept = []
    for f in sorted((NEW / "channels" / ch / "episodes").glob("*.json")):
        data = json.loads(f.read_text())
        for i, e in enumerate(data["episodes"]):
            if e["id"] in done and e["id"] in old:
                data["episodes"][i] = old[e["id"]]
                kept.append(e["id"])
        (ROOT / "channels" / ch / "episodes" / f.name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "channels" / ch / "channel.json").write_text((NEW / "channels" / ch / "channel.json").read_text())
    print(f"{ch}: new 8-clip scripts installed; kept original scripts for already-made episodes: {kept or 'none'}")
