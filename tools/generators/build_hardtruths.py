"""Hard Truths (Ask The Elders TV): ONE elder, 8 lines, lip-synced from a single still, all free tools.

  python tools/generators/build_hardtruths.py      -> channels/elders/hardtruths.json

Writes ONLY channels/elders/hardtruths.json (never channel.json). Append new episodes at the END of EPISODES;
never reorder or edit published ones (state/hardtruths.json counts by position).

Script rules (checked here and by tools/validate.py):
- line 1: "I'm {age}." + a promise (the hook). Lines 2-8: seven hard truths, numbered 1-7 on screen.
- every truth line holds at least one WORD_BANK word (they glow gold in the captions).
- truths <= 14 words; the closer (line 8) <= 13 words, because the CTA is spoken right after it.
- original lines only (no famous quotes, book titles or sayings), no specific money/medical/legal advice,
  the elder is never named and never claimed to be real.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "channels" / "elders" / "hardtruths.json"

# Powerful words: these carry each line, and the captions colour them gold as they pop in.
WORD_BANK = {
    "trust & betrayal": ["trust", "betray", "betrayal", "loyal", "loyalty", "lie", "lies", "honest", "truth",
                         "promise", "promises", "enemy", "enemies", "smile", "smiles"],
    "the heart": ["love", "heart", "kind", "kindness", "cruel", "hurt", "hurting", "pain", "wound", "heal",
                  "tears", "cry", "laugh", "laughed", "hug", "proud", "pride", "ego", "envy", "jealousy",
                  "bitterness", "grudge", "shame", "ashamed", "fear", "scared", "brave", "courage"],
    "people": ["mother", "father", "family", "children", "friend", "friends", "friendship", "friendships",
               "marriage", "parents", "brothers", "alone", "lonely", "loneliest", "people", "strangers"],
    "money & work": ["money", "debt", "rich", "poor", "borrow", "broke", "greed", "raise", "job", "company",
                     "overtime", "burnout", "wealth", "bill"],
    "time & endings": ["time", "years", "today", "tonight", "last", "late", "funeral", "funerals", "goodbye",
                       "grave", "forget", "forgets", "forgiving", "forgive", "regret", "regrets", "never"],
    "inner life": ["peace", "silence", "quiet", "rest", "sleep", "respect", "faith", "hope", "strong",
                   "strongest", "weak", "enough", "grow", "growing", "gratitude", "integrity", "name", "stress", "thief"],
}
BANK = sorted({w for ws in WORD_BANK.values() for w in ws})

CTA = "Which one hit you? Comment the number."

# One elder per episode (never named). voice = Kokoro voice id (free, runs on the GitHub runner).
ELDERS = {
    "m_uk_flatcap": {"desc": "man with fair weathered skin, white stubble, deep laugh lines, wearing a tweed flat cap",
                     "gender": "m", "voice": "bm_george"},
    "m_west_africa": {"desc": "West African man with dark skin, short white hair, a neat white beard, kind tired eyes, "
                      "wearing a simple dark collared shirt", "gender": "m", "voice": "bm_lewis"},
    "f_caribbean": {"desc": "Caribbean woman with deep brown skin, silver hair tied back in a wrap, small gold earrings, "
                    "gentle but serious eyes", "gender": "f", "voice": "bf_emma"},
    "f_irish": {"desc": "woman with pale freckled skin, short silver curls, fine wrinkles, wearing a grey knitted cardigan",
                "gender": "f", "voice": "bf_isabella"},
    "m_south_asian": {"desc": "South Asian man with brown skin, thick white moustache, thinning white hair, "
                      "wearing a cream kurta", "gender": "m", "voice": "bm_george"},
    "f_east_asian": {"desc": "East Asian woman with fine lines, short silver bob, calm steady eyes, wearing a navy blouse",
                     "gender": "f", "voice": "bf_emma"},
    "m_mediterranean": {"desc": "Mediterranean man with olive tanned skin, a white beard, deep forehead lines, "
                        "wearing a dark wool coat", "gender": "m", "voice": "bm_lewis"},
    "f_nigeria": {"desc": "Nigerian woman with dark skin, grey hair under a patterned headwrap, wise strong face",
                  "gender": "f", "voice": "bf_isabella"},
}

IMAGE_PROMPT = ("Extreme close-up portrait photograph of a {age}-year-old {desc}, looking straight into the camera "
                "with a calm, serious expression, mouth gently closed, head and shoulders, face centred and filling "
                "most of the frame, eyes in the upper third, soft overcast window light from one side, muted "
                "grey-green colour grade, plain dark softly blurred background, natural skin texture with real "
                "wrinkles and pores, 85mm lens, shallow depth of field, photorealistic, cinematic, no text")

OPENERS = [
    "I'm {age}. Here's what I wish someone had told me at 25.",
    "I'm {age}. These are the hard truths about {theme} nobody tells you.",
    "I'm {age}. I learned these about {theme} the expensive way.",
    "I'm {age}. Seven truths about {theme} I'd tell my younger self.",
    "I'm {age}. Write these down before life teaches you the hard way.",
    "I'm {age}. Nobody warned me about these. So I'm warning you.",
]

# (theme, age, elder, opener index, [7 truths; the 7th is the closer, spoken just before the CTA])
EPISODES = [
    ("life at 25", 74, "m_uk_flatcap", 0, [
        "Don't trust too fast. Let people show you who they are, slowly.",
        "Some who clap for you in public never pray for you in private.",
        "Never borrow money you'd be ashamed to explain.",
        "Rest is not laziness. Your body keeps every receipt.",
        "Forgive them. Not for them. So you can finally sleep.",
        "Love the people who stayed when you had nothing.",
        "And call your mother, before the phone stops ringing back."]),
    ("money", 81, "m_west_africa", 2, [
        "Debt is a quiet thief. It steals your sleep before your money.",
        "Rich is not what you earn. It's what you keep.",
        "Never sign anything you were rushed to sign.",
        "A friend who only calls when broke is not a friend.",
        "Pay yourself first, even coins. That's how wealth starts.",
        "Looking rich has kept more people poor than bad luck ever did.",
        "And teach your children about money. Silence costs generations."]),
    ("family", 79, "f_caribbean", 1, [
        "Family won't always understand you. Love them anyway, from a distance if needed.",
        "The quiet child is often the one hurting most.",
        "Never let money come between brothers. No amount is worth it.",
        "Your parents were young once, and just as lost as you.",
        "Show up for the funerals. People remember who came.",
        "Don't keep score at home. Nobody wins that game, and love loses.",
        "And say I love you first. Pride makes a cold home."]),
    ("friendship", 86, "m_mediterranean", 3, [
        "Real friends are few. If you have three, you are rich.",
        "A friend who gossips to you will gossip about you.",
        "Distance doesn't end friendships. Silence does.",
        "Celebrate your friends loudly. Envy grows in quiet rooms.",
        "Some friendships are seasons. Let them end without bitterness.",
        "The friend who tells you the hard truth is worth ten who flatter.",
        "And visit that old friend this week. Time is not promised."]),
    ("work", 72, "f_irish", 5, [
        "Your job will replace you in a week. Your family won't.",
        "Nobody at your funeral will mention your overtime.",
        "Be loyal to your craft, not to a company.",
        "Ask for the raise. Fear has never paid a single bill.",
        "Respect is earned in small moments when nobody is watching.",
        "Burnout is not a badge of honour. It's a warning.",
        "And leave on time tonight. Someone at home is waiting."]),
    ("love", 83, "m_south_asian", 1, [
        "Marry someone kind. Looks fade, kindness grows.",
        "Love is a decision you make again every single morning.",
        "Never go to sleep as enemies. Talk, even if it's quietly.",
        "Jealousy is just fear wearing love's coat.",
        "Protect your marriage from outside opinions. Even family.",
        "Small kindness every day beats a grand gesture once a year.",
        "And hold her hand tonight. I'd give anything for one last time."]),
    ("forgiveness", 90, "f_nigeria", 4, [
        "A grudge is a heavy bag you carry for someone else.",
        "Forgiving is not forgetting. It's choosing peace over poison.",
        "Apologise quickly. Pride gets more expensive every year.",
        "Some people will never say sorry. Heal anyway.",
        "Bitterness ages a face faster than time does.",
        "Don't let one wound make you cruel to everyone.",
        "And forgive yourself too. You did your best with what you knew."]),
    ("regret", 77, "m_uk_flatcap", 5, [
        "I regret the chances I didn't take, never the ones that failed.",
        "Fear kept me safe and small for far too long.",
        "I worried about things that never happened. Wasted years.",
        "I chose being right over being kind. I lost people.",
        "I waited for the perfect time. It never came.",
        "I hid my tears from my children. They needed to see them.",
        "And I never said goodbye to my father properly. Don't wait."]),
    ("health", 69, "f_east_asian", 2, [
        "Your health is real wealth. I learned that in a hospital bed.",
        "Sleep is not a luxury. Nothing repairs you like it.",
        "Walk every day. Strong legs at seventy are built at forty.",
        "Stress is a slow thief. Learn to let things go.",
        "Listen when your body whispers, before the pain has to scream.",
        "Rest without guilt. Even fields need a season off.",
        "And laugh often. It's the one habit I never skipped."]),
    ("people", 85, "m_west_africa", 1, [
        "People show you who they are when you can't help them anymore.",
        "Respect shows in how someone treats a waiter, not a boss.",
        "Betrayal never comes from enemies. It needs someone close.",
        "Loyalty is rare. When you find it, protect it.",
        "Not everyone who smiles at you wishes you well.",
        "Believe what people do. Promises are cheap.",
        "And be the person you're looking for. Loyal, honest, kind."]),
    ("words", 88, "f_irish", 4, [
        "Silence is sometimes the strongest answer you can give.",
        "Words said in anger stay long after the anger leaves. They hurt.",
        "Not every argument deserves your presence or your peace.",
        "Speak well of people behind their backs. It always gets back.",
        "Never share your plans with people who doubt you.",
        "Lower your voice and people lean in. Shout and they leave.",
        "And think before you post. The internet never forgets."]),
    ("time", 93, "m_mediterranean", 0, [
        "Time is the only money you can never earn back.",
        "One ordinary Tuesday will become a memory you'd pay to relive. Notice it today.",
        "Stop waiting to be ready. Nobody ever is. Time won't wait.",
        "Ask your grandparents about their lives before time takes their stories.",
        "Hours on your phone are hours taken from your years.",
        "Don't save the good plates. Use them today.",
        "And hug longer. You never know which hug is the last."]),
    ("courage", 75, "f_caribbean", 3, [
        "I was scared every time I did something brave. Do it scared.",
        "Stop asking permission to live your own life. That takes courage.",
        "People are too busy with their own lives to judge yours for long.",
        "Say no without explaining. No is a full answer, and it's enough.",
        "Your voice shakes? Speak anyway. The truth still counts.",
        "Stop comparing your inside to strangers' photos.",
        "And bet on yourself once. Regret costs more than failure."]),
    ("children", 80, "m_south_asian", 4, [
        "Your children hear little of what you say. They copy what you do.",
        "Apologise to your children. It teaches them respect.",
        "Don't raise children to be rich. Raise them to be kind.",
        "Be home for the small moments. Children never forget who showed up.",
        "Let them fail while the stakes are small. That's love.",
        "Never compare your children. Each one remembers it.",
        "And tell them you're proud. Some of us waited our whole lives."]),
    ("loneliness", 84, "f_nigeria", 1, [
        "Being alone is not the same as being lonely.",
        "Learn to enjoy being alone. One day you'll need that skill.",
        "A crowded room of the wrong people is the loneliest place.",
        "Reach out first. Everyone is waiting for someone else to. Be the friend.",
        "Your phone is full of contacts. How many friends would come at midnight?",
        "Pride keeps more people lonely than distance ever did.",
        "And call the one you've been thinking about. Today, not someday."]),
    ("pride", 78, "m_west_africa", 2, [
        "The smartest people I knew asked the most questions.",
        "Ego gets you in the room. Humility keeps you there.",
        "You can be right and still lose the people who matter.",
        "Respect the cleaner and the boss the same way.",
        "Admit when you're wrong. Pride makes you a fool twice.",
        "Nobody cares about your titles once you retire. They remember kindness.",
        "And stay teachable. The day you know everything, you stop growing."]),
    ("hard times", 71, "f_east_asian", 5, [
        "Hard seasons end. I've survived every single one. Keep hope.",
        "Cry if you must, then wash your face and keep going.",
        "Your worst day is never your whole story.",
        "Ask for help. Strong people do it too.",
        "Some doors close to stop you walking into storms. Trust that.",
        "Gratitude won't fix your problems, but it shrinks them.",
        "And hold on. I nearly gave up the year before my best years."]),
    ("contentment", 87, "m_mediterranean", 1, [
        "Peace of mind is the most expensive thing I own.",
        "A small home full of love beats a mansion full of silence.",
        "Stop buying things to impress strangers.",
        "The simple life isn't boring. It's freedom, and it's enough.",
        "Envy will rob you of everything you already have.",
        "Enough is a number. Find yours before greed does.",
        "And go outside tonight and look up. Most people forget the sky."]),
    ("honesty", 82, "f_irish", 3, [
        "Your name goes everywhere before you do. Keep it clean.",
        "One lie needs ten more lies to protect it.",
        "Be honest even when it costs you. It costs more later.",
        "Your real integrity is who you are when the door is closed.",
        "Never trade your peace for someone's approval.",
        "Keep small promises. They prove the big ones.",
        "And when you're wrong, say it plainly. Respect follows the truth."]),
    ("getting older", 76, "m_uk_flatcap", 0, [
        "Fifty felt old. Now I'd give anything to be fifty. You're young today.",
        "Wear the nice clothes today, not someday. Your body keeps changing.",
        "Dance at the wedding. Nobody remembers who looked silly, only who was brave.",
        "Wrinkles mean you laughed. Don't hate them.",
        "Take the photos, and be in them. Family forgets faces.",
        "Your knees, your teeth, your heart. Look after them now.",
        "And enjoy this age today. One day you'll miss it terribly."]),
]

NUM_WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen " \
            "sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def bank_hits(line: str) -> list:
    words = [w.strip("'") for w in re.findall(r"[a-z']+", line.lower())]
    return [w for w in words if w in BANK or w.rstrip("s") in BANK]


def check(ep: dict) -> list:
    errs = []
    lines = ep["lines"]
    if len(lines) != 8:
        errs.append("needs 8 lines")
    if not lines[0].startswith(f"I'm {ep['age']}."):
        errs.append("line 1 must start with the age")
    for i, ln in enumerate(lines[1:], 2):
        n = len(ln.split())
        limit = 13 if i == 8 else 14
        if n > limit:
            errs.append(f"line {i} has {n} words (max {limit}): {ln}")
        if not bank_hits(ln):
            errs.append(f"line {i} has no word-bank word: {ln}")
    return errs


def build():
    eps, bad = [], []
    for n, (theme, age, elder, opener, truths) in enumerate(EPISODES, 1):
        e = ELDERS[elder]
        ep = {"id": f"HT-{n:03d}", "theme": theme, "age": age, "elder": elder,
              "lines": [OPENERS[opener].format(age=age, theme=theme)] + truths,
              "image_prompt": IMAGE_PROMPT.format(age=age, desc=e["desc"]),
              "voice": e["voice"]}
        errs = check(ep)
        if errs:
            bad += [f"{ep['id']}: {x}" for x in errs]
        eps.append(ep)
    return eps, bad


def main():
    eps, bad = build()
    cfg = {
        "brand": "Hard Truths",
        "show": "Ask The Elders TV",
        "id_prefix": "HT",
        "paused": True,
        "_paused_note": "true = render + keep in GitHub Release hardtruths-preview, no YouTube upload. "
                        "Set false once a preview is approved.",
        "publish_local": "19:00",
        "timezone": "Europe/London",
        "segment_seconds": 8,
        "cta": CTA,
        "music": "calm-piano",
        "music_volume": 0.16,
        "voice_speed": 0.86,
        "voice_pitch": 0.96,
        "look": {"grade": "grey-green", "caption_font": "DejaVuSans-Bold", "caption_size": 68,
                 "word": "#FFFFFF", "power_word": "#F2C84B", "label": "#C9D6C3"},
        "title_template": "Hard Truths About {Theme} From A {age}-Year-Old #shorts",
        "tags": ["hard truths", "life lessons", "elders", "wisdom", "advice", "life advice", "motivation"],
        "ai_disclosure": "The elder in this video is an AI-generated character (image: FLUX, voice: Kokoro TTS, "
                         "lip-sync: SadTalker). Not a real person. The lessons are real-world wisdom.",
        "word_bank": WORD_BANK,
        "episodes": eps,
    }
    OUT.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(eps)} episodes, {len(BANK)} power words")
    for b in bad:
        print("!!", b)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
