#!/usr/bin/env python3
"""One-off, idempotent upgrade of channels/coldhearts to the Fridge Hearts drama engine.
Edits the existing files in place (keeps any other changes you made):
  - channel.json: show_title "Fridge Hearts", cold_open, end_card, drama_rules, format
  - every episode: last shot camera = crash zoom, + orchestral sting; cold_open overrides for CH-011, CH-025
Run: python tools/upgrades/fridge_hearts_drama.py
"""
import json
from pathlib import Path

CH = Path(__file__).resolve().parents[2] / "channels" / "coldhearts"
OVER = {"CH-011": {"shot": 6, "start": 0.0, "seconds": 4.5}, "CH-025": {"shot": 6, "start": 0.0, "seconds": 4.0}}


def save(p, d, indent):
    p.write_text(json.dumps(d, indent=indent, ensure_ascii=False) + "\n")


b = CH / "channel.json"
d = json.loads(b.read_text())
d["show_title"] = "Fridge Hearts"
d["format"] = ("Melodramatic micro-soap, 60-85s. Opens with a 3.5 s FLASH-FORWARD of the cliffhanger (cold open), "
               "then a card (\"12 HOURS EARLIER...\") and the story builds back to that moment, ends on the cliffhanger "
               "and a \"TO BE CONTINUED...\" card. Each episode understandable on its own.")
d["cold_open"] = {"seconds": 3.5, "start": 0.0, "cards": ["12 HOURS EARLIER...", "EARLIER THAT DAY...", "THAT MORNING...",
                                                         "ONE HOUR EARLIER...", "THE NIGHT BEFORE..."]}
d["end_card"] = "TO BE CONTINUED..."
d["drama_rules"] = [
    "The last shot must open on its most shocking beat (line or reveal in the first 3 seconds) because its first 3.5 s become the cold open.",
    "Every shot ends on a turn: a reveal, a threat, a betrayal or a question. No shot is only small talk.",
    "Raise the stakes every episode: someone could be Chosen, expire, be exiled to the North or lose love.",
    "Use dramatic camera language: crash zooms, slow push-ins, whip pans, extreme close-ups on eyes.",
    "Melodrama played completely straight. The comedy comes from the seriousness."]
save(b, d, 2)

n = 0
for f in sorted((CH / "episodes").glob("*.json")):
    data = json.loads(f.read_text())
    for e in data["episodes"]:
        if e["id"] in OVER:
            e["cold_open"] = OVER[e["id"]]
        last = e["shots"][-1]
        last["camera"] = "dramatic crash zoom into an extreme close-up, then hold on the face"
        if "sting" not in last.get("sfx", ""):
            last["sfx"] = (last.get("sfx", "") + ", dramatic soap-opera orchestral sting").lstrip(", ")
        n += 1
    save(f, data, 1)
print(f"Fridge Hearts upgraded: {n} episodes")
