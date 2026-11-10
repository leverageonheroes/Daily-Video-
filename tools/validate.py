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


def validate_channel(ch_dir):
    errors, warns = [], []
    bible = json.loads((ch_dir / "channel.json").read_text())
    chars, base_locs = set(bible.get("characters", {})), set(bible.get("locations", {}))
    lo, hi = bible["target_seconds"]
    eps = load_episodes(ch_dir)
    seen_ids, loglines = set(), []

    for i, ep in enumerate(eps):
        tag = f"{ep.get('id', '?')} ({ep['_file']})"
        for k in REQUIRED_EP:
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
        for w in warns:
            print("  WARN ", w)
        for e in errors:
            print("  ERROR", e)
        bad |= bool(errors)
    print("\nRESULT:", "FAILED" if bad else "OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
