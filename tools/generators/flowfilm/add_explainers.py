#!/usr/bin/env python3
"""Moral Of The Story TV: story explainer cards between scenes (narrator reads one short sentence over a
darkened still of the next scene, the same words on screen). Only where a scene change needs it (max 3 per part).

  python tools/generators/flowfilm/add_explainers.py          # writes EXPLAINERS into the flowfilm JSONs + episodes

Rules (tools/validate.py checks them): one sentence, 4-16 words, plain words, says WHO / WHERE / WHY so a
first-time viewer follows; orient, never spoil the scene's twist; never before the opening scene (the hook);
label <= 22 chars ("THAT NIGHT", "AT THE OKAFORS'"). Future arcs: put "explainers" straight into the
episode's flowfilm JSON (see pipeline/flowfilm.py expand_edit).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FF = ROOT / "tools" / "generators" / "flowfilm"
EPS = ROOT / "channels" / "drizzlepudge" / "episodes"

EXPLAINERS = {
    "MOS-002": [
        {"before": "B", "label": "Across town",
         "t": "Amara passes Uncle Femi's gate. A shiny new car is parked outside."},
        {"before": "D", "label": "That night",
         "t": "Mama hears the news. Her brother has broken her trust before."},
    ],
    "MOS-003": [
        {"before": "B", "label": "At the Okafors'",
         "t": "Amara goes home hurt. Her father, a proud retired teacher, has heard enough."},
        {"before": "D", "label": "One last chance",
         "t": "Tobi goes to Amara's father to beg for time to find the truth."},
    ],
    "MOS-004": [
        {"before": "B", "label": "On the drive home",
         "t": "Mama finally breaks her silence. Her secret is fifteen years old."},
        {"before": "C", "label": "Back home",
         "t": "Mama agrees to make it right. But someone has been listening."},
    ],
    "MOS-005": [
        {"before": "B", "label": "The next day",
         "t": "Proud Mama does what she has never done. She goes to apologise."},
        {"before": "C", "label": "At the gate",
         "t": "Just as peace returns, Uncle Femi arrives with a briefcase."},
    ],
    "MOS-006": [
        {"before": "B", "label": "Weeks later",
         "t": "Two families, one small celebration. This time, nothing is hidden."},
    ],
}


def main():
    for ep_id, ex in EXPLAINERS.items():
        src = FF / f"{ep_id}_flowfilm.json"
        if src.exists():
            txt = src.read_text()
            d = json.loads(txt)
            if d.get("explainers") != ex:
                if "explainers" in d:
                    d["explainers"] = ex
                    txt = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
                else:          # append as text, so a hand-formatted file keeps its layout
                    body = txt.rstrip().rstrip("}").rstrip()
                    txt = body + ',\n "explainers": ' + json.dumps(ex, ensure_ascii=False) + "\n}\n"
                json.loads(txt)
                src.write_text(txt)
        for f in sorted(EPS.glob("*.json")):
            data = json.loads(f.read_text())
            hit = [e for e in data["episodes"] if e["id"] == ep_id]
            for e in hit:
                e["explainers"] = ex
            if hit:
                f.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
                print(f"   {ep_id}: {len(ex)} explainers")


if __name__ == "__main__":
    main()
