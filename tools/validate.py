#!/usr/bin/env python3
"""Validate every episode script against its channel bible.

Usage:  python tools/validate.py            # all channels
        python tools/validate.py flat4b     # one channel
Exit code 1 if any ERROR is found (pipeline must not render broken scripts).
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_DUR = {6, 8, 10}          # clip lengths every recommended model supports
MAX_WPS_ERROR = 3.0               # words per second of dialogue -> impossible to say
MAX_WPS_WARN = 2.6                # rushed
REQUIRED_EP = ["id", "number", "title", "logline", "hook_text", "description", "tags", "music", "shots"]
REQUIRED_SHOT = ["n", "dur", "loc", "chars", "keyframe", "action", "camera", "lines", "sfx"]


def load_episodes(ch_dir):
    eps = []
    for f in sorted((ch_dir / "episodes").glob("*.json")):
        data = json.loads(f.read_text())
        for ep in data["episodes"]:
            ep["_file"] = f.name
            eps.append(ep)
    return eps


def words(text):
    return len(re.findall(r"[A-Za-z0-9']+", text))


FF_TRANSITIONS = {"dip", "flash", "freeze", "cut"}
FF_CLIPS = 15     # 3 Flow accounts x 5 free clips a day
# start frames and Flow prompts describe people by look, never by nationality, ethnicity or accent
FF_BANNED = re.compile(r"\b(accents?|accented|ethnic\w*|tribal|tribes?|nationality|nigerians?|ghanaians?|kenyans?|"
                       r"africans?|west african|yorubas?|igbos?|hausas?|(black|white|asian) (man|woman|men|women|"
                       r"person|people|girl|boy|family))\b", re.I)


def validate_flowfilm(ep, tag, bible, chars, locs, errors, warns):
    """Flow-film episode (Google Flow clips + cut list). Returns the story length in seconds."""
    clip_s = float(bible.get("flow", {}).get("clip_seconds", 8))
    known = chars | set(ep.get("guests", {}))
    clips = {c.get("n"): c for c in ep.get("clips", [])}
    scenes = ep.get("scenes", {})
    voices = ep.get("voices", {})
    for k in ("clips", "edit", "scenes", "voices", "accounts", "hook_text", "title", "description", "tags"):
        if not ep.get(k):
            errors.append(f"{tag}: flow-film needs '{k}'")
    if len(clips) != FF_CLIPS:
        errors.append(f"{tag}: flow-film needs exactly {FF_CLIPS} clips (has {len(clips)})")
    if sorted(clips) != list(range(1, len(clips) + 1)):
        errors.append(f"{tag}: clips must be numbered 1..{len(clips)}")
    fl = bible.get("flow", {})
    per_acct = fl.get("daily_free_credits", 50) // max(fl.get("credits_per_clip", 10), 1)
    assigned = []
    for a, ns in ep.get("accounts", {}).items():
        if len(ns) > per_acct:
            errors.append(f"{tag}: account {a} has {len(ns)} clips, the free credits make {per_acct} a day")
        assigned += ns
    if sorted(assigned) != sorted(clips):
        errors.append(f"{tag}: accounts must cover every clip exactly once")
    for sid, sc in scenes.items():
        if sc.get("loc") not in locs:
            errors.append(f"{tag} scene {sid}: unknown loc '{sc.get('loc')}'")
        if sc.get("out", "cut") not in FF_TRANSITIONS:
            errors.append(f"{tag} scene {sid}: out must be one of {sorted(FF_TRANSITIONS)}")
        amb = clips.get(sc.get("ambience_clip"))
        if amb and amb.get("speaks"):
            warns.append(f"{tag} scene {sid}: ambience_clip {amb['n']} has speech (its Veo voice would leak) -"
                         " room tone is used instead; pick a non-speaking clip")
    for n, c in clips.items():
        ct = f"{tag} clip {n}"
        if c.get("scene") not in scenes:
            errors.append(f"{ct}: unknown scene '{c.get('scene')}'")
        loc = c.get("loc") or scenes.get(c.get("scene"), {}).get("loc")
        if loc not in locs:
            errors.append(f"{ct}: unknown loc '{loc}'")
        for ch in c.get("chars", []):
            if ch not in known:
                errors.append(f"{ct}: unknown character '{ch}'")
        if len(c.get("keyframe", "")) < 40:
            errors.append(f"{ct}: missing or too-short keyframe (the start frame prompt)")
        if len(c.get("flow_prompt", "")) < 80:
            errors.append(f"{ct}: missing or too-short flow_prompt")
        if c.get("speaks") and int(c.get("faces", 0)) != 1:
            errors.append(f"{ct}: speaks: true needs faces: 1 (lip-sync moves the one visible mouth)")
        for fld in ("keyframe", "flow_prompt"):
            m = FF_BANNED.search(c.get(fld, ""))
            if m:
                errors.append(f"{ct}: {fld} mentions '{m.group(0)}' - describe people by look, "
                              "never nationality, ethnicity or accent")
        if re.search(r'"[^"]{6,}"', c.get("flow_prompt", "")):
            warns.append(f"{ct}: flow_prompt quotes dialogue - Flow would speak it; voices are added later")
    used, total = set(), 0.0
    for i, e in enumerate(ep.get("edit", []), 1):
        et = f"{tag} cut {i}"
        c = clips.get(e.get("clip"))
        if not c:
            errors.append(f"{et}: unknown clip {e.get('clip')}")
            continue
        used.add(c["n"])
        a, d = float(e.get("in", 0)), float(e.get("dur", 0))
        total += d + float(e.get("freeze", 0))
        if a < 0 or d <= 0 or a + d > clip_s + 0.01:
            errors.append(f"{et}: in {a} + dur {d} must fit inside the {clip_s:.0f} s clip")
        for kind in ("line", "vo"):
            ln = e.get(kind)
            if not ln:
                continue
            if ln.get("c") not in known:
                errors.append(f"{et}: {kind} by unknown character '{ln.get('c')}'")
            if ln.get("c") not in voices:
                errors.append(f"{et}: '{ln.get('c')}' has no entry in voices")
            room = d - float(ln.get("at", 0)) - 0.1
            nw = words(ln.get("t", ""))
            if room <= 0:
                errors.append(f"{et}: {kind} starts after the cut ends")
            elif nw / room > MAX_WPS_ERROR:
                errors.append(f"{et}: {kind} {nw} words in {room:.1f}s is too fast")
            elif nw / room > MAX_WPS_WARN:
                warns.append(f"{et}: {kind} {nw} words in {room:.1f}s is rushed")
        ln = e.get("line")
        if ln:
            if ln.get("c") not in c.get("chars", []):
                errors.append(f"{et}: speaker '{ln.get('c')}' is not in clip {c['n']} (lip-sync needs their face)")
            if c.get("faces", 1) != 1:
                warns.append(f"{et}: clip {c['n']} shows {c.get('faces')} faces - lip-sync may move the wrong mouth")
            if not 2.0 <= d <= 10.0:
                errors.append(f"{et}: lip-synced cuts must be 2-10 s (is {d})")
    for n in set(clips) - used:
        warns.append(f"{tag} clip {n}: never used in the edit (a wasted Flow credit)")
    return total


def validate_channel(ch_dir):
    errors, warns = [], []
    bible = json.loads((ch_dir / "channel.json").read_text())
    chars, base_locs = set(bible.get("characters", {})), set(bible.get("locations", {}))
    lo, hi = bible["target_seconds"]
    eps = load_episodes(ch_dir)
    seen_ids, loglines = set(), []

    pending_ff = []
    for i, ep in enumerate(eps):
        tag = f"{ep.get('id', '?')} ({ep['_file']})"
        for k in REQUIRED_EP:
            if ep.get("format") == "flow-film" and k in ("shots", "music"):
                continue
            if k not in ep:
                errors.append(f"{tag}: missing field '{k}'")
        if ep.get("id") in seen_ids:
            errors.append(f"{tag}: duplicate id")
        seen_ids.add(ep.get("id"))
        expected_id = f"{bible['episode_id_prefix']}-{ep.get('number', 0):03d}"
        if ep.get("id") != expected_id:
            errors.append(f"{tag}: id should be {expected_id}")
        if ep.get("number") != i + 1:
            errors.append(f"{tag}: episode numbers must be continuous (expected {i + 1})")
        if len(ep.get("title", "")) > 90:
            errors.append(f"{tag}: title over 90 chars")
        if len(ep.get("hook_text", "")) > 45:
            warns.append(f"{tag}: hook_text over 45 chars (hard to read in 2s)")

        guests = set(ep.get("guests", {}))
        locs = base_locs | set(ep.get("locations", {}))
        if ep.get("format") == "flow-film":
            total = validate_flowfilm(ep, tag, bible, chars, locs, errors, warns)
            if total > bible["max_seconds"]:
                errors.append(f"{tag}: {total:.1f}s exceeds {bible['max_seconds']}s")
            elif not lo <= total <= hi:
                warns.append(f"{tag}: {total:.1f}s outside target {lo}-{hi}s")
            ep["_total"] = round(total, 1)
            loglines.append((ep.get("id"), ep.get("logline", "").lower()))
            continue
        if bible.get("episode_format") == "flow-film":
            pending_ff.append(ep.get("id"))
            ep["_total"] = sum(s.get("dur", 0) for s in ep.get("shots", []))
            continue
        narrated = 0
        total = 0
        for s in ep.get("shots", []):
            st = f"{tag} shot {s.get('n')}"
            for k in REQUIRED_SHOT:
                if k not in s:
                    errors.append(f"{st}: missing '{k}'")
            dur = s.get("dur", 0)
            total += dur
            if dur not in ALLOWED_DUR:
                errors.append(f"{st}: dur {dur} not in {sorted(ALLOWED_DUR)}")
            if s.get("loc") not in locs:
                errors.append(f"{st}: unknown loc '{s.get('loc')}'")
            for c in s.get("chars", []):
                if c not in chars and c not in guests:
                    errors.append(f"{st}: unknown character '{c}'")
            spoken = 0
            for ln in s.get("lines", []):
                if ln.get("c") not in chars and ln.get("c") not in guests:
                    errors.append(f"{st}: line by unknown character '{ln.get('c')}'")
                if ln.get("c") not in s.get("chars", []):
                    errors.append(f"{st}: speaker '{ln.get('c')}' not listed in shot chars")
                spoken += words(ln.get("t", ""))
            if bible.get("nonverbal") and s.get("lines"):
                errors.append(f"{st}: channel is nonverbal - put vocal sounds in 'sfx', keep 'lines' empty")
            speakers = {ln.get("c") for ln in s.get("lines", [])}
            if len(speakers) > 2:
                errors.append(f"{st}: {len(speakers)} speakers - max 2 per shot")
            nw = words(s.get("narration", ""))
            if nw:
                narrated += 1
                if dur and nw / dur > MAX_WPS_ERROR:
                    errors.append(f"{st}: narration {nw} words in {dur}s is too fast")
                elif dur and nw / dur > MAX_WPS_WARN:
                    warns.append(f"{st}: narration {nw} words in {dur}s is rushed")
                if s.get("lines"):
                    warns.append(f"{st}: has both narration and dialogue - they will overlap")
            if dur and spoken / dur > MAX_WPS_ERROR:
                errors.append(f"{st}: {spoken} words in {dur}s is too fast")
            elif dur and spoken / dur > MAX_WPS_WARN:
                warns.append(f"{st}: {spoken} words in {dur}s is rushed")
        if bible.get("narrator") and narrated < len(ep.get("shots", [])) - 1:
            errors.append(f"{tag}: narrated channel - every shot (except at most one) needs 'narration'")
        if bible.get("source") == "flow":
            for s in ep.get("shots", []):
                if s.get("dur") != 8:
                    errors.append(f"{tag} shot {s.get('n')}: Google Flow clips are 8 s - dur must be 8")
                if len(s.get("flow_prompt", "")) < 80:
                    errors.append(f"{tag} shot {s.get('n')}: missing or too-short flow_prompt")
                for ln in s.get("lines", []):
                    if ln.get("t", "") not in s.get("flow_prompt", ""):
                        errors.append(f"{tag} shot {s.get('n')}: spoken line not inside flow_prompt (captions would not match)")
            fl = bible.get("flow", {})
            per_acct = fl.get("daily_free_credits", 50) // max(fl.get("credits_per_clip", 10), 1)
            max_clips = per_acct * max(len(fl.get("accounts", [])), 1)
            if len(ep.get("shots", [])) > max_clips:
                errors.append(f"{tag}: {len(ep['shots'])} clips but channel.json flow.accounts only allows {max_clips} a day")
        if total > bible["max_seconds"]:
            errors.append(f"{tag}: {total}s exceeds {bible['max_seconds']}s")
        elif not lo <= total <= hi:
            warns.append(f"{tag}: {total}s outside target {lo}-{hi}s")
        ep["_total"] = total

        ll = ep.get("logline", "").lower()
        for other_id, other in loglines:
            if difflib.SequenceMatcher(None, ll, other).ratio() > 0.75:
                warns.append(f"{tag}: logline very similar to {other_id} - make it more unique")
        loglines.append((ep.get("id"), ll))

    if pending_ff:
        warns.append(f"{len(pending_ff)} episodes not converted to flow-film yet ({pending_ff[0]}..{pending_ff[-1]}):"
                     " flow-import waits at the first one until it is converted")
    return eps, errors, warns


def validate_carousel(ch_dir):
    """channels/<ch>/carousel.json: the second daily video (image carousel + scrolling words)."""
    import string
    errors, warns = [], []
    p = ch_dir / "carousel.json"
    if not p.exists():
        return errors, warns
    c = json.loads(p.read_text())
    tpl = c["image_prompt"]["template"]
    keys = {f for _, f, _, _ in string.Formatter().parse(tpl) if f}
    missing = keys - set(c["image_prompt"]["pools"])
    if missing:
        errors.append(f"carousel image template uses unknown pools: {sorted(missing)}")
    for k in c["image_prompt"].get("unique_per_video", []):
        if len(c["image_prompt"]["pools"].get(k, [])) < c.get("images_per_video", 8):
            warns.append(f"carousel pool '{k}' has fewer options than images per video")
    seen = set()
    for i, ep in enumerate(c["episodes"]):
        tag = f"carousel #{i + 1} ({ep.get('theme')})"
        if not 6 <= len(ep.get("lines", [])) <= 10:
            errors.append(f"{tag}: needs 6-10 lines")
        for ln in ep.get("lines", []):
            if words(ln) > 16:
                warns.append(f"{tag}: line over 16 words: {ln[:40]}")
            if ln in seen:
                errors.append(f"{tag}: duplicate line: {ln[:50]}")
            seen.add(ln)
        if len(ep.get("hook", "")) > 60:
            warns.append(f"{tag}: hook over 60 chars")
    return errors, warns


def validate_extras(ch_dir):
    """channels/<ch>/extras.json: short daily extra formats (pipeline/extras.py)."""
    errors, warns = [], []
    p = ch_dir / "extras.json"
    if not p.exists():
        return errors, warns
    c = json.loads(p.read_text())
    known = set()
    cp = ch_dir / "carousel.json"
    if cp.exists():
        known = {ln for e in json.loads(cp.read_text())["episodes"] for ln in e["lines"]}
    need = {"finish": ("theme", "start", "end"), "thennow": ("theme", "topic", "then_img", "now_img", "pairs", "lesson"),
            "babymean": ("theme", "topic", "pairs")}
    for name in c.get("priority", []):
        if name not in c["formats"]:
            errors.append(f"extras priority names unknown format {name}")
    for name, fmt in c["formats"].items():
        if name not in need:
            errors.append(f"extras: unknown format {name} (pipeline/extras.py MAKERS)")
            continue
        seen = set()
        for i, ep in enumerate(fmt["episodes"]):
            tag = f"extras {name} #{i + 1}"
            for k in need[name]:
                if not ep.get(k):
                    errors.append(f"{tag}: missing {k}")
            texts = []
            if name == "finish":
                texts = [f"{ep.get('start', '')} {ep.get('end', '')}"]
            elif ep.get("pairs"):
                if len(ep["pairs"]) != 3:
                    errors.append(f"{tag}: needs exactly 3 pairs")
                texts = [" ".join(pr) for pr in ep["pairs"]] + ([ep["lesson"]] if ep.get("lesson") else [])
            for t in texts:
                if words(t) > 18:
                    warns.append(f"{tag}: over 18 words: {t[:50]}")
                if t in seen or t in known:
                    errors.append(f"{tag}: repeats an earlier line: {t[:50]}")
                seen.add(t)
            try:
                fmt["title_template"].format(**ep)
            except KeyError as e:
                errors.append(f"{tag}: title_template needs {e}")
    return errors, warns


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    bad = False
    for ch_dir in sorted((ROOT / "channels").iterdir()):
        if only and ch_dir.name != only:
            continue
        eps, errors, warns = validate_channel(ch_dir)
        durs = [e["_total"] for e in eps]
        print(f"\n== {ch_dir.name}: {len(eps)} episodes", end="")
        if durs:
            print(f", {min(durs)}-{max(durs)}s (avg {sum(durs) / len(durs):.0f}s)")
        else:
            print()
        ce, cw = validate_carousel(ch_dir)
        errors += ce
        warns += cw
        ce, cw = validate_extras(ch_dir)
        errors += ce
        warns += cw
        for w in warns:
            print("  WARN ", w)
        for e in errors:
            print("  ERROR", e)
        bad |= bool(errors)
    print("\nRESULT:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
