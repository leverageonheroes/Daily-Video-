"""ffmpeg assembly: normalise clips -> concat -> hook text + captions -> music bed -> loudness -> final.mp4"""
import json
import re
import subprocess
from pathlib import Path

from . import config, seo

W, H, FPS = config.OUT_W, config.OUT_H, config.OUT_FPS


def _run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}")
    return r


def has_audio(path: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


FADE = 0.35   # seconds of dip/flash at a scene change


def normalise(src: Path, dest: Path, seconds: int, fade_in: str = "", fade_out: str = "", freeze: float = 0.0):
    """fade_in / fade_out: "dip" (through black) or "flash" (through white) for scene changes.
    freeze: hold the frame at (seconds - freeze) for the last `freeze` seconds, desaturated (cliffhanger)."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
    if freeze:
        vf += f",trim=0:{seconds - freeze:.2f},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={freeze + 1:.2f}"
        vf += f",eq=saturation='if(gte(t,{seconds - freeze:.2f}),0.25,1)':eval=frame"
    else:
        vf += ",tpad=stop_mode=clone:stop_duration=3"
    col = {"dip": "black", "flash": "white"}
    if fade_in in col:
        vf += f",fade=t=in:st=0:d={FADE}:color={col[fade_in]}"
    if fade_out in col:
        vf += f",fade=t=out:st={seconds - FADE:.2f}:d={FADE}:color={col[fade_out]}"
    vf += ",format=yuv420p"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    if has_audio(src):
        amap = "0:a:0"
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        amap = "1:a:0"
    cmd += ["-map", "0:v:0", "-map", amap, "-vf", vf, "-af", "aresample=48000,apad",
            "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(dest)]
    _run(cmd)


# ---------------- captions (ASS) ----------------

def _ts(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍←-⇿⬀-⯿]")


def _clean(text: str) -> str:
    """Strip characters libass can't draw with a normal font (emoji) and ASS control characters."""
    text = EMOJI.sub("", text)
    return re.sub(r"\s+", " ", re.sub(r"[{}\\]", "", text)).strip()


def _chunks(text: str, max_words: int = 7):
    """Split narration into short caption phrases (sentence / comma boundaries, max ~7 words)."""
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        cur = []
        for w in sent.split():
            cur.append(w)
            if len(cur) >= max_words or (w.endswith(",") and len(cur) >= 3):
                out.append(" ".join(cur))
                cur = []
        if cur:
            if out and len(cur) <= 2 and not out[-1].endswith((".", "!", "?")):
                out[-1] += " " + " ".join(cur)
            else:
                out.append(" ".join(cur))
    return out


def build_ass(episode: dict, dest: Path, hook: bool = True, captions: bool = True,
              offset: float = 0.0, card: str = "", end_text: str = "", end_at: float = 0.0,
              part_label: str = "", moral: str = "", card_over_lead: bool = False):
    """offset = seconds of cold open before the story starts (captions shift by it).
    end_text is shown for the 1.9 s before end_at (the end of the story)."""
    font = config.CAPTION_FONT
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,{font},74,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB0000000,1,0,0,0,100,100,0,0,3,18,0,8,70,70,230,1
Style: Line,{font},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,6,2,2,90,90,520,1
Style: Card,{font},82,&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,1,1,0,0,100,100,4,0,3,22,0,5,80,80,0,1
Style: End,{font},64,&H0000D7FF,&H00FFFFFF,&H00000000,&HA0000000,1,0,0,0,100,100,2,0,3,18,0,2,70,70,140,1
Style: Part,{font},46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,6,0,3,14,0,8,70,70,230,1
Style: Moral,{font},70,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC8000000,1,0,0,0,100,100,1,0,3,40,0,5,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 1,{_ts(0)},{_ts(2.6)},Hook,,0,0,0,,{_clean(episode['hook_text'])}"] if hook else []
    if part_label:
        events.append(f"Dialogue: 1,{_ts(2.8)},{_ts(5.6)},Part,,0,0,0,,{{\\fad(200,300)}}{_clean(part_label)}")
    if card and card_over_lead:      # recap: label sits on the recap itself
        events.append(f"Dialogue: 2,{_ts(0.1)},{_ts(max(offset - 0.15, 0.5))},Card,,0,0,0,,{{\\fad(150,150)}}{_clean(card)}")
    elif card:
        events.append(f"Dialogue: 2,{_ts(offset + 0.05)},{_ts(offset + 1.7)},Card,,0,0,0,,{{\\fad(150,250)}}{_clean(card)}")
    t0 = offset
    for shot in episode["shots"]:
        if captions:
            if shot.get("narration"):
                parts = _chunks(shot["narration"])
                nw = [max(len(p.split()), 1) for p in parts]
                speech = min(shot["dur"] - 0.35, sum(nw) / 2.5 + 0.2)   # narrator speaks ~2.5 words/s
                t = t0 + 0.1
                for p, w in zip(parts, nw):
                    span = speech * w / sum(nw)
                    events.append(f"Dialogue: 0,{_ts(t)},{_ts(t + span)},Line,,0,0,0,,{_clean(p)}")
                    t += span
            lines = shot.get("lines", [])
            words = [max(len(l["t"].split()), 1) for l in lines]
            usable = shot["dur"] - 0.6
            t = t0 + 0.3
            for ln, wc in zip(lines, words):
                span = usable * wc / sum(words)
                events.append(f"Dialogue: 0,{_ts(t)},{_ts(t + span)},Line,,0,0,0,,{_clean(ln['t'])}")
                t += span
        t0 += shot["dur"]
    if moral and end_at:
        events.append(f"Dialogue: 3,{_ts(end_at - 7.0)},{_ts(end_at)},Moral,,0,0,0,,{{\\fad(500,0)}}"
                      f"THE MORAL OF THE STORY\\N\\N{_clean(moral)}")
        end_text = ""
    if end_text and end_at:
        events.append(f"Dialogue: 2,{_ts(end_at - 1.9)},{_ts(end_at)},End,,0,0,0,,{{\\fad(200,0)}}"
                      f"{_clean(end_text).replace('|', chr(92) + 'N')}")
    dest.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return dest


def find_music(mood: str):
    slug = re.sub(r"[^a-z0-9]+", "-", mood.lower()).strip("-")
    for name in (slug, "default"):
        for ext in ("mp3", "m4a", "wav", "ogg"):
            p = config.MUSIC / f"{name}.{ext}"
            if p.exists():
                return p
    return None


def end_card(bible: dict | None, workdir: Path):
    """Render channel.json `end_card` (a still PNG) as a short clip with a fade-in, or None if not configured."""
    cfg = (bible or {}).get("end_card") or {}
    if not isinstance(cfg, dict):          # a text end card (e.g. "TO BE CONTINUED...") is drawn in captions
        return None, 0
    img = config.ROOT / cfg.get("image", "")
    if not cfg.get("enabled") or not cfg.get("image") or not img.is_file():
        return None, 0
    sec = float(cfg.get("seconds", 4))
    out = workdir / "endcard.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(img.resolve()),
          "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
          "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                 f"fade=t=in:st=0:d=0.5,format=yuv420p",
          "-t", str(sec), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", str(FPS),
          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(out)])
    return out, sec


CARDS = ["EARLIER THAT DAY...", "12 HOURS EARLIER...", "THAT MORNING...", "ONE HOUR EARLIER..."]


def cold_open_spec(episode: dict, bible: dict):
    """Flash-forward teaser: a few seconds of a later shot (default: the last) before the story starts.
    channel.json "cold_open": {"seconds": 3.5, "cards": [...]}; an episode can override with
    "cold_open": {"shot": 7, "start": 0.5, "seconds": 3, "card": "..."} or false to switch it off."""
    base = bible.get("cold_open")
    ep = episode.get("cold_open", {})
    if not base or ep is False:
        return None
    shots = episode["shots"]
    n = ep.get("shot", shots[-1]["n"])
    idx = next(i for i, sh in enumerate(shots) if sh["n"] == n)
    secs = float(ep.get("seconds", base.get("seconds", 3.5)))
    start = float(ep.get("start", base.get("start", 0.0)))
    secs = min(secs, shots[idx]["dur"] - start)
    cards = base.get("cards", CARDS)
    card = ep.get("card", cards[(episode.get("number", 1) - 1) % len(cards)])
    return {"idx": idx, "start": start, "seconds": secs, "card": card}


def _cold_open(src: Path, dest: Path, start: float, secs: float):
    vf = (f"eq=saturation=0.7:contrast=1.12,vignette=PI/4,"
          f"fade=t=out:st={secs - 0.18:.2f}:d=0.18:color=white,format=yuv420p")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(src), "-t", f"{secs:.2f}",
          "-vf", vf, "-af", f"afade=t=out:st={max(secs - 0.6, 0):.2f}:d=0.6",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", str(FPS),
          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(dest)])


def _narration_track(episode: dict, narration: list, workdir: Path) -> Path:
    """One story-length track: each shot's narration placed at that shot's start."""
    total = sum(s["dur"] for s in episode["shots"])
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    t0 = 0.0
    for shot, a in zip(episode["shots"], narration):
        if a:
            k = len(inputs) // 2
            inputs += ["-i", str(a)]
            ms = int(t0 * 1000)
            filters.append(f"[{k}:a]adelay={ms}|{ms}[n{k}]")
            labels.append(f"[n{k}]")
        t0 += shot["dur"]
    dest = workdir / "narration.wav"
    fc = ";".join(filters) + f";{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,apad[a]"
    _run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[a]",
          "-t", str(total), "-ar", "48000", "-ac", "2", str(dest)])
    return dest


def _render(video: Path, ass: str, out: str, total: float, workdir: Path, music, narr, narr_delay: float,
            bed: float, grade: str = ""):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video)]
    has_text = "Dialogue:" in (workdir / ass).read_text(encoding="utf-8")
    pre = f"{grade}," if grade else ""          # cinematic grade / grain / vignette under the captions
    vf = f"[0:v]{pre}subtitles={ass}[v]" if has_text else f"[0:v]{pre}null[v]"
    loud = f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11"
    chains, mix = [f"[0:a]volume={bed}[b]"], ["[b]"]
    k = 1
    if narr:
        cmd += ["-i", str(narr)]
        ms = int(narr_delay * 1000)
        chains.append(f"[{k}:a]adelay={ms}|{ms},apad[n]")
        mix.append("[n]")
        k += 1
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
        chains.append(f"[{k}:a]volume={config.MUSIC_VOLUME},afade=t=out:st={max(total - 1.5, 0)}:d=1.5[m]")
        mix.append("[m]")
    af = ";".join(chains) + f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0,{loud}[a]"
    cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
    _run(cmd, cwd=workdir)


def _concat(workdir: Path, parts: list, out: str):
    (workdir / f"{out}.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{out}.txt",
          "-c", "copy", out], cwd=workdir)
    (workdir / f"{out}.txt").unlink(missing_ok=True)


def assemble(episode: dict, clips: list, workdir: Path, bible: dict | None = None,
             narration: list | None = None, recap: dict | None = None) -> Path:
    """recap = {"src": Path, "start": s, "seconds": n}: a flash of the previous episode before the story."""
    bible = bible or {}
    ov = bible.get("overlays", {})
    show_hook, show_caps = ov.get("hook", True), ov.get("captions", True)
    norm = []
    shots = episode["shots"]
    for i, (shot, c) in enumerate(zip(shots, clips)):
        n = workdir / f"norm{shot['n']:02d}.mp4"
        nxt = shots[i + 1].get("transition", "cut") if i + 1 < len(shots) else ""
        normalise(c, n, shot["dur"], fade_in=shot.get("transition", "cut") if i else "",
                  fade_out=nxt, freeze=float(shot.get("freeze", 0)))
        norm.append(n)
    _concat(workdir, [p.name for p in norm], "base.mp4")
    story = sum(s["dur"] for s in episode["shots"])

    # final.mp4 = [flash-forward cold open] + story + [image end card]; clean.mp4 (compilations) = story only
    co = cold_open_spec(episode, bible)
    lead, parts = 0.0, ["base.mp4"]
    has_recap = bool(recap and Path(recap["src"]).exists())
    if has_recap:
        co = {"card": bible.get("recap_card", "PREVIOUSLY...")}
        _cold_open(Path(recap["src"]), workdir / "cold.mp4", recap["start"], recap["seconds"])
        lead = duration(workdir / "cold.mp4")
        parts.insert(0, "cold.mp4")
    elif co:
        _cold_open(norm[co["idx"]], workdir / "cold.mp4", co["start"], co["seconds"])
        lead = duration(workdir / "cold.mp4")
        parts.insert(0, "cold.mp4")
    card, card_sec = end_card(bible, workdir)
    if card:
        parts.append("endcard.mp4")
    src = "base.mp4"
    if len(parts) > 1:
        _concat(workdir, parts, "full.mp4")
        src = "full.mp4"
    total = lead + story + card_sec
    ec = episode.get("end_card", bible.get("end_card"))   # a string, or an image-card dict whose optional "text" shows over the last story beat
    end_text = ec if isinstance(ec, str) else (ec or {}).get("text", "")
    build_ass(episode, workdir / "captions.ass", hook=show_hook, captions=show_caps, offset=lead,
              card=co["card"] if co else "", end_text=end_text, end_at=lead + story,
              part_label=episode.get("part_label", ""), moral=episode.get("moral", ""),
              card_over_lead=has_recap)
    build_ass(episode, workdir / "captions_clean.ass", hook=False, captions=show_caps)

    narr = _narration_track(episode, narration, workdir) if narration and any(narration) else None
    bed = float(bible.get("clip_audio_volume", 0.45 if narr else 1.0))
    music = find_music(episode.get("music", ""))
    grade = bible.get("cinema_vf", "")
    _render(workdir / src, "captions.ass", "final.mp4", total, workdir, music, narr, lead, bed, grade)
    _render(workdir / "base.mp4", "captions_clean.ass", "clean.mp4", story, workdir, music, narr, 0.0, bed, grade)

    meta = {
        "title": episode["title"][:100],
        "description": "\n\n".join(x for x in (episode["description"], seo.about(bible),
                                                bible.get("ai_disclosure", config.AI_DISCLOSURE),
                                                seo.hashtag_line(bible, episode["tags"])) if x),
        "made_for_kids": bool(bible.get("made_for_kids", False)),
        "tags": seo.youtube_tags(bible, episode["tags"]),
        "music": str(music.name) if music else None,
        "social": episode.get("captions", {}),     # per-platform captions (TikTok / Facebook) to paste
        "seconds": round(total, 2),
    }
    (workdir / "metadata.json").write_text(json.dumps(meta, indent=2))
    for f in norm + [workdir / t for t in ("base.mp4", "full.mp4", "cold.mp4", "endcard.mp4")]:
        f.unlink(missing_ok=True)
    return workdir / "final.mp4"
