"""Hard Truths (Ask The Elders TV): one AI elder speaks 8 lines to camera, lip-synced, ~66 s. All free tools.

  python -m pipeline.run hardtruths [elders]

  1. portrait   free FLUX still (pipeline/images.py), extreme close-up, composed to 1080x1920
  2. voice      Kokoro TTS (Apache-2.0, ONNX, runs on the CPU runner), one clip per line, slightly lowered pitch
  3. lip-sync   SadTalker (Apache-2.0) in its own Python 3.10 venv (tools/setup_sadtalker.sh), one pass over the
                whole voice track, GFPGAN face enhancer. LIPSYNC=still renders without lip-sync (tests only).
  4. finish     slow push-in, grey-green grade, captions popping in word by word (power words from the
                word bank in gold), "HARD TRUTH #n" label, soft piano under the voice, -14 LUFS.

Content: channels/elders/hardtruths.json (tools/generators/build_hardtruths.py). Progress: state/hardtruths.json.
While hardtruths.json has "paused": true, each new episode is rendered ONCE and kept in GitHub Release
`hardtruths-preview` for review (no YouTube upload). Set it to false to start daily uploads.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import assemble, config, images, seo

W, H, FPS = 1080, 1920, 30
STATE = config.ROOT / "state" / ("hardtruths.mock.json" if config.MOCK else "hardtruths.json")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
LEAD = 0.35            # silence before each line inside its segment
CTA_GAP = 0.45         # pause between the closer and the spoken question
END_HOLD = 1.6         # silence after the question
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


# ---------------------------------------------------------------- content / state
def load_cfg(ch="elders"):
    return json.loads((config.CHANNELS_DIR / ch / "hardtruths.json").read_text())


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"channels": {}}


def save_state(s):
    s["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2) + "\n")


def power_words(cfg) -> set:
    return {w.lower() for ws in cfg.get("word_bank", {}).values() for w in ws}


def is_power(word, bank) -> bool:
    w = re.sub(r"[^a-z']", "", word.lower()).strip("'")
    return w in bank or w.rstrip("s") in bank


# ---------------------------------------------------------------- voice (Kokoro, free, local)
_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
         "sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _num(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    return str(n)


def speakable(text: str) -> str:
    return re.sub(r"\b\d{1,2}\b", lambda m: _num(int(m.group())), text)


_KOKORO = None


def _kokoro():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro
        d = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))
        d.mkdir(parents=True, exist_ok=True)
        for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            if not (d / f).exists():
                print(f"   downloading Kokoro {f}")
                urllib.request.urlretrieve(KOKORO_URL + f, d / f)
        _KOKORO = Kokoro(str(d / "kokoro-v1.0.onnx"), str(d / "voices-v1.0.bin"))
    return _KOKORO


def tts(text: str, voice: str, cfg: dict, dest: Path) -> dict:
    """Write dest (48 kHz mono wav) and return {"dur", "on", "off"}: speech start/end inside the file."""
    meta_p = dest.with_suffix(".json")
    if dest.exists() and meta_p.exists():
        return json.loads(meta_p.read_text())
    import numpy as np
    raw = dest.with_suffix(".raw.wav")
    if config.MOCK and os.environ.get("HT_REAL_TTS") != "1":
        secs = max(1.2, len(text.split()) / 2.3)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"sine=frequency=180:sample_rate=24000:duration={secs:.2f}", "-af", "volume=0.3", str(raw)],
                       check=True)
    else:
        import soundfile as sf
        samples, sr = _kokoro().create(speakable(text), voice=voice, speed=float(cfg.get("voice_speed", 0.86)),
                                       lang="en-gb" if voice.startswith("b") else "en-us")
        sf.write(raw, samples, sr)
    pitch = float(cfg.get("voice_pitch", 0.96))      # a touch lower and warmer = older voice, same speed
    af = (f"asetrate=24000*{pitch},aresample=24000,atempo={1 / pitch:.4f}," if pitch != 1 else "") + \
        "highpass=f=70,lowpass=f=9000,aresample=48000"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", af, "-ac", "1", str(dest)],
                   check=True)
    raw.unlink(missing_ok=True)
    import soundfile as sf
    a, sr = sf.read(dest)
    env = np.abs(a)
    thr = max(0.02, env.max() * 0.06)
    idx = np.nonzero(env > thr)[0]
    info = {"dur": len(a) / sr, "on": float(idx[0] / sr) if len(idx) else 0.0,
            "off": float(idx[-1] / sr) if len(idx) else len(a) / sr}
    meta_p.write_text(json.dumps(info))
    return info


def word_times(text: str, on: float, off: float):
    """Spread the words over the speech span by rough syllable weight (+ pauses at punctuation)."""
    words = text.split()
    weights, pauses = [], []
    for w in words:
        syl = max(1, len(re.findall(r"[aeiouy]+", w.lower().rstrip("e")) or [1]))
        weights.append(0.55 + syl)
        pauses.append(1.3 if w[-1] in ".?!" else 0.6 if w[-1] in ",;:" else 0.0)
    total = sum(weights) + sum(pauses[:-1])
    t, out = on, []
    span = max(0.5, off - on)
    for w, wt, p in zip(words, weights, pauses):
        out.append((w, t))
        t += (wt + p) * span / total
    return out


# ---------------------------------------------------------------- picture
def portrait(ep: dict, wd: Path) -> Path:
    """Square FLUX close-up -> 1080x1920: centre 720x1024 crop scaled to 1080x1536 (face fills the frame),
    top/bottom 192 px extended with a dark blurred copy, feathered so the seam disappears."""
    out = wd / "portrait.png"
    if out.exists():
        return out
    from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    src = images.generate(ep["image_prompt"], int(ep["id"].split("-")[-1]) * 7919, wd / "elder.jpg")
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im = im.resize((1024, 1024), Image.Resampling.LANCZOS)
    main = im.crop((152, 0, 872, 1024)).resize((W, 1536), Image.Resampling.LANCZOS)
    bg = im.resize((H, H), Image.Resampling.LANCZOS).crop(((H - W) // 2, 0, (H + W) // 2, H))
    bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(45))).enhance(0.45)
    mask = Image.new("L", (W, 1536), 255)
    d = ImageDraw.Draw(mask)
    for i in range(140):
        v = int(255 * i / 140)
        d.line([(0, i), (W, i)], fill=v)
        d.line([(0, 1535 - i), (W, 1535 - i)], fill=v)
    bg.paste(main, (0, 192), mask)
    bg.save(out)
    return out


PAD_W, PAD_H, PAD_SCALE = 2.0, 1.25, 0.75   # SadTalker canvas: 2x width, 1.25x height, then scaled to 75%


def pad_for_sadtalker(img: Path, dest: Path) -> Path:
    """SadTalker crops a square ~4x the eye distance around the face. Our close-up fills the whole width, so that
    square ran off the image, got clipped/squashed and the face check failed ('bboxes[0]' IndexError). Put the
    portrait in the middle of a wider dark blurred canvas so the square fits; lipsync() crops it back afterwards."""
    from PIL import Image, ImageFilter, ImageEnhance
    im = Image.open(img).convert("RGB")
    cw, chh = int(im.width * PAD_W), int(im.height * PAD_H)
    bg = im.resize((cw, chh), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(60))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)
    bg.paste(im, ((cw - im.width) // 2, (chh - im.height) // 2))
    size = (int(cw * PAD_SCALE) // 2 * 2, int(chh * PAD_SCALE) // 2 * 2)
    bg.resize(size, Image.Resampling.LANCZOS).save(dest)
    return dest


def lipsync(img: Path, voice: Path, wd: Path, total: float) -> Path:
    out = wd / "talking.mp4"
    if out.exists():
        return out
    mode = os.environ.get("LIPSYNC", "still" if config.MOCK else "sadtalker")
    if mode == "still":
        print("   (LIPSYNC=still: no lip-sync, test render only)")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-i", str(img),
                        "-t", f"{total:.2f}", "-vf", f"scale={W}:{H},setsar=1", "-c:v", "libx264", "-preset",
                        "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True)
        return out
    st_dir = Path(os.environ.get("SADTALKER_DIR", Path.home() / "sadtalker")).resolve()
    py = os.environ.get("SADTALKER_PY", str(st_dir / "venv" / "bin" / "python"))
    if not (st_dir / "inference.py").exists():
        raise RuntimeError(f"SadTalker not found in {st_dir} - run tools/setup_sadtalker.sh")
    a16 = wd / "voice16k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-ac", "1", "-ar", "16000", str(a16)],
                   check=True)
    res = wd / "sadtalker"
    shutil.rmtree(res, ignore_errors=True)
    padded = pad_for_sadtalker(img, wd / "sadtalker_src.png")
    cmd = [py, "inference.py", "--driven_audio", str(a16.resolve()), "--source_image", str(padded.resolve()),
           "--result_dir", str(res.resolve()), "--still", "--preprocess", "full", "--size", "256",
           "--expression_scale", os.environ.get("SADTALKER_EXPRESSION", "1.1")]
    enh = os.environ.get("SADTALKER_ENHANCER", "gfpgan")
    if enh and enh != "none":
        cmd += ["--enhancer", enh]
    if os.environ.get("SADTALKER_GPU") != "1":
        cmd += ["--cpu"]
    print("   lip-sync: SadTalker (CPU, this takes a while)")
    t0 = dt.datetime.now()
    r = subprocess.run(cmd, cwd=st_dir, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("SadTalker failed:\n" + (r.stderr or r.stdout)[-3000:])
    mp4s = sorted(res.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not mp4s:
        raise RuntimeError("SadTalker produced no video:\n" + r.stdout[-2000:])
    # cut the padding off again: back to the original 1080x1920 portrait framing
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4s[-1]), "-vf",
                    f"crop=iw*{1 / PAD_W:.6f}:ih*{1 / PAD_H:.6f}:iw*{(1 - 1 / PAD_W) / 2:.6f}:ih*{(1 - 1 / PAD_H) / 2:.6f},"
                    f"scale={W}:{H}:flags=lanczos,setsar=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)], check=True)
    print(f"   lip-sync done in {(dt.datetime.now() - t0).seconds // 60} min")
    return out


# ---------------------------------------------------------------- captions (ASS, libass)
def _ass_color(hexcol: str) -> str:
    h = hexcol.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def build_ass(cfg, blocks, labels, dest: Path):
    """blocks: [(start, end, [(word, t), ...], kind)]; labels: [(start, end, text)]."""
    look = cfg.get("look", {})
    white, gold = _ass_color(look.get("word", "#FFFFFF")), _ass_color(look.get("power_word", "#F2C84B"))
    label = _ass_color(look.get("label", "#C9D6C3"))
    size = int(look.get("caption_size", 68))
    bank = power_words(cfg)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,{size},{white},{white},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,3,8,100,100,430,1
Style: Label,DejaVu Sans,40,{label},{label},&H00000000,&H64000000,-1,0,0,0,100,100,3,0,1,4,2,8,60,60,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for start, end, words, kind in blocks:
        for k, (_, t) in enumerate(words):
            t_end = words[k + 1][1] if k + 1 < len(words) else end
            parts = []
            for j, (w, _) in enumerate(words):
                col = gold if (kind == "cta" or is_power(w, bank)) else white
                if j < k:
                    parts.append(f"{{\\alpha&H00&\\c{col}}}{w}")
                elif j == k:      # newest word pops in
                    parts.append(f"{{\\alpha&HFF&\\c{col}\\t(0,110,\\alpha&H00&)}}{w}")
                else:             # not spoken yet: laid out (so nothing jumps) but invisible
                    parts.append(f"{{\\alpha&HFF&}}{w}")
            ev.append(f"Dialogue: 1,{_ass_time(max(t - 0.06, start))},{_ass_time(t_end - 0.06 if k + 1 < len(words) else end)},"
                      f"Cap,,0,0,0,,{' '.join(parts)}")
    for start, end, text in labels:
        ev.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Label,,0,0,0,,{{\\fad(250,200)}}{text}")
    dest.write_text(head + "\n".join(ev) + "\n")
    return dest


# ---------------------------------------------------------------- one episode
def render(cfg, ep, wd: Path) -> Path:
    wd.mkdir(parents=True, exist_ok=True)
    seg_min = float(cfg.get("segment_seconds", 8))
    voice = ep.get("voice", "bm_george")
    lines = list(ep["lines"])
    cta = cfg.get("cta", "")
    print(f"   voice ({voice}) x {len(lines) + (1 if cta else 0)}")
    infos = [tts(t, voice, cfg, wd / f"line{i + 1}.wav") for i, t in enumerate(lines)]
    cta_info = tts(cta, voice, cfg, wd / "cta.wav") if cta else None

    # timeline: every line gets >= segment_seconds; the last one also carries the spoken question
    placements, blocks, labels = [], [], []
    t = 0.0
    for i, (text, inf) in enumerate(zip(lines, infos)):
        start = t
        at = start + LEAD
        placements.append((wd / f"line{i + 1}.wav", at))
        blocks.append((at + inf["on"] - 0.05, None, word_times(text, at + inf["on"], at + inf["off"]), "line"))
        need = LEAD + inf["dur"] + 0.5
        if i == len(lines) - 1 and cta_info:
            c_at = at + inf["dur"] + CTA_GAP
            placements.append((wd / "cta.wav", c_at))
            blocks.append((c_at + cta_info["on"] - 0.05, None,
                           word_times(cta, c_at + cta_info["on"], c_at + cta_info["off"]), "cta"))
            need = (c_at - start) + cta_info["dur"] + END_HOLD
        seg = max(seg_min, -(-need * 2 // 1) / 2)            # round up to 0.5 s
        if i == 0:
            labels.append((start + 0.1, start + seg - 0.2, cfg.get("brand", "Hard Truths").upper()))
        else:
            labels.append((start + 0.1, start + seg - 0.2,
                           f"HARD TRUTH\\N{{\\fs96\\c{_ass_color(cfg['look'].get('power_word', '#F2C84B'))}}}{i}"))
        t = start + seg
    total = t
    # each caption block stays until the next one starts (or the end)
    blocks = [(b[0], (blocks[k + 1][0] - 0.02) if k + 1 < len(blocks) else total, b[2], b[3])
              for k, b in enumerate(blocks)]
    labels[-1] = (labels[-1][0], total - 0.1, labels[-1][2])
    if cta_info:      # last label switches to the question prompt while it is asked
        c_start = blocks[-1][0]
        last = labels[-1]
        labels[-1] = (last[0], c_start, last[2])
        labels.append((c_start, total - 0.1, f"COMMENT THE NUMBER\\N{{\\fs90}}1 - {len(lines) - 1}"))

    # voice track
    vtrack = wd / "voice.wav"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, _ in placements:
        cmd += ["-i", str(p)]
    fc = [f"[{k}:a]adelay={int(at * 1000)}:all=1[d{k}]" for k, (_, at) in enumerate(placements)]
    fc.append("".join(f"[d{k}]" for k in range(len(placements))) +
              f"amix=inputs={len(placements)}:normalize=0,apad,atrim=0:{total:.3f}[a]")
    subprocess.run(cmd + ["-filter_complex", ";".join(fc), "-map", "[a]", "-ar", "48000", "-ac", "1", str(vtrack)],
                   check=True)

    img = portrait(ep, wd)
    talk = lipsync(img, vtrack, wd, total)
    ass = build_ass(cfg, blocks, labels, wd / "captions.ass")

    music = assemble.find_music(cfg.get("music", "calm-piano"))
    out = wd / "final.mp4"
    grade = ("eq=saturation=0.70:contrast=1.07:brightness=-0.015:gamma=0.97,"
             "colorbalance=rs=-0.06:gs=0.025:bs=-0.035:rm=-0.05:gm=0.035:bm=-0.01:rh=-0.03:gh=0.02:bh=-0.01,"
             "vignette=angle=PI/4.5,noise=alls=5:allf=t")
    zoom = (f"scale=w='trunc({W}*(1+0.055*t/{total:.2f})/2)*2':h=-2:eval=frame:flags=bicubic,"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2.6")
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},{zoom},"
          f"{grade},ass={ass.resolve()}:fontsdir={FONT_DIR},format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(talk), "-i", str(vtrack)]
    vol = float(cfg.get("music_volume", 0.16))
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
        af = (f"[2:a]volume={vol},afade=t=in:st=0:d=2,afade=t=out:st={total - 3:.2f}:d=3[m];"
              f"[1:a]volume=1.0,acompressor=threshold=0.2:ratio=2.5:attack=5:release=120[vo];"
              f"[vo][m]amix=inputs=2:normalize=0:duration=first,"
              f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11[a]")
    else:
        print("   (music/calm-piano.mp3 missing: voice only)")
        af = f"[1:a]loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11[a]"
    r = subprocess.run(cmd + ["-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
                              "-t", f"{total:.2f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                              "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                              "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("hardtruths ffmpeg failed:\n" + r.stderr[-2000:])
    return out


# ---------------------------------------------------------------- publishing
def metadata(cfg, ep, bible):
    title = cfg["title_template"].format(Theme=ep["theme"].title(), theme=ep["theme"], age=ep["age"])[:100]
    truths = "\n".join(f"{i}. {l}" for i, l in enumerate(ep["lines"][1:], 1))
    tags = [ep["theme"]] + cfg.get("tags", [])
    desc = (f"{ep['lines'][0]}\n\n{truths}\n\n{cfg.get('cta', '')}\n\n"
            + (f"{seo.about(bible)}\n\n" if seo.about(bible) else "")
            + f"{cfg.get('ai_disclosure', config.AI_DISCLOSURE)}\n\n" + seo.hashtag_line(bible, tags))
    return {"title": title, "description": desc[:4900], "tags": seo.youtube_tags(bible, tags), "topic_tags": tags,
            "made_for_kids": bool(bible.get("made_for_kids", False))}


def keep_preview(ep_id: str, wd: Path) -> str:
    """Store the render in GitHub Release hardtruths-preview (phone-downloadable). Returns the download URL."""
    if config.MOCK or not shutil.which("gh") or os.environ.get("HT_SKIP_RELEASE") == "1":
        return ""
    from . import storage
    named = wd / f"{ep_id}.mp4"
    shutil.copy(wd / "final.mp4", named)
    storage._upload("hardtruths-preview", "Hard Truths previews", [named, wd / "metadata.json"])
    repo = os.environ.get("GITHUB_REPOSITORY", "leverageonheroes/Daily-Video-")
    return f"https://github.com/{repo}/releases/download/hardtruths-preview/{ep_id}.mp4"


def run_channel(s, ch, upload=True):
    cfg = load_cfg(ch)
    bible = json.loads((config.CHANNELS_DIR / ch / "channel.json").read_text())
    st = s["channels"].setdefault(ch, {"done": {}})
    paused = bool(cfg.get("paused")) and os.environ.get("HT_FORCE_UPLOAD") != "1"
    eps = cfg["episodes"]
    want = os.environ.get("HT_EPISODE")
    if want:
        ep = next(e for e in eps if e["id"] == want)
    else:
        ep = next((e for e in eps if not st["done"].get(e["id"], {}).get("youtube_id")), None)
        if ep is None:
            print(f"!! {ch}: all {len(eps)} Hard Truths scripts are used - write the next batch")
            return None
        if paused and st["done"].get(ep["id"], {}).get("preview"):
            print(f"   {ch}: Hard Truths is paused and {ep['id']} is already waiting for review: "
                  f"{st['done'][ep['id']]['preview']}")
            return None
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if upload and not paused and os.environ.get("YT_PUBLISH_NOW") != "1" and \
            any(r.get("rendered", "").startswith(today) and r.get("youtube_id") for r in st["done"].values()):
        print(f"   {ch}: a Hard Truths Short was already uploaded today - skipped")
        return None
    wd = config.OUTPUT / "hardtruths" / ch / ep["id"]
    print(f"\n== Hard Truths {ch} {ep['id']}: {ep['theme']} (age {ep['age']})")
    final = render(cfg, ep, wd)
    meta = metadata(cfg, ep, bible)
    (wd / "metadata.json").write_text(json.dumps(meta, indent=2))
    rec = st["done"].setdefault(ep["id"], {})
    rec.update({"theme": ep["theme"], "rendered": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "seconds": round(assemble.duration(final), 2)})
    url = keep_preview(ep["id"], wd)
    if url:
        rec["preview"] = url
        print(f"   preview: {url}")
    if upload and not paused:
        from . import carousel, youtube
        if os.environ.get("YT_PUBLISH_NOW") != "1":
            meta["publish_at"] = carousel.publish_time(cfg)
        res = youtube.upload(ch, final, meta)
        rec.update(res)
        print(f"   -> https://youtu.be/{res['youtube_id']} (public at {res.get('publish_at')})")
        rec["meta"] = carousel.post_meta(ch, final, meta)          # Facebook + Instagram (never blocks)
        try:                                                       # TikTok: video + caption for manual posting
            from . import storage
            storage.save_tiktok(ch, ep["id"], final, {"title": meta["title"], "description": ep["lines"][0],
                                                      "tags": meta.get("topic_tags", [])})
        except Exception as e:
            print(f"!! {ch}: TikTok copy failed: {e}")
    else:
        print(f"   -> {final} ({'paused: review the preview, then set paused=false' if paused else 'upload off'})")
    return final


def run(argv):
    upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
    s = load_state()
    failed = False
    for ch in argv or ["elders"]:
        try:
            run_channel(s, ch, upload=upload)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"!! {ch}: hardtruths failed: {e}")
            failed = True
        save_state(s)
    return failed
