"""Stitch episodes into one long-form video (16:9 with blurred background), with YouTube chapters.

Two independent schedules, each with its own tracker in state.json, so they never block each other:
  weekly  -> tracker `last_compiled_weekly`; runs every Sunday but only compiles a channel once its new
             episodes add up to WEEKLY_MIN_SECONDS (default 510 s = 8.5 min, so mid-roll ads are allowed)
  monthly -> tracker `last_compiled`; 1st of the month, every episode since the previous monthly one
Turn either off per channel in channel.json: "compilations": {"weekly": false, "monthly": true}
"""
import json
import os
from pathlib import Path

from . import assemble, config, state, storage
from .generate import load_bible

LW, LH, LFPS = 1920, 1080, 30
DONE = ("uploaded", "published")
TRACKER = {"weekly": "last_compiled_weekly", "monthly": "last_compiled", "range": None, "arc": None}
WEEKLY_MIN_SECONDS = int(os.environ.get("WEEKLY_MIN_SECONDS", "510"))
MONTHLY_MIN_EPISODES = 3


def enabled(channel: str, kind: str) -> bool:
    return load_bible(channel).get("compilations", {}).get(kind, True)


def ep_seconds(e) -> int:
    return sum(s["dur"] for s in e["shots"])


def pick_episodes(s, channel, kind, first=None, last=None):
    eps = state.episodes(channel)
    recs = s["channels"][channel]["episodes"]
    if kind == "range":
        return [e for e in eps if first <= e["number"] <= last
                and recs[e["id"]]["status"] in ("rendered",) + DONE]
    after = s["channels"][channel].get(TRACKER[kind], 0)
    return [e for e in eps if e["number"] > after and recs[e["id"]]["status"] in DONE]


def _ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def widescreen(src: Path, dest: Path):
    """Vertical episode centred on a 16:9 frame, background = blurred zoomed copy of itself."""
    fc = (f"[0:v]split[a][b];"
          f"[a]scale=480:270:force_original_aspect_ratio=increase,crop=480:270,boxblur=12:2,"
          f"eq=brightness=-0.12,scale={LW}:{LH}[bg];"
          f"[b]scale=-2:{LH}[fg];[bg][fg]overlay=(W-w)/2:0,fps={LFPS},format=yuv420p[v]")
    assemble._run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", fc,
                   "-map", "[v]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest)])


def ready(s, channel, kind) -> bool:
    """Is there enough new material for this kind of compilation?"""
    eps = pick_episodes(s, channel, kind)
    if kind == "weekly":
        secs = sum(ep_seconds(e) for e in eps)
        if secs < WEEKLY_MIN_SECONDS:
            print(f"   {channel}: {len(eps)} new episodes = {secs // 60}m{secs % 60:02d}s, "
                  f"waiting for {WEEKLY_MIN_SECONDS // 60}m{WEEKLY_MIN_SECONDS % 60:02d}s (mid-roll ads need 8+ min).")
            return False
        return True
    if len(eps) < MONTHLY_MIN_EPISODES:
        print(f"   {channel}: only {len(eps)} new episodes this month, need {MONTHLY_MIN_EPISODES}.")
        return False
    return True


def compile_channel(s, channel, kind="monthly", first=None, last=None):
    if kind != "range" and not ready(s, channel, kind):
        return None
    eps = pick_episodes(s, channel, kind, first, last)
    if not eps:
        print(f"   {channel}: nothing to compile.")
        return None
    bible = load_bible(channel)
    a0, b0 = eps[0]["number"], eps[-1]["number"]
    name = f"{channel}_{kind}_ep{a0:03d}-{b0:03d}"
    wd = config.OUTPUT / channel / "compilations" / name
    wd.mkdir(parents=True, exist_ok=True)
    print(f"\n== {kind.title()} compilation: {bible['show_title']} episodes {a0}-{b0} ({len(eps)} videos)")

    parts, chapters, t, used = [], [], 0.0, []
    for e in eps:
        try:
            src = storage.fetch_episode(channel, e["id"], wd / "src" / f"{e['id']}.mp4")
        except FileNotFoundError as err:
            print(f"   skipping {e['id']}: {err}")
            continue
        used.append(e)
        part = wd / f"part_{e['number']:03d}.mp4"
        if not part.exists():
            widescreen(src, part)
        parts.append(part)
        title = assemble._clean(e["title"]).replace("#shorts", "").strip()
        chapters.append(f"{_ts(t)} Ep {e['number']} - {title}")
        t += assemble.duration(part)

    if len(used) < 2:
        print(f"   {channel}: only {len(used)} episode files available. Skipping.")
        return None
    a, b = used[0]["number"], used[-1]["number"]
    (wd / "concat.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    out = wd / f"{name}.mp4"
    assemble._run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "concat.txt",
                   "-c", "copy", "-movflags", "+faststart", out.name], cwd=wd)
    for p in parts:
        p.unlink(missing_ok=True)

    if kind == "monthly" and a == 1 and b >= 30:
        label = "Season 1"
    elif kind == "monthly":
        label = f"Monthly Marathon (Ep {a}-{b})"
    else:
        label = f"Episodes {a}-{b}"
    tpl = bible.get("compilation_title", "{show} | {label} - {n} Episodes")
    title = tpl.format(show=bible["show_title"], label=label, n=len(used), a=a, b=b)
    if kind == "weekly" and "{label}" not in tpl:
        title = f"{title} (Ep {a}-{b})"
    meta = {
        "title": title[:100],
        "description": (f"{bible['tagline']}\n\nEpisodes {a} to {b} back to back.\n\nChapters:\n"
                        + "\n".join(chapters)
                        + f"\n\nNew episodes daily on this channel's Shorts.\n\n{config.AI_DISCLOSURE}"),
        "tags": list({*bible.get("compilation_tags", []), bible["show_title"].lower(), "animation",
                      "compilation", "full episodes"})[:15],
        "seconds": round(t),
        "made_for_kids": bool(bible.get("made_for_kids", False)),
    }
    (wd / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"   -> {out} ({_ts(t)})  title: {meta['title']}")
    return out, meta, b, used


def finish(s, channel, kind, out, meta, last_number, eps, upload=True):
    rec = {"kind": kind, "file": str(out.relative_to(config.ROOT)), "episodes": [e["id"] for e in eps],
           "at": state.now(), "seconds": meta["seconds"], "title": meta["title"]}
    if upload:
        from . import youtube
        res = youtube.upload(channel, out, meta)
        rec.update(res)
        print(f"   uploaded https://youtu.be/{res['youtube_id']}")
    ch = s["channels"][channel]
    ch.setdefault("compilations", []).append(rec)
    if TRACKER.get(kind):
        ch[TRACKER[kind]] = max(ch.get(TRACKER[kind], 0), last_number)
    state.save(s)


# ---------------- story arcs: the full movie after each finale ----------------
def _card(text_top, text_main, dest: Path, seconds: float, accent="#e8b04a"):
    """Simple cinematic 1920x1080 title / moral card (Pillow image -> short video with silence)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (LW, LH), (8, 8, 10))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 44)
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 86)
    acc = tuple(int(accent.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    words, lines, cur = text_main.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f2) <= LW - 300:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    h = 70 + len(lines) * 104
    y = (LH - h) / 2
    d.text(((LW - d.textlength(text_top, font=f1)) / 2, y), text_top, font=f1, fill=acc)
    y += 90
    for ln in lines:
        d.text(((LW - d.textlength(ln, font=f2)) / 2, y), ln, font=f2, fill=(245, 240, 230))
        y += 104
    png = dest.with_suffix(".png")
    im.save(png)
    assemble._run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(LFPS), "-i", str(png),
                   "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.2f}",
                   "-vf", f"fade=t=in:st=0:d=0.8,fade=t=out:st={seconds - 0.8:.2f}:d=0.8,format=yuv420p",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(LFPS),
                   "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest)])
    return dest


def compile_arc(s, channel, finale: dict, upload=True):
    """Glue every part of the finished arc into one long movie (16:9, chapters, title + moral cards).
    6 parts x ~80 s + cards > 8 minutes, so YouTube allows mid-roll ads."""
    bible = load_bible(channel)
    arc = finale["arc"]
    parts_eps = sorted((e for e in state.episodes(channel) if e.get("arc") == arc), key=lambda e: e["part"])
    title = finale.get("arc_title", arc)
    name = f"{channel}_movie_{arc}"
    wd = config.OUTPUT / channel / "compilations" / name
    wd.mkdir(parents=True, exist_ok=True)
    print(f"\n== Arc movie: {title} ({len(parts_eps)} parts)")
    segs = [_card(bible["show_title"].upper(), title, wd / "card_title.mp4", 5.0)]
    chapters, t = [f"{_ts(0)} {title}"], 5.0
    for e in parts_eps:
        src = storage.fetch_episode(channel, e["id"], wd / "src" / f"{e['id']}.mp4")
        part = wd / f"part_{e['part']:02d}.mp4"
        if not part.exists():
            widescreen(src, part)
        segs.append(part)
        chapters.append(f"{_ts(t)} Part {e['part']} - {e.get('part_title', '')}".rstrip(" -"))
        t += assemble.duration(part)
    if finale.get("moral"):
        segs.append(_card("THE MORAL OF THE STORY", finale["moral"], wd / "card_moral.mp4", 7.0))
        chapters.append(f"{_ts(t)} The moral of the story")
        t += 7.0
    (wd / "concat.txt").write_text("".join(f"file '{p.name}'\n" for p in segs))
    out = wd / f"{name}.mp4"
    assemble._run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "concat.txt",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "192k",
                   "-movflags", "+faststart", out.name], cwd=wd)
    rec = s["channels"][channel]["episodes"].get(finale["id"], {})
    publish_at = None
    if rec.get("publish_at"):
        import datetime as dt
        when = dt.datetime.fromisoformat(rec["publish_at"].replace("Z", "+00:00")) + dt.timedelta(hours=24)
        publish_at = when.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
    meta = {
        "title": bible.get("movie_title", "{arc} | Full Movie | {show}").format(arc=title, show=bible["show_title"])[:100],
        "description": (f"{finale.get('arc_logline', '')}\n\nThe complete story, all {len(parts_eps)} parts in one movie."
                        f"\n\nChapters:\n" + "\n".join(chapters)
                        + (f"\n\nThe moral of the story: {finale['moral']}" if finale.get("moral") else "")
                        + f"\n\n{bible.get('ai_disclosure', config.AI_DISCLOSURE)}"),
        "tags": list(dict.fromkeys(bible.get("compilation_tags", []) + [title.lower(), "full movie"]))[:15],
        "seconds": round(t), "made_for_kids": bool(bible.get("made_for_kids", False)),
    }
    if publish_at:
        meta["publish_at"] = publish_at
    (wd / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"   -> {out} ({_ts(t)})")
    finish(s, channel, "arc", out, meta, finale["number"], parts_eps, upload=upload)
    return out
