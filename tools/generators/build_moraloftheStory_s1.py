#!/usr/bin/env python3
"""Moral Of The Story TV, season 1: 6 story arcs x 6 parts (runs in the drizzlepudge channel slot).

Reads tools/generators/mos_arcs_screenplay.txt (compact screenplay) + the cast/location sheets below and writes
channels/drizzlepudge/channel.json + episodes/eps_001-018.json, eps_019-036.json. The old Drizzle & Pudge scripts
move to channels/drizzlepudge/archive/. Re-run safely.

Each part: 10 shots x 8 s = 80 s (+3 s "previously" recap from part 2 on). Every arc's cast and sets are
episode guests/locations with ids prefixed by the arc (a1_mama...), so reference portraits are generated ONCE
per arc and reused by every part: faces stay consistent from part 1 to the movie.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "channels" / "drizzlepudge"
SCREENPLAY = Path(__file__).with_name("mos_arcs_screenplay.txt")
SHOW = "Moral Of The Story TV"

CAM = {
    "CRASH": "dramatic crash zoom into a close-up, then hold",
    "CU": "close-up, slow push-in, shallow depth of field",
    "ECU": "extreme close-up on the eyes, very slow push-in",
    "MS": "medium shot, subtle handheld",
    "TWO": "two-shot, shallow focus, slow lateral dolly",
    "WIDE": "wide establishing shot, slow dolly-in",
    "TRACK": "tracking shot following the character, handheld",
    "LOW": "low-angle hero shot, slow push-in",
    "OTS": "over-the-shoulder shot, rack focus",
}

# Every person is a fictional adult, described visually with a FIXED outfit (keeps the reference portrait valid
# for the whole arc) and a FIXED voice (repeated in every shot prompt so the voice stays consistent).
CAST = {
 "a1": {
  "tobi": ("Tobi", "a 29-year-old Nigerian man, slim, short neat haircut, light beard, crisp white shirt with rolled sleeves", "a calm, warm young male voice"),
  "amara": ("Amara", "a 27-year-old Nigerian woman, natural hair in a neat bun, small gold earrings, soft peach blouse", "a clear, gentle but confident female voice"),
  "mama": ("Mrs Adebayo", "a 58-year-old Nigerian woman, elegant emerald lace blouse and wrapper with a matching head tie, gold necklace", "a commanding, proud older female voice"),
  "okafor": ("Mr Okafor", "a 62-year-old Nigerian man, short grey hair, reading glasses, simple cream kaftan", "a slow, dignified older male voice"),
  "femi": ("Uncle Femi", "a 50-year-old Nigerian man, slicked-back hair, gold watch, flashy patterned shirt", "a smooth, charming male voice"),
 },
 "a2": {
  "chidi": ("Chidi", "a 45-year-old Nigerian man, tall, rimless glasses, navy blazer over a black polo shirt", "a deep, clipped male voice"),
  "ngozi": ("Ngozi", "a 40-year-old Nigerian woman, sleek bob, red designer dress, gold bangles", "a sharp, assertive female voice"),
  "ifeoma": ("Ifeoma", "a 33-year-old Nigerian woman, simple braids tied back, plain grey blouse, gentle face", "a soft, steady female voice"),
  "barrister": ("Barrister Eze", "a 60-year-old Nigerian man, grey beard, black suit and tie, holding a folder", "a measured, formal older male voice"),
  "mama": ("Mama", "a 75-year-old Nigerian woman, short grey hair, soft blue blouse, kind eyes, seated in an armchair", "a frail, loving elderly female voice"),
  "emeka": ("Emeka", "a 38-year-old Nigerian man, kind face, short hair, brown suit jacket, chalk on his fingers", "a soft, warm male voice"),
 },
 "a3": {
  "grace": ("Madam Grace", "a 62-year-old Nigerian woman, neat grey braids in a bun, kind eyes, dignified posture, light-blue cleaner's uniform", "a calm, warm, dignified older female voice"),
  "kelechi": ("Kelechi", "a 32-year-old Nigerian man, sharp grey suit, sharp fade haircut, smartwatch", "an arrogant, clipped male voice"),
  "tolu": ("Tolu", "a 26-year-old Nigerian woman, round glasses, white blouse, staff lanyard", "a bright, earnest young female voice"),
 },
 "a4": {
  "dayo": ("Dayo", "a 31-year-old Nigerian man, athletic build, short twists, denim jacket over a white T-shirt", "a warm, expressive male voice"),
  "segun": ("Segun", "a 31-year-old Nigerian man, clean-shaven, round glasses, blue checked shirt", "a gentle, slightly husky male voice"),
  "funmi": ("Funmi", "a 29-year-old Nigerian woman, long braids, mustard-yellow dress", "a soft, anxious female voice"),
  "collector": ("The collector", "a tall, stern Nigerian man in a black leather jacket and dark sunglasses", "a low, menacing male voice"),
  "bimpe": ("Nurse Bimpe", "a 25-year-old Nigerian woman, short natural hair, teal nurse scrubs", "a calm, kind female voice"),
 },
 "a5": {
  "chief": ("Chief Balogun", "a 65-year-old Nigerian man, grey beard, rich royal-blue embroidered kaftan, gold rings", "a booming, proud older male voice"),
  "temi": ("Temi", "a 26-year-old Nigerian woman, graceful, long braids, lavender dress", "a warm, determined female voice"),
  "kunle": ("Kunle", "a 28-year-old Nigerian man, short hair, strong build, oil-stained grey overalls", "a calm, steady male voice"),
  "mama_kunle": ("Mama Kunle", "a 55-year-old Nigerian woman, kind round face, simple floral dress and headscarf", "a warm, knowing female voice"),
 },
 "a6": {
  "nkem": ("Nkem", "a 38-year-old Nigerian woman, elegant short natural hair, wine-coloured blouse, small diamond earrings", "a calm, controlled female voice"),
  "obinna": ("Obinna", "a 42-year-old Nigerian man, tall, trimmed beard, expensive grey suit", "a smooth, confident male voice"),
  "lola": ("Lola", "a 27-year-old Nigerian woman, long wavy hair, white dress", "a bright, emotional young female voice"),
  "rose": ("Aunty Rose", "a 50-year-old Nigerian woman lawyer, warm smile, black blazer over a colourful blouse", "a crisp, reassuring female voice"),
  "mama_obinna": ("Mama Obinna", "a 68-year-old Nigerian woman, stern, gold-rimmed glasses, royal-blue lace blouse and head tie", "a stern, commanding elderly female voice"),
 },
}

SETS = {
 "a1": {"parlour": "an upscale Lagos family living room, cream sofas, framed family portraits, a crystal chandelier, evening light through curtains",
        "okafor_home": "a modest, tidy sitting room with bookshelves, a wall clock and a ceiling fan, warm afternoon light",
        "office": "a modern tech office at night, glass walls, the glow of a laptop",
        "lounge": "a busy upscale lounge at night, neon accents, blurred patrons",
        "bank": "a bright modern bank hall with glass counters",
        "garden": "a garden decorated for a small wedding, fairy lights, white chairs, golden hour",
        "car": "the inside of a parked car at night, streetlights through a rain-streaked windscreen",
        "estate_gate": "a gated Lagos estate driveway at dusk, palm trees, a gleaming new SUV with a red ribbon",
        "okafor_gate": "the gate of a modest house at night, lit by a single bulb"},
 "a2": {"house": "a large old family house in Enugu, faded green walls, framed photos, an old armchair by the window",
        "compound": "the dusty front compound of an old family house, a big mango tree, parked cars",
        "lawyer_office": "a wood-panelled lawyer's office, shelves of files, a ceiling fan",
        "kitchen": "a small family kitchen, old pots, a window over the yard",
        "hospital": "a hospital room in soft hazy morning light",
        "road": "a highway at dawn through green hills, seen from inside a car",
        "school": "a modest primary school classroom, wooden desks, a chalkboard, children's drawings on the wall"},
 "a3": {"office_floor": "a modern open-plan Lagos office, desks, glass meeting rooms, city view",
        "lobby": "a glossy corporate lobby, marble floors, glass doors and a glass lift",
        "boardroom": "a sleek boardroom with a long table and a city skyline view",
        "pantry": "a small office kitchen with a kettle and mugs",
        "grace_home": "a humble, tidy flat with plants and old framed photographs",
        "car": "the back seat of a sleek black car at night, city lights passing",
        "street_night": "a busy Lagos roadside at night, food stalls, headlights"},
 "a4": {"apartment": "a cosy Lagos apartment living room with a small balcony, evening light",
        "shop": "a small fashion boutique with mannequins and rolls of fabric",
        "terminal": "a busy city bus terminal at dawn, yellow buses, vendors",
        "segun_room": "a small rented room, mattress on the floor, a laptop, one window",
        "abuja_street": "a quiet Abuja street at dawn, a row of small rented flats",
        "hospital2": "a hospital corridor and ward at night, soft blue light"},
 "a5": {"compound2": "a large Lagos tenement yard, rows of rooms, washing lines, a big iron gate",
        "mansion": "a grand Lagos mansion sitting room, gold accents, leather sofas, a large portrait on the wall",
        "workshop": "a roadside auto workshop, a car on a jack, tools, sparks",
        "kunle_room": "a small, neat one-room apartment, stacked books, a single bulb",
        "food_stall": "a roadside food stall with steaming pots under a big umbrella",
        "highway": "a dark expressway at midnight, hazard lights blinking, empty road"},
 "a6": {"home2": "an elegant Abuja living room, white sofas, modern art, evening lamps",
        "pharmacy": "a bright modern pharmacy with shelves of medicine and a counter",
        "lola_flat": "a stylish small apartment with fairy lights and a vanity mirror",
        "restaurant": "an upscale restaurant at night, candles, quiet tables",
        "lawyer2": "a calm modern law office, glass desk, city view",
        "village_house": "a big family house in a village, carved wooden doors, a shaded courtyard"},
}


def parse():
    arcs, arc, ep = [], None, None
    for raw in SCREENPLAY.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("ARC "):
            aid, title, logline, moral, music = [x.strip() for x in line[4:].split("|")]
            arc = {"id": aid, "title": title, "logline": logline, "moral": moral, "music": music, "eps": []}
            arcs.append(arc)
        elif line.startswith("EP "):
            title, hook, question = [x.strip() for x in line[3:].split("|")]
            ep = {"title": title, "hook": hook, "question": question, "shots": []}
            arc["eps"].append(ep)
        else:
            loc, chars, cam, trans, visual, rest = [x.strip() for x in line.split("|", 5)]
            lines, sfx = [x.strip() for x in rest.rsplit("|", 1)]
            ls = []
            for part in [p.strip() for p in lines.split("||") if p.strip()]:
                who, text = part.split(":", 1)
                text, tone = text.strip(), ""
                if text.endswith(")") and "(" in text:
                    text, tone = text[:text.rindex("(")].strip(), text[text.rindex("(") + 1:-1]
                ls.append((who.strip(), text, tone))
            ep["shots"].append({"loc": loc, "chars": [c for c in chars.split(",") if c], "cam": cam,
                                "trans": trans, "visual": visual, "lines": ls, "sfx": sfx})
    return arcs


def build():
    eps, n = [], 0
    for arc in parse():
        aid = arc["id"]
        guests = {f"{aid}_{k}": {"name": nm, "ref_prompt": ref, "voice": voice, "species": "human"}
                  for k, (nm, ref, voice) in CAST[aid].items()}
        locs = {f"{aid}_{k}": v for k, v in SETS[aid].items()}
        assert len(arc["eps"]) == 6, aid
        for p, e in enumerate(arc["eps"], start=1):
            n += 1
            finale = p == 6
            shots = []
            for i, s in enumerate(e["shots"]):
                assert len(e["shots"]) == 10, (aid, p, len(e["shots"]))
                shots.append({
                    "n": i + 1, "dur": 8, "loc": f"{aid}_{s['loc']}",
                    "chars": [f"{aid}_{c}" for c in s["chars"]],
                    "keyframe": s["visual"], "action": s["visual"], "camera": CAM[s["cam"]],
                    "lines": [{"c": f"{aid}_{w}", "t": t, "tone": tone} for w, t, tone in s["lines"]],
                    "sfx": s["sfx"], "transition": s["trans"] if i else "cut",
                    **({"freeze": 1.5} if (i == 9 and not finale) else {}),
                })
            q = e["question"]
            end = "" if finale else (f"{q}|FINALE TOMORROW" if p == 5 else f"{q}|PART {p + 1} TOMORROW")
            title = f"{e['hook']} | {arc['title']} Part {p}"
            title = (title[:80] + " #shorts") if len(title) <= 80 else (title[:77] + "... #shorts")
            tags = ["moral of the story", "nigerian drama", "short drama", "african drama", "family drama",
                    arc["title"].lower(), "storytime", "drama series"]
            eps.append({
                "id": f"MOS-{n:03d}", "number": n,
                "arc": aid, "arc_title": arc["title"], "arc_logline": arc["logline"],
                "part": p, "part_title": e["title"],
                "part_label": f"PART {p} OF 6 · {arc['title'].upper()}",
                "title": title, "hook_text": e["hook"],
                "logline": f"{arc['title']} part {p}, {e['title']}: " + " / ".join(
                    l[1] for sh in e["shots"][:3] for l in sh["lines"])[:200],
                "description": (f"{arc['logline']}\n\n{arc['title']}, part {p} of 6: {e['title']}."
                                + ("" if finale else f"\n\n{q.capitalize().rstrip('?')}? Tell us in the comments.")
                                + f"\n\n{SHOW}: a new story every week, and the full movie after every finale."),
                "tags": tags, "music": arc["music"],
                "guests": guests, "locations": locs,
                "end_card": end,
                **({"moral": arc["moral"], "arc_finale": True} if finale else {}),
                "captions": {
                    "tiktok": (f"{e['hook']} \U0001F633 Part {p}/6 · {arc['title']}. "
                               + (f"The moral of the story: {arc['moral']} " if finale else f"{q.capitalize()} ")
                               + "#moralofthestory #nigeriandrama #shortdrama #storytime #aidrama"),
                    "facebook": (f"{arc['title']}, part {p} of 6: {e['title']}. {arc['logline']} "
                                 + (f"The moral of the story: {arc['moral']}" if finale
                                    else f"{q.capitalize()} Follow {SHOW} for part {p + 1}.")),
                },
                "shots": shots,
                "loop_note": "cliffhanger freeze-frame; tomorrow opens with a 3 s 'previously' flash of it",
            })
    return eps


def bible():
    return {
        "channel_id": "drizzlepudge",
        "show_title": SHOW,
        "previous_format": "Drizzle & Pudge (kids cartoon) - scripts archived in channels/drizzlepudge/archive/",
        "tagline": "Every story has a twist. Every story has a lesson.",
        "audience": "general (13+), NOT made for kids",
        "format": ("Story arcs: one topic per arc, 6 parts of ~80 s (10 shots x 8 s) released daily, then the full "
                   "movie (all parts + title and moral cards, ~8.5 min, mid-roll eligible) 24 h after the finale. "
                   "Hook line first, a 3 s 'previously' flash from part 2, scene-change transitions, a freeze-frame "
                   "cliffhanger with a question, and the moral card in the finale."),
        "episode_id_prefix": "MOS",
        "target_seconds": [75, 90],
        "max_seconds": 90,
        "live_action": True,
        "made_for_kids": False,
        "youtube_category": "24",
        "nonverbal": False,
        "video_provider": "fal",
        "video_fallback": "fal_backup",
        "fal_video_endpoint": "fal-ai/veo3.1/lite/image-to-video",
        "fal_video_fallback_endpoint": "fal-ai/veo3.1/fast/image-to-video",
        "price_per_video_second": 0.05,
        "style_prompt": ("cinematic photoreal film still, shot on a digital cinema camera with anamorphic lenses, shallow "
                         "depth of field, motivated practical lighting, rich true-to-life dark skin tones, warm amber "
                         "highlights and soft teal shadows, gentle atmospheric haze, premium drama series look, "
                         "vertical 9:16 composition, subject centred, no text, no subtitles, no watermark"),
        "audio_prompt": ("clear natural dialogue in natural Nigerian English, never exaggerated, realistic room tone and "
                         "subtle Foley sound effects, no background music (music is added in post)"),
        "negative_prompt": "text, subtitles, captions, watermark, logo, cartoon, distorted faces, extra fingers, caricature, children",
        "cinema_vf": ("eq=contrast=1.07:saturation=1.06:gamma=0.98,"
                      "colorbalance=rs=0.03:bs=-0.03:rh=0.04:bh=-0.04,"
                      "noise=alls=6:allf=t+u,vignette=PI/5"),
        "recaps": True, "recap_seconds": 3.0, "recap_card": "PREVIOUSLY...",
        "arc_movies": True,
        "movie_title": "{arc} | Full Movie | {show}",
        "characters": {}, "locations": {},
        "guests_allowed": True,
        "music_moods": ["nollywood suspense", "tender strings", "tension drums"],
        "overlays": {"hook": True, "captions": True},
        "ai_disclosure": "Fictional story. All characters are AI-generated; any resemblance to real people is coincidental.",
        "content_rules": [
            "Fictional adults only. Dignified, modern, aspirational Nigerian settings and natural Nigerian English.",
            "Never caricature: no scam plots, no mocking accents, tribes or religion, no poverty played as a joke.",
            "Each arc: 6 parts x 10 shots x 8 s. Part 1 opens on the most explosive line. Parts 1-5 end on a freeze-frame "
            "cliffhanger + question card; part 6 resolves and ends on the moral card.",
            "One fixed outfit and one fixed voice description per character for the whole arc (consistency).",
            "<= 2 speakers per shot, <= 20 words per 8 s shot. Transitions only at scene changes (dip or flash).",
            "No children on screen (the video model blocks minors; mention them off-screen only).",
        ],
        "compilation_title": "{show} | {label}",
        "compilation_tags": ["full movie", "nigerian movie", "african drama", "moral of the story", "family drama"],
        "compilations": {"weekly": False, "monthly": False},
    }


if __name__ == "__main__":
    arch = CH / "archive"
    arch.mkdir(parents=True, exist_ok=True)
    for f in (CH / "episodes").glob("eps_*.json"):
        if json.loads(f.read_text())["episodes"][0]["id"].startswith("DP"):
            shutil.move(str(f), arch / f.name)
            print(f"archived old Drizzle & Pudge scripts: {f.name}")
    b = CH / "channel.json"
    if b.exists() and json.loads(b.read_text()).get("show_title", "").startswith("Drizzle"):
        shutil.copy(b, arch / "channel_drizzlepudge.json")
    b.write_text(json.dumps(bible(), indent=2, ensure_ascii=False) + "\n")
    eps = build()
    (CH / "episodes").mkdir(exist_ok=True)
    for a in (0, 18):
        (CH / "episodes" / f"eps_{a + 1:03d}-{a + 18:03d}.json").write_text(
            json.dumps({"episodes": eps[a:a + 18]}, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(eps)} Moral Of The Story episodes")
