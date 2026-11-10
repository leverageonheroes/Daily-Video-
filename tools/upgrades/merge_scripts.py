#!/usr/bin/env python3
"""Install new scripts for the given channels WITHOUT changing episodes that were already made.

Episodes whose state is rendered / uploaded / published keep their current script (so compilations and
history stay correct); every other episode gets the new version. channel.json is replaced.
Usage: python tools/upgrades/merge_scripts.py <folder containing channels/> elders cribcommittee
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = Path(sys.argv[1]).resolve()
state_file = ROOT / "state" / "state.json"
state = json.loads(state_file.read_text()) if state_file.exists() else {"channels": {}}

for ch in sys.argv[2:]:
    recs = state["channels"].get(ch, {}).get("episodes", {})
    done = {k for k, r in recs.items() if r.get("status") in ("rendered", "uploaded", "published")}
    old = {e["id"]: e for f in sorted((ROOT / "channels" / ch / "episodes").glob("*.json"))
           for e in json.loads(f.read_text())["episodes"]}
    kept = []
    for f in sorted((NEW / "channels" / ch / "episodes").glob("*.json")):
        data = json.loads(f.read_text())
        for i, e in enumerate(data["episodes"]):
            if e["id"] in done and e["id"] in old:
                data["episodes"][i] = old[e["id"]]
                kept.append(e["id"])
        (ROOT / "channels" / ch / "episodes" / f.name).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "channels" / ch / "channel.json").write_text((NEW / "channels" / ch / "channel.json").read_text())
    print(f"{ch}: new scripts installed; kept already-made episodes unchanged: {kept or 'none'}")
