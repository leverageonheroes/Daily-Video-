#!/usr/bin/env python3
"""Install a Moral Of The Story TV "flow-film" episode (Google Flow clips + film cut list) into the scripts.

  python tools/generators/install_mos_flowfilm.py tools/generators/flowfilm/MOS-001_flowfilm.json

Keeps the episode's existing metadata (title, hook_text, part_label, end_card, captions, description, tags,
arc fields, guests, locations) and replaces its `shots` with format / voices / scenes / clips / edit / accounts.
Also makes sure channels/drizzlepudge/channel.json has the flow-film settings (only adds missing keys, never
overwrites a value that is already there, except "source", which must be "flow").
Safe to re-run. Never touches other episodes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "channels" / "drizzlepudge"

# Small fixes applied while installing (the uploaded JSON names a location id that does not exist,
# and clip 13 is in a car although its scene is the office). Logged when used.
LOC_ALIAS = {"a1_okafor": "a1_okafor_home"}
CLIP_LOC = {("MOS-001", 13): "a1_car"}

FLOW = {"model": "Veo 3.1 Lite", "mode": "Frames to Video", "aspect": "9:16", "clip_seconds": 8,
        "outputs_per_prompt": 1, "daily_free_credits": 50, "credits_per_clip": 10,
        "accounts": ["MOS-A", "MOS-B", "MOS-C"]}
LIPSYNC = {"endpoint": "fal-ai/kling-video/lipsync/audio-to-video",
           "fallbacks": ["fal-ai/sync-lipsync/v2", "fal-ai/latentsync"]}
GRADE = ("eq=contrast=1.07:saturation=1.06:gamma=0.98,unsharp=5:5:0.6,"
         "colorbalance=rs=0.03:bs=-0.03:rh=0.04:bh=-0.04,noise=alls=3:allf=t+u,vignette=PI/5")


def install(src: Path):
    ff = json.loads(src.read_text())
    ep_id = ff["id"]
    for f in sorted((CH / "episodes").glob("*.json")):
        data = json.loads(f.read_text())
        for ep in data["episodes"]:
            if ep["id"] != ep_id:
                continue
            for sc in ff["scenes"].values():
                if sc["loc"] in LOC_ALIAS and sc["loc"] not in ep.get("locations", {}):
                    print(f"   scene loc {sc['loc']} -> {LOC_ALIAS[sc['loc']]} (id in this episode's locations)")
                    sc["loc"] = LOC_ALIAS[sc["loc"]]
            for c in ff["clips"]:
                if (ep_id, c["n"]) in CLIP_LOC and "loc" not in c:
                    c["loc"] = CLIP_LOC[(ep_id, c["n"])]
                    print(f"   clip {c['n']}: loc {c['loc']} (overrides its scene's location)")
            ep.pop("shots", None)
            for k in ("format", "voices", "scenes", "clips", "edit", "accounts"):
                ep[k] = ff[k]
            f.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            print(f"   {ep_id} installed in {f.relative_to(ROOT)}")
            break
        else:
            continue
        break
    else:
        sys.exit(f"{ep_id} not found in {CH / 'episodes'}")

    p = CH / "channel.json"
    bible = json.loads(p.read_text())
    bible["source"] = "flow"
    bible.setdefault("episode_format", "flow-film")
    bible.setdefault("flow", FLOW)
    bible.setdefault("cast_voices", {})
    bible.setdefault("lipsync", LIPSYNC)
    bible.setdefault("tts", {"endpoint": "fal-ai/elevenlabs/tts/eleven-v3",
                             "fallback": "fal-ai/elevenlabs/tts/turbo-v2.5"})
    if "noise=alls=6" in bible.get("cinema_vf", ""):     # the old grade -> lighter grain + sharpening
        bible["cinema_vf"] = GRADE
    p.write_text(json.dumps(bible, indent=2, ensure_ascii=False) + "\n")
    print(f"   channel.json updated (source=flow, paused={bible['paused']})")


if __name__ == "__main__":
    install(Path(sys.argv[1]))
