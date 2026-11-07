#!/usr/bin/env python3
"""Builds channels/cribcommittee/channel.json and episodes 001-030 (The Crib Committee, Google Flow channel).

Source scripts: channels/cribcommittee/scripts_001-030.md (5 lines per episode: Chair, then three of
Sassy/Wise/Dramatic in any order, then Closer + a newborn reaction in brackets).
Each episode = 5 different babies x 8 s Veo 3.1 Lite clips = 40 s. No names: every clip is a different baby,
but the ROLE look stays the same (the Chair always wears the tiny tie and reading glasses).
Every shot carries a ready-to-paste `flow_prompt` containing the exact spoken line.

Re-run safely: python tools/generators/build_cribcommittee_001-030.py
Next batch: copy to build_cribcommittee_031-060.py, add scripts_031-060.md, change SRC and START.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "channels" / "cribcommittee"
SRC = CH / "scripts_001-030.md"
START = 1

STYLE = ("Vertical 9:16, photorealistic, cinematic shallow depth of field, soft warm window light, "
         "gentle pastel nursery colours, natural baby skin texture, shot on a 50mm lens")
AUDIO_TAIL = "No music. No subtitles, no captions, no text on screen."
VOICE = "a tiny, clear, articulate toddler voice"

LOCATIONS = {
    "boardroom": ("a cosy nursery set up like a tiny boardroom: a low toddler-sized wooden table, stacked "
                  "building blocks, a sippy cup and a little water jug, a crib with wooden bars softly blurred behind",
                  "quiet room tone, a soft rattle shake"),
    "crib_side": ("beside a white wooden crib with a soft knitted blanket, plush toys lined up like a panel, "
                  "warm lamp light, mobile slowly turning above",
                  "quiet room tone, mobile tinkling faintly"),
}

# role: (char id, outfit/pose that never changes, delivery tone, gesture, camera, location)
ROLES = {
    "Chair":    ("chair", "wearing a tiny navy necktie over a white onesie and little round reading glasses, "
                 "sitting at the head of the toddler table", "seriously, like opening an official meeting",
                 "taps a soft toy gavel on the table once, then looks over the glasses into the lens",
                 "static medium shot, slow push-in", "boardroom"),
    "Sassy":    ("sassy", "in a bright pink knitted cardigan, one hand on hip, one eyebrow raised",
                 "with confident sass and a knowing look", "tilts the head and gives a slow unimpressed blink",
                 "static medium close-up, subtle handheld drift", "boardroom"),
    "Wise":     ("wise", "in a cosy oatmeal knitted jumper, calm and thoughtful, hands folded on the table",
                 "softly and sincerely, holding eye contact", "pauses, then speaks slowly and gently",
                 "very slow push-in on the face", "crib_side"),
    "Dramatic": ("dramatic", "in a little velvet bow tie and a tiny cape blanket over the shoulders",
                 "with over-the-top theatrical outrage", "throws both little arms up and flops back dramatically",
                 "static medium shot, quick small push-in on the outburst", "boardroom"),
    "Closer":   ("closer", "in a soft yellow onesie, holding a wooden toy gavel, a swaddled newborn in a "
                 "bassinet right beside", "warmly and decisively, like closing the meeting",
                 "taps the toy gavel once at the end", "slow push-in to a medium close-up", "crib_side"),
}

# Rotating faces: every clip a different baby (no recurring individuals).
BABIES = [
    "a chubby-cheeked 1-year-old Black baby boy with tight curls",
    "a 2-year-old white toddler girl with wispy blonde hair",
    "an 18-month-old South Asian baby boy with thick dark hair",
    "a 2-year-old East Asian toddler girl with a short fringe",
    "a 1-year-old mixed-race baby girl with soft brown curls",
    "a 2-year-old Latino toddler boy with big brown eyes",
    "an 18-month-old ginger white baby boy with freckles",
    "a 2-year-old Black toddler girl with two puff bunches",
    "a 1-year-old Middle Eastern baby boy with dark curls",
    "a 2-year-old Southeast Asian toddler boy with straight black hair",
    "an 18-month-old white baby girl with a tiny top-knot",
    "a 2-year-old Indian toddler girl with a small side clip",
    "a 1-year-old bald, round-faced white baby boy",
    "a 2-year-old Black toddler boy with a short fade",
    "an 18-month-old East Asian baby boy with spiky hair",
    "a 2-year-old Latina toddler girl with dark pigtails",
    "a 1-year-old North African baby girl with brown curls",
    "a 2-year-old white toddler boy with messy brown hair",
]

NEWBORN_SFX = {   # newborn reaction -> sound effect
    "burp": "a tiny loud newborn burp",
    "hiccup": "a single loud newborn hiccup",
    "sneeze": "a tiny newborn sneeze",
    "yawn": "a long squeaky newborn yawn",
    "raspberry": "a little newborn raspberry",
    "giggle": "a soft newborn giggle",
    "startle": "a tiny startled newborn squeak",
}

MUSIC = ["playful pizzicato", "boardroom jazz", "gentle music box", "light marimba"]


def parse(md: str):
    eps = []
    for block in re.split(r"^## ", md, flags=re.M)[1:]:
        head, *rest = block.strip().splitlines()
        m = re.match(r"(CC-\d{3}) - (.+)", head.strip())
        ep = {"id": m.group(1), "title": m.group(2).strip(), "lines": []}
        for ln in rest:
            ln = ln.strip()
            if ln.startswith("*Hook:*"):
                ep["hook"] = ln.split("*Hook:*", 1)[1].strip()
            elif ln.startswith("*Parenting note:*"):
                ep["note"] = ln.split("*Parenting note:*", 1)[1].strip()
            else:
                lm = re.match(r"\d\.\s+\*\*(\w+):\*\*\s+(.+)", ln)
                if lm:
                    text, newborn = lm.group(2), None
                    nb = re.search(r"\s*\(newborn:\s*(.+?)\)\s*$", text)
                    if nb:
                        newborn, text = nb.group(1), text[:nb.start()].strip()
                    ep["lines"].append((lm.group(1), text, newborn))
        eps.append(ep)
    return eps


def newborn_sound(desc):
    for k, v in NEWBORN_SFX.items():
        if k in desc:
            return v
    return "a tiny newborn noise"


def title(t):
    t = t.strip()
    return (t if len(t) <= 80 else t[:80].rstrip()) + " #shorts"


def build():
    out = []
    raw = parse(SRC.read_text())
    for i, e in enumerate(raw):
        n = START + i
        assert e["id"] == f"CC-{n:03d}", (e["id"], n)
        assert len(e["lines"]) == 5 and e["lines"][0][0] == "Chair" and e["lines"][4][0] == "Closer", e["id"]
        shots = []
        for k, (role, line, newborn) in enumerate(e["lines"]):
            cid, outfit, tone, gesture, camera, loc = ROLES[role]
            baby = BABIES[(i * 5 + k * 7) % len(BABIES)]   # 5 different faces per episode, rotating daily
            place, ambience = LOCATIONS[loc]
            chars = [cid]
            sfx = ambience
            extra = ""
            if newborn:
                chars.append("newborn")
                sound = newborn_sound(newborn)
                sfx = f"{ambience}; right after the last word, {sound}"
                extra = (f" Right after the last word, the swaddled newborn in the bassinet {newborn}, "
                         f"and the speaking baby glances at it.")
            prompt = (f"{STYLE}. {baby[0].upper() + baby[1:]}, {outfit}. Setting: {place}. "
                      f"The baby {gesture}. Camera: {camera}. "
                      f"The baby looks into the lens and speaks {tone}, in {VOICE}, with British English, "
                      f"lips clearly moving, saying: \"{line}\"{extra} "
                      f"Ambient sound: {sfx}. {AUDIO_TAIL}")
            shots.append({
                "n": k + 1, "dur": 8, "loc": loc, "chars": chars,
                "keyframe": f"{baby}, {outfit}, looking into the lens. Setting: {place}",
                "action": gesture + (f"; then the newborn {newborn}" if newborn else ""),
                "camera": camera,
                "lines": [{"c": cid, "t": line, "tone": tone}],
                "sfx": sfx,
                "flow_prompt": prompt,
            })
        desc = (f"The Crib Committee is in session. {e['note']} "
                "New meeting every day. Which baby is yours? Tell us below.")
        out.append({
            "id": e["id"], "number": n,
            "title": title(e["title"]),
            "logline": f"Committee meeting: {e['title']}. {e['note']}",
            "hook_text": e["hook"][:45],
            "description": desc,
            "tags": ["parenting", "parenting tips", "toddler", "baby", "gentle parenting", "mum life",
                     "dad life", "funny babies", "the crib committee", "shorts"],
            "music": MUSIC[i % len(MUSIC)],
            "shots": shots,
            "loop_note": "the Closer's gavel tap ends the meeting; the next Short opens with a new Chair",
        })
    return out


def bible():
    chars = {cid: {"name": role, "ref_prompt": f"a baby {outfit}", "home_location": loc, "voice": VOICE,
                   "tts_voice_id": ""}
             for role, (cid, outfit, *_x, loc) in ROLES.items()}
    chars["newborn"] = {"name": "Newborn", "ref_prompt": "a tiny swaddled newborn in a bassinet, never speaks",
                        "home_location": "crib_side", "voice": "newborn noises only", "tts_voice_id": ""}
    return {
        "channel_id": "cribcommittee",
        "show_title": "The Crib Committee",
        "tagline": "Babies hold a meeting about you. Real parenting wisdom, 40 seconds, motion carried.",
        "audience": "general (parents), NOT made for kids",
        "format": "One parenting topic per Short. Five different babies (Chair, Sassy, Wise, Dramatic, Closer), "
                  "one line each, 8 s per clip, spoken to camera. The Closer ends with 'Motion carried.' "
                  "and a newborn reaction.",
        "source": "flow",
        "episode_id_prefix": "CC",
        "target_seconds": [36, 44],
        "max_seconds": 90,
        "review_hours": 11,
        "style_prompt": STYLE,
        "audio_prompt": AUDIO_TAIL,
        "negative_prompt": "text, subtitles, logos, brands, celebrities, real identifiable people, unsafe sleep "
                           "setups, babies left unattended near hazards",
        "characters": chars,
        "locations": {k: v[0] for k, v in LOCATIONS.items()},
        "content_rules": [
            "Babies are AI-generated; never name them, never claim they are real children.",
            "Evidence-based, mainstream parenting ideas only. No medical, sleep-training, feeding or legal advice "
            "beyond general guidance; no products or brands.",
            "Line 1 is always the Chair opening the meeting; line 5 is the Closer ending 'Motion carried.'",
            "Each line <= 18 words so Veo can say it naturally in 8 s.",
            "Humour is kind: the babies tease parents lovingly, never shame them.",
        ],
        "music_moods": MUSIC,
        "made_for_kids": False,
        "youtube_category": "22",
        "nonverbal": False,
        "ai_disclosure": "The babies in this video are AI-generated characters (Google Veo). "
                         "The parenting tips are general guidance, not professional advice.",
        "overlays": {"hook": True, "captions": True},
        "end_card": {
            "enabled": True, "seconds": 4,
            "image": "assets/cribcommittee/endcard.png",
            "logo": "assets/cribcommittee/logo.png",
            "cta": "LIKE, SHARE AND SUBSCRIBE TO",
            "name": "THE CRIB COMMITTEE",
            "sub": "A NEW MEETING ABOUT YOU, EVERY DAY",
            "handle": "@TheCribCommittee",
            "initials": "CC",
            "colors": {"bg_top": "#1e3354", "bg_bottom": "#0f1a2e", "accent": "#f2b84b", "text": "#f5ecdc"},
            "_note": "Shorts only (not compilations). Edit text/colours here, then: python tools/make_endcard.py cribcommittee",
            "logo_size": 470, "logo_top": 190,
        },
        "flow": {"model": "Veo 3.1 Lite", "aspect": "9:16", "outputs_per_prompt": 1, "clip_seconds": 8,
                 "credits_per_clip": 10, "daily_free_credits": 50},
        "compilation_title": "{show} | {label} - {n} Committee Meetings Back to Back",
        "compilation_tags": ["parenting", "parenting tips", "funny babies", "toddler"],
        "compilations": {"weekly": True, "monthly": True},
    }


if __name__ == "__main__":
    (CH / "episodes").mkdir(parents=True, exist_ok=True)
    (CH / "channel.json").write_text(json.dumps(bible(), indent=2, ensure_ascii=False) + "\n")
    eps = build()
    for a in range(0, len(eps), 15):
        f = CH / "episodes" / f"eps_{START + a:03d}-{START + a + 14:03d}.json"
        f.write_text(json.dumps({"episodes": eps[a:a + 15]}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(eps)} episodes to {CH}")
