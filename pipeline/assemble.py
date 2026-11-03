"""ffmpeg assembly: normalise clips -> concat -> hook text + captions -> music bed -> loudness -> final.mp4"""
import json
import re
import subprocess
from pathlib import Path

from . import config

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


def normalise(src: Path, dest: Path, seconds: int):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration=3,format=yuv420p")
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


def build_ass(episode: dict, dest: Path, hook: bool = True, captions: bool = True):
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

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 1,{_ts(0)},{_ts(2.6)},Hook,,0,0,0,,{_clean(episode['hook_text'])}"] if hook else []
    t0 = 0.0
    for shot in episode["shots"]:
        lines = shot.get("lines", []) if captions else []
        words = [max(len(l["t"].split()), 1) for l in lines]
        usable = shot["dur"] - 0.6
        t = t0 + 0.3
        for ln, wc in zip(lines, words):
            span = usable * wc / sum(words)
            events.append(f"Dialogue: 0,{_ts(t)},{_ts(t + span)},Line,,0,0,0,,{_clean(ln['t'])}")
            t += span
        t0 += shot["dur"]
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


def assemble(episode: dict, clips: list, workdir: Path, bible: dict | None = None) -> Path:
    ov = (bible or {}).get("overlays", {})
    show_hook, show_caps = ov.get("hook", True), ov.get("captions", True)
    norm = []
    for shot, c in zip(episode["shots"], clips):
        n = workdir / f"norm{shot['n']:02d}.mp4"
        normalise(c, n, shot["dur"])
        norm.append(n)
    (workdir / "concat.txt").write_text("".join(f"file '{p.name}'\n" for p in norm))
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "concat.txt",
          "-c", "copy", "base.mp4"], cwd=workdir)
    build_ass(episode, workdir / "captions.ass", hook=show_hook, captions=show_caps)
    build_ass(episode, workdir / "captions_clean.ass", hook=False, captions=show_caps)

    total = sum(s["dur"] for s in episode["shots"])
    music = find_music(episode.get("music", ""))
    loud = f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11"
    # final.mp4 = the Short (with hook text); clean.mp4 = same without hook, used for long compilations
    for ass, out in (("captions.ass", "final.mp4"), ("captions_clean.ass", "clean.mp4")):
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", "base.mp4"]
        has_text = "Dialogue:" in (workdir / ass).read_text(encoding="utf-8")
        vf = f"[0:v]subtitles={ass}[v]" if has_text else "[0:v]null[v]"
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
            af = (f"[1:a]volume={config.MUSIC_VOLUME},afade=t=out:st={total - 1.5}:d=1.5[m];"
                  f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,{loud}[a]")
        else:
            af = f"[0:a]{loud}[a]"
        cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", str(total),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out]
        _run(cmd, cwd=workdir)

    meta = {
        "title": episode["title"][:100],
        "description": f"{episode['description']}\n\n{config.AI_DISCLOSURE}\n\n"
                       + " ".join("#" + re.sub(r"\W", "", t) for t in episode["tags"][:4]) + " #shorts",
        "made_for_kids": bool((bible or {}).get("made_for_kids", False)),
        "tags": episode["tags"][:15],
        "music": str(music.name) if music else None,
        "seconds": total,
    }
    (workdir / "metadata.json").write_text(json.dumps(meta, indent=2))
    for n in norm:
        n.unlink(missing_ok=True)
    (workdir / "base.mp4").unlink(missing_ok=True)
    return workdir / "final.mp4"
