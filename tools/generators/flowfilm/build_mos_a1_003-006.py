#!/usr/bin/env python3
"""Writes the flow-film JSONs for Arc 1 (The Wedding Fund) parts 3-6: tools/generators/flowfilm/MOS-00N_flowfilm.json.
Then install each:  python tools/generators/install_mos_flowfilm.py tools/generators/flowfilm/MOS-00N_flowfilm.json
Same format as MOS-001/002: 15 Flow clips, cut list, 'line' = on-screen speaker (lip-sync), 'vo' = heard over the shot.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

VOICES = {
    "a1_mama":   {"brief": "mature woman, 55-60, low, controlled, cold authority, unhurried", "tags": ["cold", "final", "proud"]},
    "a1_tobi":   {"brief": "young man, late 20s, warm, soft-spoken, strained under pressure", "tags": ["quiet", "whispers", "desperate"]},
    "a1_amara":  {"brief": "young woman, late 20s, gentle, clear, emotional, respectful", "tags": ["trembling", "hopeful"]},
    "a1_okafor": {"brief": "older man, 60s, slow, deep, tired dignity, a teacher's diction", "tags": ["slow", "hurt", "gentle"]},
    "a1_femi":   {"brief": "man, about 50, loud, charming, showy; can turn cold and quiet", "tags": ["laughing", "cold whisper"]},
}
ACCOUNTS = {"A": [1, 2, 3, 4, 5], "B": [6, 7, 8, 9, 10], "C": [11, 12, 13, 14, 15]}

# wardrobe/look, identical in every part so the start frames stay consistent
MAMA = "the older woman in emerald lace with a matching emerald head tie and gold necklace"
TOBI = "the young man with a short neat haircut and light beard in a crisp white shirt with rolled sleeves"
AMARA = "the young woman with her hair in a neat bun, small gold earrings and a soft peach blouse"
OKAFOR = "the grey-haired older man with reading glasses in a cream kaftan"
FEMI = "the man about 50 with slicked-back hair, a gold paisley shirt and a gold watch"

STYLE = "Photoreal, cinematic, shallow depth of field. No text."
KEEP = "Keep the exact face, hair, clothes and lighting from the start frame."
KEEPALL = "Keep the exact people, faces, clothes, place and lighting from the start frame."


def clip(n, scene, chars, faces, speaks, keyframe, action, sound, loc=None):
    keep = KEEPALL if faces != 1 else KEEP
    if faces == 0:
        keep = "Keep the exact hands, objects and lighting from the start frame. No faces."
    talk = "" if speaks else " Nobody speaks: no dialogue, no voices."
    c = {"n": n, "scene": scene, "chars": chars, "faces": faces, "speaks": speaks, "keyframe": keyframe,
         "flow_prompt": f"{keep} {action}{talk} Ambient sound only: {sound}; no music. {STYLE}"}
    if loc:
        c["loc"] = loc
    return c


def line(c, t, tag, at):
    return {"c": c, "t": t, "tag": tag, "at": at}


def cut(clip_n, i, d, **kw):
    e = {"clip": clip_n, "in": i, "dur": d}
    for k in ("line", "vo"):
        if k in kw:
            e[k] = line(*kw.pop(k))
    e.update(kw)
    return e


EPS = {}

# ---------------------------------------------------------------- MOS-003 Blame
EPS["MOS-003"] = {
    "scenes": {
        "A": {"title": "No Peace", "loc": "a1_parlour", "ambience_clip": 1, "music": "tension drums", "music_level": "low", "out": "dip"},
        "B": {"title": "The Engagement", "loc": "a1_okafor_home", "ambience_clip": 6, "music": "tender strings", "music_level": "low", "out": "flash"},
        "C": {"title": "Lost Her", "loc": "a1_office", "ambience_clip": 9, "music": "tension drums", "music_level": "rising", "out": "dip"},
        "D": {"title": "One Week", "loc": "a1_okafor_gate", "ambience_clip": 14, "music": "nollywood suspense", "music_level": "cut-on-last-line", "out": "freeze"},
    },
    "clips": [
        clip(1, "A", ["a1_mama", "a1_amara"], 2, False,
             f"Wide shot of an upscale living room at evening, crystal chandelier, cream sofas. {MAMA[0].upper() + MAMA[1:]} stands with one finger raised at {AMARA}, who stands a few steps away, shoulders tense. Both fully visible, faces small in frame. Exactly two people, nobody else.",
             "Slow dolly-in. The older woman jabs her raised finger; the young woman stands still, holding her ground.",
             "a wall clock ticking, a distant generator hum"),
        clip(2, "A", ["a1_mama"], 1, True,
             f"Medium close-up of {MAMA}, chandelier light on her face, furious, finger raised at someone off-camera, lips closed. Living room blurred behind her. Only her face in frame.",
             "Quick push-in that settles. She speaks furiously to someone off-camera, natural mouth movement. For the last three seconds she falls silent and holds a cold, furious stare.",
             "room tone, faint clock"),
        clip(3, "A", ["a1_amara"], 1, True,
             f"Close-up of {AMARA}, standing tall in a warm living room, eyes shining with held-back tears, chin up, lips closed. Background softly blurred. Only her face in frame.",
             "Static close-up. She answers respectfully but firmly to someone off-camera, voice shaking, natural mouth movement.",
             "room tone, clock ticking"),
        clip(4, "A", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI}, in a living room at evening, tired, eyes turned away from someone beside him, lips closed. Warm lamp light, background blurred. Only his face in frame.",
             "Static close-up. Without meeting anyone's eyes he speaks quietly and wearily, natural mouth movement, then looks at the floor.",
             "room tone"),
        clip(5, "A", ["a1_amara"], 1, True,
             f"Extreme close-up of {AMARA}, eyes filling with tears, staring at someone off-camera in disbelief, lips closed. Warm lamp light. Only her face in frame.",
             "Very slow push-in. For the first second a tear rolls down; then she speaks softly, heartbroken, natural mouth movement.",
             "room tone, a single soft breath"),
        clip(6, "B", ["a1_okafor", "a1_amara"], 2, False,
             f"Wide shot at the open front door of a modest, tidy home at evening, rain falling outside. {OKAFOR[0].upper() + OKAFOR[1:]} holds {AMARA} in a protective hug as she cries on his shoulder. Both visible, faces small. Exactly two people.",
             "Static wide shot. He holds his crying daughter close and strokes her back; rain falls behind them.",
             "steady rain, a ceiling fan whirring inside"),
        clip(7, "B", ["a1_okafor"], 1, True,
             f"Medium close-up of {OKAFOR}, standing inside a modest sitting room, firm and protective, looking at someone off-camera, lips closed. Bookshelves softly blurred, rain on the window behind. Only his face in frame.",
             "Static medium close-up. He speaks firmly and slowly, natural mouth movement. For the last three seconds he falls silent and looks down, his decision made.",
             "rain outside, ceiling fan"),
        clip(8, "B", [], 0, False,
             "Macro insert: an older man's hand with a cream kaftan sleeve picking up a simple mobile phone from a small wooden table beside a teacup, warm lamp light. Hand only, no faces. The phone screen is dark, no text.",
             "Macro shot, almost still. The hand lifts the phone slowly and steadily.",
             "rain outside, a teacup clink"),
        clip(9, "C", [], 0, False,
             "Macro insert in a dark glass office at night: a phone lying face-up on a desk next to a laptop, the phone screen glowing as it vibrates, cold blue light. No faces, no readable text.",
             "Macro shot, almost still. The phone vibrates twice on the desk, its glow pulsing.",
             "phone vibration, office air-conditioning hum"),
        clip(10, "C", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI}, alone in a dark glass-walled office at night, phone in hand below the frame, face lit cold blue, reading, lips closed. Only his face in frame.",
             "Static close-up. He reads, the colour drains from his face, and he speaks in panic to himself, natural mouth movement. For the last three seconds he covers his mouth with his hand and stares.",
             "air-conditioning hum"),
        clip(11, "C", ["a1_tobi"], 1, True,
             f"{TOBI[0].upper() + TOBI[1:]} driving at night, seen through the side window, city lights streaking across his face, rain on the glass, bitter expression, lips closed. Only his face in frame.",
             "Slow tracking shot alongside the car, lights sliding over his face. He speaks bitterly to himself, natural mouth movement, gripping the wheel.",
             "engine hum, rain on the car", loc="a1_car"),
        clip(12, "D", ["a1_tobi"], 1, False,
             f"Wide shot at night of the gate of a modest house lit by a single bulb, {TOBI} standing at the closed metal gate, one hand raised to knock, seen in three-quarter profile. Exactly one person.",
             "Static wide shot. He knocks on the metal gate three times, waits, and knocks again, moths circling the bulb.",
             "knocking on metal, crickets"),
        clip(13, "D", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI}, standing at a closed gate at night under a single bulb, pleading eyes, lips closed. Darkness behind him. Only his face in frame.",
             "Static close-up. He speaks desperately and respectfully to someone behind the gate, begging, natural mouth movement.",
             "crickets, a distant dog"),
        clip(14, "D", [], 0, False,
             "Macro insert at night: an older man's hand with a cream kaftan sleeve sliding back the bolt of a simple metal gate under a single bulb. Hand only, no faces.",
             "Macro shot, almost still. The hand slowly slides the bolt back and the gate creaks open a little.",
             "a metal bolt sliding, a gate creaking, crickets"),
        clip(15, "D", ["a1_okafor"], 1, True,
             f"Close-up of {OKAFOR}, standing in a half-open gateway at night under a single bulb, studying someone coldly, lips closed. Darkness behind. Only his face in frame.",
             "Slow push-in. He studies someone in silence for a moment, then speaks coldly and finally, natural mouth movement, and holds his stare.",
             "crickets"),
    ],
    "edit": [
        cut(2, 0.5, 4.2, line=("a1_mama", "Since you came, this family has known no peace!", "[furious]", 0.3), hook=True, sfx="boom"),
        cut(1, 1.0, 3.5),
        cut(3, 0.5, 4.4, line=("a1_amara", "Ma, I only told the truth about the car.", "[hurt, trembling]", 0.5)),
        cut(4, 0.5, 4.4, line=("a1_tobi", "Amara, not now. Let me handle my family.", "[tired]", 0.4)),
        cut(2, 5.2, 2.6),
        cut(5, 0.5, 5.2, line=("a1_amara", "Your family? I thought I was becoming your family.", "[quiet, devastated]", 1.4)),

        cut(6, 1.0, 5.0),
        cut(7, 0.5, 4.0, line=("a1_okafor", "My daughter will not beg to be accepted.", "[firm, protective]", 0.5)),
        cut(8, 1.0, 4.2, vo=("a1_okafor", "Tell Tobi's mother: the engagement is off.", "[final]", 0.4)),
        cut(7, 5.0, 3.0),

        cut(9, 1.5, 3.0, sfx_start="riser"),
        cut(10, 0.5, 4.5, line=("a1_tobi", "Engagement off? No, no, no.", "[panicking]", 1.2)),
        cut(10, 5.3, 2.5),
        cut(11, 0.5, 6.5, line=("a1_tobi", "I chose silence to protect them. And I lost her.", "[bitter]", 1.0)),

        cut(12, 1.0, 5.5),
        cut(13, 0.5, 5.0, line=("a1_tobi", "Sir, please. Give me one week. I'll bring the truth.", "[begging]", 0.6)),
        cut(14, 1.0, 2.5),
        cut(15, 0.5, 5.0, line=("a1_okafor", "One week. After that, don't come back.", "[cold]", 1.5), sfx="music cut + deep boom on the line", freeze=1.5),
    ],
}

# ---------------------------------------------------------------- MOS-004 The Bank
EPS["MOS-004"] = {
    "scenes": {
        "A": {"title": "Seven Withdrawals", "loc": "a1_bank", "ambience_clip": 1, "music": "tension drums", "music_level": "low", "out": "dip"},
        "B": {"title": "The Confession", "loc": "a1_car", "ambience_clip": 6, "music": "tender strings", "music_level": "low", "out": "dip"},
        "C": {"title": "Nobody Is Going Anywhere", "loc": "a1_parlour", "ambience_clip": 11, "music": "nollywood suspense", "music_level": "cut-on-last-line", "out": "freeze"},
    },
    "clips": [
        clip(1, "A", ["a1_tobi", "a1_mama"], 2, False,
             f"Wide shot of a bright modern bank hall with glass counters. {TOBI[0].upper() + TOBI[1:]} stands at a counter beside {MAMA}; papers lie on the counter between them. Both fully visible, faces small. Exactly two people, nobody else, no readable signs or text.",
             "Slow dolly-in. The young man turns to his mother; she keeps her eyes on the floor.",
             "quiet bank murmur, a printer, footsteps on tiles"),
        clip(2, "A", [], 0, False,
             "Macro insert: a young man's hand in a white rolled shirt sleeve slapping a stack of printed papers down onto a glass bank counter; the pages are out of focus, no readable text. Hand only, no faces.",
             "Macro shot. The hand slaps the papers down hard and spreads them with two fingers.",
             "a paper slap on glass, bank murmur"),
        clip(3, "A", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI}, standing at a bank counter in bright light, hard expression, looking at someone beside him, lips closed. Bank hall blurred behind. Only his face in frame.",
             "Static close-up. He speaks hard and low to someone beside him, natural mouth movement, tapping the counter once.",
             "bank murmur"),
        clip(4, "A", ["a1_mama"], 1, True,
             f"Close-up of {MAMA}, standing in a bright bank hall, eyes closed, refusing to look down at the counter, lips closed. Only her face in frame.",
             "Static close-up. With her eyes still closed she speaks quietly, almost begging, natural mouth movement. For the last three seconds she opens her eyes, guilty, and looks away.",
             "bank murmur"),
        clip(5, "A", ["a1_tobi"], 1, True,
             f"Over-the-shoulder shot: the blurred back of an emerald head tie in the left foreground (no face visible), and beyond it, in sharp focus, {TOBI}, stunned, realisation dawning, lips closed. Only his face is visible.",
             "Static over-the-shoulder shot; the woman in the foreground never turns around. He stares at her, then speaks in stunned disbelief, natural mouth movement.",
             "a low drone of bank noise"),
        clip(6, "B", ["a1_mama", "a1_tobi"], 2, False,
             f"Wide shot through the windscreen of a parked car at night, rain streaking the glass: {MAMA} in the passenger seat and {TOBI} in the driver's seat, both staring ahead. Both faces visible, small. Exactly two people.",
             "Static shot through the windscreen, rain running down the glass. The woman stares ahead and her lips tremble; the young man turns slowly to look at her.",
             "heavy rain on the car roof, wipers off"),
        clip(7, "B", ["a1_mama"], 1, True,
             f"Close-up of {MAMA} in the passenger seat of a parked car at night, tears on her cheeks, streetlight through the rainy window on her face, lips closed. Only her face in frame.",
             "Static close-up, rain shadows moving on her face. She confesses quietly, full of shame, natural mouth movement.",
             "rain on the roof"),
        clip(8, "B", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI} in the driver's seat of a parked car at night, rain shadows on his face, shaking his head slowly in disbelief, lips closed. Only his face in frame.",
             "Static close-up. He shakes his head, then speaks in disbelief to the woman beside him, natural mouth movement.",
             "rain on the roof"),
        clip(9, "B", ["a1_mama"], 1, True,
             f"Extreme close-up of {MAMA} in a dark car, trembling lips, wet eyes looking down, rain light on her skin, lips closed. Only her face in frame.",
             "Very slow push-in. She whispers a painful confession, trembling, natural mouth movement, then closes her eyes.",
             "rain, a soft heartbeat of silence"),
        clip(10, "C", ["a1_mama"], 1, True,
             f"Medium close-up of {MAMA} alone in a dark living room at night, looking up at something on the wall above the frame, lamp light on her face, broken, lips closed. Only her face in frame.",
             "Static shot. She gazes up at something on the wall and speaks quietly to herself, broken, natural mouth movement.",
             "a clock ticking in a quiet house"),
        clip(11, "C", [], 0, False,
             "Macro insert at night: a woman's hand with gold rings and an emerald lace sleeve touching the edge of a large gilded picture frame on a wall, lamp light. Hand only, no faces, the picture itself not visible.",
             "Macro shot, almost still. Her fingers trace the edge of the frame slowly.",
             "a clock ticking, quiet house"),
        clip(12, "C", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI} kneeling in a dark living room at night, looking up at someone above him with gentle eyes, lamp light, lips closed. Only his face in frame.",
             "Static close-up, slight upward angle. He speaks gently and warmly up to someone, natural mouth movement, a small hopeful smile.",
             "a clock ticking"),
        clip(13, "C", [], 0, False,
             "Macro insert: a young man's hands in white rolled shirt sleeves holding an older woman's hands with gold rings and emerald lace sleeves, lamp light, shallow depth of field. Hands only, no faces.",
             "Macro shot, almost still. He squeezes her hands; her fingers close around his.",
             "soft fabric rustle, clock ticking"),
        clip(14, "C", ["a1_femi"], 1, True,
             f"Close-up of {FEMI} standing in a dark doorway at night, half his face in shadow, listening, face hardening, lips closed. Only his face in frame.",
             "Slow push-in. He listens in silence, his jaw tightening, then speaks low and menacing, natural mouth movement, and goes still.",
             "the quiet of a dark house"),
        clip(15, "C", ["a1_tobi", "a1_mama"], 2, False,
             f"Wide shot from behind a man standing in a dark doorway: his blurred dark silhouette fills the left foreground, no face visible. Across the dim living room, {TOBI} kneels beside {MAMA} under a lamp; both turn their heads toward the doorway. Exactly two visible faces, small.",
             "Static shot. The silhouette in the doorway stays still and never turns; the mother and son slowly turn to look toward him, frightened.",
             "a floorboard creak, clock ticking"),
    ],
    "edit": [
        cut(3, 0.5, 4.4, line=("a1_tobi", "Seven withdrawals, Mummy. Every one signed by Uncle Femi.", "[hard]", 0.3), hook=True, sfx="boom"),
        cut(2, 1.0, 3.0),
        cut(1, 1.0, 4.5),
        cut(4, 0.5, 4.0, line=("a1_mama", "Put it away, Tobi. Please.", "[quiet]", 1.2)),
        cut(5, 0.5, 5.0, line=("a1_tobi", "You're not surprised. Mummy, you knew?", "[stunned]", 1.2)),
        cut(4, 5.0, 3.0),

        cut(6, 0.5, 7.0, vo=("a1_mama", "Fifteen years ago, I was dying. Femi paid my hospital bills.", "[confessing]", 0.6)),
        cut(7, 0.5, 5.5, line=("a1_mama", "When he took the money, I told myself I owed him.", "[shame]", 0.6)),
        cut(8, 0.5, 5.0, line=("a1_tobi", "So the fifteen million was to cover his hole?", "[disbelief]", 0.5)),
        cut(9, 0.5, 6.0, line=("a1_mama", "If the in-laws paid, nobody would ask questions. God forgive me.", "[whispers]", 0.6), sfx="heartbeat"),

        cut(11, 1.0, 3.5),
        cut(10, 0.5, 5.0, line=("a1_mama", "I protected my brother and broke my son.", "[broken]", 1.0)),
        cut(12, 0.5, 5.8, line=("a1_tobi", "Then fix it with me, Mummy. Tomorrow we go to the Okafors.", "[gentle]", 0.6)),
        cut(13, 1.0, 3.5),
        cut(15, 1.0, 4.0, sfx_start="riser"),
        cut(14, 0.5, 5.0, line=("a1_femi", "Nobody is going anywhere.", "[cold, menacing]", 2.0), sfx="music cut + deep boom on the line", freeze=1.5),
    ],
}

# ---------------------------------------------------------------- MOS-005 Pride
EPS["MOS-005"] = {
    "scenes": {
        "A": {"title": "Your Name", "loc": "a1_parlour", "ambience_clip": 1, "music": "tension drums", "music_level": "low", "out": "dip"},
        "B": {"title": "On Her Knees", "loc": "a1_okafor_home", "ambience_clip": 7, "music": "tender strings", "music_level": "rising", "out": "flash"},
        "C": {"title": "The Briefcase", "loc": "a1_okafor_gate", "ambience_clip": 14, "music": "nollywood suspense", "music_level": "cut-on-last-line", "out": "freeze"},
    },
    "clips": [
        clip(1, "A", ["a1_femi", "a1_mama"], 2, False,
             f"Wide shot of an upscale living room at night, chandelier glowing. {FEMI[0].upper() + FEMI[1:]} looms over {MAMA}, who stands her ground by the sofa. Both visible, faces small. Exactly two people, nobody else.",
             "Slow dolly-in. The man steps closer, towering over her; she does not move back.",
             "a clock ticking, a distant generator hum"),
        clip(2, "A", ["a1_femi"], 1, True,
             f"Close-up of {FEMI}, in a living room at night, leaning in threateningly toward someone off-camera, lips closed. Chandelier blurred behind. Only his face in frame.",
             "Static close-up. He speaks low and threatening to someone off-camera, natural mouth movement. For the last three seconds he falls silent, shocked, his eyes widening.",
             "room tone"),
        clip(3, "A", ["a1_mama"], 1, True,
             f"Medium close-up of {MAMA}, standing straight and fearless in a living room at night, chin raised, looking at someone off-camera, lips closed. Only her face in frame.",
             "Static medium close-up. She speaks with iron calm, natural mouth movement, never blinking.",
             "room tone, clock"),
        clip(4, "A", ["a1_femi"], 1, True,
             f"Medium shot of {FEMI}, in a living room at night, both hands thrown up defensively, lips closed. Only his face in frame.",
             "Static medium shot. He throws up his hands and argues defensively and loudly, natural mouth movement, then sets a glass down hard on a side table.",
             "a glass set down hard, room tone"),
        clip(5, "A", ["a1_tobi"], 1, True,
             f"Over-the-shoulder shot: the blurred back of a man's slicked-back head and gold paisley collar in the right foreground (no face visible), and beyond, in sharp focus, {TOBI}, holding out his open palm, cold steady eyes, lips closed. Only the young man's face is visible.",
             "Static over-the-shoulder shot; the man in the foreground never turns. The young man holds out his palm and speaks coldly and calmly, natural mouth movement.",
             "room tone"),
        clip(6, "A", [], 0, False,
             "Macro insert: a man's hand with a gold watch dropping a set of shiny car keys with a small red ribbon into a young man's open palm in a white rolled sleeve, chandelier light. Hands only, no faces, no logos.",
             "Macro shot, almost still. The keys drop slowly into the open palm, which closes around them.",
             "keys jangling"),
        clip(7, "B", ["a1_mama", "a1_okafor"], 2, False,
             f"Wide shot of a modest, tidy sitting room in warm afternoon light, bookshelves, ceiling fan. {MAMA[0].upper() + MAMA[1:]} enters with her head bowed; {OKAFOR} sits at a small wooden table, looking up. Both visible, faces small. Exactly two people.",
             "Slow dolly-in. She steps in humbly with her head bowed and stops; he sets down his teacup.",
             "ceiling fan whirring, distant traffic"),
        clip(8, "B", ["a1_mama"], 1, True,
             f"Medium close-up of {MAMA}, standing humbly in a modest sitting room, eyes lowered, hands clasped, lips closed. Bookshelves blurred. Only her face in frame.",
             "Static medium close-up. She lifts her eyes and speaks humbly to someone seated off-camera, natural mouth movement.",
             "ceiling fan"),
        clip(9, "B", ["a1_okafor"], 1, True,
             f"Close-up of {OKAFOR}, seated at a small table, studying someone over the top of his reading glasses, measured expression, lips closed. Warm light. Only his face in frame.",
             "Static close-up. He studies her over his glasses, then speaks slowly and measuredly, natural mouth movement.",
             "ceiling fan, a clock ticking"),
        clip(10, "B", ["a1_mama"], 1, True,
             f"Medium shot of {MAMA} kneeling on a woven rug in a modest sitting room, looking up, tears on her face, lips closed. Only her face in frame.",
             "Static medium shot. Kneeling, she pleads tearfully up to someone, natural mouth movement. For the last two seconds she bows her head and weeps silently.",
             "ceiling fan, soft sobbing breath"),
        clip(11, "B", ["a1_amara"], 1, True,
             f"Medium close-up of {AMARA}, standing in a doorway of a modest home, one hand over her mouth in shock, lips hidden, eyes wet. Only her face in frame.",
             "Static shot. She gasps, lowers her hand and speaks emotionally to someone kneeling, natural mouth movement, stepping forward.",
             "a gasp, ceiling fan"),
        clip(12, "B", ["a1_okafor"], 1, True,
             f"Close-up of {OKAFOR}, standing and reaching one hand down toward someone below the frame, his face softening into warmth, lips closed. Only his face in frame.",
             "Static close-up. He reaches down and speaks warmly, natural mouth movement, with a gentle smile.",
             "ceiling fan"),
        clip(13, "B", [], 0, False,
             "Macro insert: an older man's hand in a cream kaftan sleeve clasping an older woman's hand with gold rings and an emerald lace sleeve, helping her up, warm afternoon light. Hands only, no faces.",
             "Macro shot. The hands clasp firmly and lift upward together.",
             "fabric rustle, ceiling fan"),
        clip(14, "C", ["a1_femi"], 1, False,
             f"Wide shot at dusk of the gate of a modest house lit by a single bulb: {FEMI} stands outside the gate holding a black leather briefcase in both hands. Exactly one person.",
             "Slow push-in. He stands still at the gate, gripping the briefcase, glancing up at the house.",
             "crickets, a distant car"),
        clip(15, "C", ["a1_femi"], 1, True,
             f"Close-up of {FEMI} at a gate at dusk, a black briefcase raised in front of his chest, urgent eyes, lips closed. Single bulb light. Only his face in frame.",
             "Slow push-in. He lifts the briefcase slightly and speaks urgently to someone off-camera, natural mouth movement, then holds still.",
             "crickets"),
    ],
    "edit": [
        cut(2, 0.5, 4.4, line=("a1_femi", "You will ruin my name for that small family?", "[threatening]", 0.3), hook=True, sfx="boom"),
        cut(1, 1.0, 4.0),
        cut(3, 0.5, 5.2, line=("a1_mama", "Your name was ruined the day you stole from my son.", "[iron, cold]", 0.5)),
        cut(2, 5.2, 2.6),
        cut(4, 0.5, 4.5, line=("a1_femi", "Stole? I invested! The market crashed. It happens!", "[defensive]", 0.5)),
        cut(5, 0.5, 4.0, line=("a1_tobi", "Then sell the car, Uncle. Today.", "[cold]", 0.6)),
        cut(6, 1.0, 3.5),

        cut(7, 1.0, 5.5),
        cut(8, 0.5, 4.6, line=("a1_mama", "Mr Okafor, I came to apologise. I was wrong.", "[humble]", 0.6)),
        cut(9, 0.5, 5.0, line=("a1_okafor", "Madam, pride is an expensive habit. Who will pay for it?", "[measured]", 0.4)),
        cut(10, 0.5, 5.0, line=("a1_mama", "I will. Please, don't punish our children for my sins.", "[tearful]", 0.6)),
        cut(11, 0.5, 4.0, line=("a1_amara", "Mummy, please, get up.", "[emotional]", 0.9)),
        cut(10, 5.5, 2.5),
        cut(12, 0.5, 5.0, line=("a1_okafor", "Get up, my sister. Now let us talk like family.", "[warm]", 0.6)),
        cut(13, 1.0, 3.5),

        cut(14, 1.0, 6.0, sfx_start="riser"),
        cut(15, 0.5, 5.4, line=("a1_femi", "Before you decide anything, open this.", "[urgent]", 1.8), sfx="music cut + deep boom on the line", freeze=1.5),
    ],
}

# ---------------------------------------------------------------- MOS-006 The Truth (finale)
EPS["MOS-006"] = {
    "scenes": {
        "A": {"title": "The Briefcase", "loc": "a1_okafor_home", "ambience_clip": 3, "music": "tender strings", "music_level": "low", "out": "dip"},
        "B": {"title": "No More Secrets", "loc": "a1_garden", "ambience_clip": 8, "music": "tender strings", "music_level": "rising", "out": "freeze"},
    },
    "clips": [
        clip(1, "A", [], 0, False,
             "Macro insert: an open black briefcase on a small wooden table in warm evening light, filled with neat paper-banded bundles of cash and a folded document, a man's hand with a gold watch resting on the lid. Hand only, no faces, no readable text.",
             "Macro shot, almost still. The hand slowly pushes the open briefcase forward across the table.",
             "briefcase latches clicking, a ceiling fan"),
        clip(2, "A", ["a1_femi"], 1, True,
             f"Medium close-up of {FEMI}, standing in a modest sitting room at evening, humbled, shoulders low, looking at people off-camera, lips closed. Bookshelves blurred. Only his face in frame.",
             "Static medium close-up. He speaks quietly and humbly to the room, natural mouth movement.",
             "ceiling fan, room tone"),
        clip(3, "A", ["a1_femi", "a1_okafor", "a1_mama", "a1_tobi", "a1_amara"], 5, False,
             f"Wide shot of a modest sitting room at evening, bookshelves, ceiling fan: {FEMI} stands by a small wooden table with an open black briefcase; {OKAFOR} sits at the table; {MAMA} and {TOBI} stand nearby; {AMARA} stands by the window. All five visible, faces small. Exactly five people, nobody else.",
             "Slow dolly-in. Everyone is still and silent, looking at the briefcase; the ceiling fan turns.",
             "ceiling fan whirring, a clock ticking"),
        clip(4, "A", ["a1_femi"], 1, True,
             f"Close-up of {FEMI}, eyes lowered in shame, voice about to crack, lips closed. Warm lamp light, background blurred. Only his face in frame.",
             "Very slow push-in. He keeps his eyes down, then looks up and apologises, voice cracking, natural mouth movement.",
             "room tone"),
        clip(5, "A", ["a1_tobi"], 1, True,
             f"Close-up of {TOBI}, in a modest sitting room at evening, exhaling, the anger leaving his face, lips closed. Only his face in frame.",
             "Static close-up. He exhales slowly, his face softens, and he speaks quietly, natural mouth movement.",
             "room tone, ceiling fan"),
        clip(6, "A", ["a1_okafor"], 1, True,
             f"Medium close-up of {OKAFOR}, seated at a small wooden table, one hand gently pushing something away across the table, wise calm expression, lips closed. Only his face in frame.",
             "Static medium close-up. He gently pushes the briefcase back and speaks with calm wisdom, natural mouth movement.",
             "ceiling fan, a clock ticking"),
        clip(7, "A", ["a1_mama"], 1, True,
             f"Close-up of {MAMA}, smiling through tears in warm lamp light, lips closed. Only her face in frame.",
             "Static close-up. She wipes a tear, smiles, and speaks warmly, natural mouth movement, then laughs softly.",
             "room tone"),
        clip(8, "B", ["a1_amara", "a1_tobi"], 2, False,
             "Wide shot of a small garden wedding at golden hour, fairy lights strung overhead, rows of white chairs, a simple flower arch. The young woman with her hair in a neat bun, in a simple white lace dress, faces the young man with a light beard in a cream suit under the arch. Both visible, faces small. Exactly two people, nobody else.",
             "Slow crane-down. The couple stand facing each other and hold hands under the arch; fairy lights twinkle.",
             "birdsong, soft wind"),
        clip(9, "B", ["a1_amara"], 1, True,
             "Close-up of the young woman with her hair in a neat bun and small gold earrings, in a simple white lace dress, under fairy lights at golden hour, soft hopeful eyes, lips closed. Only her face in frame.",
             "Static close-up. She asks a soft question to someone in front of her, natural mouth movement, then smiles.",
             "birdsong"),
        clip(10, "B", ["a1_tobi"], 1, True,
             "Close-up of the young man with a short neat haircut and light beard, in a cream suit, under fairy lights at golden hour, sincere eyes, lips closed. Only his face in frame.",
             "Static close-up. He answers sincerely, natural mouth movement, with a slow smile.",
             "birdsong"),
        clip(11, "B", ["a1_mama"], 1, True,
             f"Medium close-up of {MAMA}, seated at a garden table with a plate of rice, laughing, fairy lights behind, lips closed. Only her face in frame.",
             "Static medium close-up. She laughs and teases someone beside her, natural mouth movement. For the last three seconds she keeps laughing without words.",
             "garden chatter, cutlery"),
        clip(12, "B", ["a1_okafor"], 1, True,
             f"Close-up of {OKAFOR}, seated at a garden table at golden hour, a dry little smile, lips closed. Fairy lights blurred. Only his face in frame.",
             "Static close-up. He answers with two dry words, natural mouth movement, then raises an eyebrow.",
             "garden chatter, cutlery"),
        clip(13, "B", ["a1_femi"], 1, True,
             "Medium close-up of the man about 50 with slicked-back hair, in a plain white shirt, carrying a tray of drinks through a garden wedding at golden hour, humble smile, lips closed. Background blurred. Only his face in frame.",
             "Slow tracking shot. He serves a drink and speaks sincerely, natural mouth movement, nodding humbly.",
             "glasses clinking, garden chatter"),
        clip(14, "B", ["a1_amara"], 1, True,
             "Over-the-shoulder close-up at golden hour: the blurred back of a young man's head and cream suit collar in the foreground (no face visible); the young woman in the white lace dress, hair in a neat bun, faces him, foreheads almost touching, slow-dancing, lips closed. Only her face is visible.",
             "Slow circling camera. They sway slowly; she speaks tenderly to him, natural mouth movement. For the last two seconds they rest foreheads together in silence.",
             "soft wind, birdsong"),
        clip(15, "B", [], 0, False,
             "High crane shot rising over a small glowing garden wedding at sunset: fairy lights, white chairs, tiny figures dancing far below, no faces visible, palm trees and an orange sky.",
             "Slow crane up and away from the garden into the sunset sky.",
             "soft wind, distant laughter"),
    ],
    "edit": [
        cut(2, 0.5, 4.8, line=("a1_femi", "The car is sold. This is eight million. All I have.", "[humbled]", 0.4), hook=True, sfx="boom"),
        cut(1, 1.0, 3.5),
        cut(3, 1.0, 5.0),
        cut(4, 0.5, 4.8, line=("a1_femi", "I gambled your wedding away, Tobi. I'm sorry.", "[ashamed, voice cracking]", 1.0)),
        cut(5, 0.5, 4.6, line=("a1_tobi", "Thank you for finally telling the truth, Uncle.", "[quiet]", 0.8)),
        cut(6, 0.5, 5.0, line=("a1_okafor", "Keep your millions. Our children need a home, not a show.", "[wise]", 0.5)),
        cut(7, 0.5, 5.2, line=("a1_mama", "A small wedding, then. With truth, and with love.", "[warm]", 0.6)),

        cut(8, 1.0, 6.0),
        cut(9, 0.5, 3.0, line=("a1_amara", "No more secrets?", "[soft]", 0.8)),
        cut(10, 0.5, 3.4, line=("a1_tobi", "No more secrets. Ever.", "[sincere]", 0.6)),
        cut(11, 0.5, 4.2, line=("a1_mama", "In-law, your jollof is better than mine.", "[laughing]", 0.4)),
        cut(12, 0.5, 3.0, line=("a1_okafor", "I know.", "[dry]", 1.0)),
        cut(11, 5.0, 2.6),
        cut(13, 0.5, 5.0, line=("a1_femi", "Today, I serve. It's the least I can do.", "[sincere]", 0.6)),
        cut(14, 0.5, 4.6, line=("a1_amara", "We built this on the truth.", "[tender]", 1.2)),
        cut(14, 5.3, 2.5),
        cut(15, 0.5, 7.0, freeze=1.5),
    ],
}

for ep_id, body in EPS.items():
    data = {"_format": f"flow-film v1 (same as MOS-001). {ep_id}, Arc 1 The Wedding Fund. Built by build_mos_a1_003-006.py.",
            "id": ep_id, "format": "flow-film", "accounts": ACCOUNTS, "voices": VOICES, **body}
    p = OUT / f"{ep_id}_flowfilm.json"
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"   wrote {p.name}: {len(body['clips'])} clips, {len(body['edit'])} cuts, "
          f"{sum(e['dur'] + e.get('freeze', 0) for e in body['edit']):.1f} s")
