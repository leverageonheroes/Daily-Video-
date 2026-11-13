"""Moral Of The Story TV "flow-film" episodes: Google Flow clips + a film cut list (episode "format": "flow-film").

An episode carries
  voices  {char: {"brief", "tags"}}             fixed TTS voice per character (channel.json cast_voices picks the voice)
  scenes  {"A": {"title", "loc", "ambience_clip", "music", "music_level", "out"}}
  clips   [{"n", "scene", "chars", "faces", "speaks", "keyframe", "flow_prompt", ["loc"]}]   made in Google Flow
  edit    [{"clip", "in", "dur", ["line"|"vo": {"c", "t", "tag", "at"}], ["sfx"|"sfx_start"|"sfx_end"], ["freeze"]}]
  accounts {"A": [1..5], "B": [...], ...}      which Flow account makes which clip

Steps:
  1. flow-frames <ch> <id>  start frame per clip (fal image model + the cast reference images, ~$0.02 each)
                           -> inbox/<ch>/frames/<id>/NN.jpg; PROMPTS.md shows frame + prompt per clip.
  2. Human: Google Flow, Frames to Video, start frame + prompt -> clip; upload 1.mp4 .. N.mp4 to inbox/<ch>/.
  3. flow-import: cut list -> segments; each spoken `line` = fixed-voice TTS lip-synced onto the one visible
     face (fal Kling lip-sync); `vo` lines are heard over the shot. Flow's own audio is used only as scene
     ambience (from the scene's ambience_clip; speaking clips are never used, their Veo voices would leak).
     Music per scene, self-made SFX (assets/sfx), scene transitions, freeze, then assemble.assemble() adds
     hook, part label, timed captions, recap, end card, grade and loudness.
Everything is cached in output/<ch>/<id>/ff/, so a rerun never pays twice. MOCK=1 = free placeholder run.
"""
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config

CLIP_SECONDS = 8.0
SFX_FILES = {"riser": "riser", "boom": "boom", "whoosh": "whoosh", "heartbeat": "heartbeat", "footstep": "footsteps"}
MUSIC_LEVELS = {"low": 1.0, "rising": 1.0, "cut-on-last-line": 1.0, "none": 0.0, "high": 1.6}
AMBIENCE_VOLUME = 0.55
SFX_VOLUME = 0.8
MAX_SPEEDUP = 1.12
# ElevenLabs premade voices, picked by the voice brief when channel.json cast_voices has no entry.
AUTO_VOICES = {("f", "old"): ["Lily", "Matilda", "Laura"], ("f", "young"): ["Sarah", "Jessica", "Alice"],
               ("m", "old"): ["Bill", "Brian", "George"], ("m", "young"): ["Chris", "Eric", "Liam"]}
# rough fal prices (USD) for the cost estimate only
PRICE_FRAME = 0.02
PRICE_TTS_1K = 0.10
PRICE_LIPSYNC_SEC = 0.014


def is_flowfilm(ep: dict) -> bool:
    return ep.get("format") == "flow-film"


def seg_seconds(e: dict) -> float:
    return float(e["dur"]) + float(e.get("freeze", 0))


def _clips(ep):
    return {c["n"]: c for c in ep["clips"]}


def clip_loc(ep, clip):
    return clip.get("loc") or ep["scenes"][clip["scene"]]["loc"]


def account_of(ep, n):
    return next((a for a, ns in ep.get("accounts", {}).items() if n in ns), "")


def _words(t):
    return len(re.findall(r"[A-Za-z0-9']+", t))


def _cap_span(ln, seg_dur, speech=None):
    start = float(ln.get("at", 0))
    span = speech if speech else max(_words(ln["t"]) / 2.5, 0.8)
    return start, min(start + span + 0.25, seg_dur - 0.05)


# seconds each side of a scene change: dip = 0.4 s through black, flash = 6 white frames at 30 fps
TRANSITION_FADE = {"dip": 0.2, "flash": 0.1}


def word_times(text: str, start: float, end: float) -> list:
    """[(word, start, end)] spread over the spoken span by character count (no TTS timestamps needed)."""
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 1 for w in words]
    span, t, out = max(end - start - 0.2, 0.3), start, []
    for w, k in zip(words, weights):
        d = span * k / sum(weights)
        out.append((w, round(t, 3), round(t + d, 3)))
        t += d
    return out


def pseudo_shots(ep: dict, speech: dict | None = None) -> list:
    """The cut list as ordinary `shots`, so compile / recap / stories / captions work unchanged.
    speech = {(edit index, "line"|"vo"): seconds} from the real TTS (exact caption timing)."""
    clips, scenes = _clips(ep), ep["scenes"]
    out, prev = [], None
    for i, e in enumerate(ep["edit"]):
        c = clips[e["clip"]]
        sc = c["scene"]
        tr = "cut"
        if prev and sc != prev and scenes[prev].get("out") in ("dip", "flash"):
            tr = scenes[prev]["out"]
        caps, lines = [], []
        for kind in ("vo", "line"):
            ln = e.get(kind)
            if ln:
                s, t = _cap_span(ln, float(e["dur"]), (speech or {}).get((i, kind)))
                caps.append({"t": ln["t"], "s": s, "e": t, "words": word_times(ln["t"], s, t)})
                lines.append({"c": ln["c"], "t": ln["t"]})
        out.append({"n": i + 1, "dur": seg_seconds(e), "clip": e["clip"], "chars": c["chars"], "fade": TRANSITION_FADE,
                    "loc": clip_loc(ep, c), "lines": lines, "caps": sorted(caps, key=lambda x: x["s"]),
                    "transition": tr, "freeze": float(e.get("freeze", 0))})
        prev = sc
    return out


def with_shots(ep: dict) -> dict:
    return {**ep, "shots": pseudo_shots(ep)} if is_flowfilm(ep) and "shots" not in ep else ep


def estimate_cost(ep: dict, frames: bool = False) -> float:
    chars = sum(len(e[k]["t"]) for e in ep["edit"] for k in ("line", "vo") if e.get(k))
    lips = sum(float(e["dur"]) for e in ep["edit"] if e.get("line"))
    return (len(ep["clips"]) * PRICE_FRAME if frames else 0) + chars / 1000 * PRICE_TTS_1K + lips * PRICE_LIPSYNC_SEC


# ---------------------------------------------------------------- ffmpeg helpers

def _ff(*args):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed: {' '.join(map(str, args))[:300]}\n{r.stderr[-1200:]}")


# ---------------------------------------------------------------- 1. start frames

def frame_prompt(bible, ep, clip, names):
    from . import prompts
    cast = prompts.cast(bible, ep)
    refs = "; ".join(f"image {i + 1} is {n}" for i, n in enumerate(names))
    who = "; ".join(f"{cast[c]['name']}: {cast[c]['ref_prompt']}" for c in clip["chars"] if c in cast)
    style = bible["style_prompt"].replace("film still, ", "")
    return " ".join(x for x in (
        "Create one vertical 9:16 photoreal frame from a premium drama series.",
        f"Reference images: {refs}. Each person must look exactly like their reference image (same face, "
        "skin tone, hair, clothing)." if names else "",
        clip["keyframe"],
        "Exactly the people described, nobody else, no extra figures, no text.",
        f"Setting: {prompts.locations(bible, ep)[clip_loc(ep, clip)]}.",
        f"People in frame: {who}." if who else "No people in frame.",
        f"Exactly {clip.get('faces', len(clip['chars']))} clearly visible face(s); no reflections of faces, "
        "no portraits or photos of faces, background people fully out of focus.",
        f"Style: {style}.",
        "Mouths closed. No text, no letters, no subtitles, no watermark.") if x)


def frames_dir(channel, ep_id) -> Path:
    from . import flow
    return flow.inbox(channel) / "frames" / ep_id


def frames_release(bible) -> str:
    return bible.get("flow", {}).get("frames_release") or f"{bible.get('episode_id_prefix', 'ff').lower()}-frames"


def frame_asset(ep_id, n) -> str:
    return f"{ep_id}_{n:02d}.jpg"


def released_frames(bible, ep_id) -> set:
    """Clip numbers whose start frame is in the frames release (needs gh + GH_TOKEN; empty set otherwise)."""
    import json as _json
    try:
        r = subprocess.run(["gh", "release", "view", frames_release(bible), "--json", "assets"],
                           capture_output=True, text=True, timeout=60)
        names = {a["name"] for a in _json.loads(r.stdout)["assets"]} if r.returncode == 0 else set()
    except Exception:
        names = set()
    return {n for n in range(1, 100) if frame_asset(ep_id, n) in names}


def upload_frames(channel, bible, ep) -> bool:
    """Frames -> GitHub release <prefix>-frames as MOS-001_01.jpg ... (the issue shows them inline from there)."""
    import shutil
    import tempfile
    files = sorted(frames_dir(channel, ep["id"]).glob("[0-9][0-9].jpg"))
    if not files or config.MOCK or not shutil.which("gh"):
        return False
    tag = frames_release(bible)
    if subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode != 0:
        subprocess.run(["gh", "release", "create", tag, "--title", f"{bible['show_title']} start frames",
                        "--notes", "Start frames for Google Flow (Frames to Video). Made by pipeline.run flow-frames."],
                       capture_output=True)
    with tempfile.TemporaryDirectory() as td:
        named = []
        for f in files:
            q = Path(td) / frame_asset(ep["id"], int(f.stem))
            shutil.copy(f, q)
            named.append(str(q))
        r = subprocess.run(["gh", "release", "upload", tag, *named, "--clobber"], capture_output=True, text=True)
    if r.returncode:
        print(f"   (could not upload frames to release {tag}: {(r.stderr or r.stdout).strip()[:200]})")
        return False
    print(f"   {len(files)} start frames -> release {tag}")
    return True


MAX_REROLLS = 2


def make_frames(channel: str, ep: dict) -> list:
    """Start frame per clip -> inbox/<ch>/frames/<id>/NN.jpg (cached: existing frames are never remade).
    Each frame is face-checked (free, faces.py): the clearly visible faces must equal the clip's `faces`,
    else it is re-rolled with a new seed (max 2). Every check and re-roll goes to qc.json."""
    import json as _json
    import random
    from . import fal_api, faces, generate, prompts
    bible = generate.load_bible(channel)
    cast = prompts.cast(bible, ep)
    out_dir = frames_dir(channel, ep["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    qc_file = out_dir / "qc.json"
    qc = _json.loads(qc_file.read_text()) if qc_file.exists() else {}
    todo = [c for c in ep["clips"] if not (out_dir / f"{c['n']:02d}.jpg").exists()]
    if todo:
        print(f"   {ep['id']}: {len(todo)} start frames to make (about ${len(todo) * PRICE_FRAME:.2f} + re-rolls)")
    refs = {cid: generate.reference_image(channel, bible, cid, cast[cid])
            for c in todo for cid in c["chars"]}
    made = []

    def gen(c, png, seed):
        if config.MOCK:
            return fal_api.mock_image(png, f"{ep['id']} clip {c['n']}: {c['keyframe']}", generate.COLORS[c["n"] % 6])
        urls = [fal_api.upload(refs[x]) for x in c["chars"]]
        model = config.IMAGE_EDIT if urls else config.IMAGE_KEY_T2I
        args = {"prompt": frame_prompt(bible, ep, c, [cast[x]["name"] for x in c["chars"]]),
                "num_images": 1, "output_format": "png", "seed": seed}
        if "nano-banana" in model:
            args["aspect_ratio"] = "9:16"
        else:
            args["image_size"] = config.KEYFRAME_SIZE
        if urls:
            args["image_urls"] = urls
        return fal_api.download(generate._first_image_url(fal_api.run(model, args)), png)

    def one(c):
        dest = out_dir / f"{c['n']:02d}.jpg"
        want = int(c.get("faces", len(c["chars"])))
        log = []
        for attempt in range(MAX_REROLLS + 1):
            png = out_dir / f"{c['n']:02d}_try{attempt}.png"
            seed = random.randint(1, 2**31 - 1)
            gen(c, png, seed)
            made.append(c["n"])
            got = None if config.MOCK else faces.count_image(png)
            log.append({"try": attempt + 1, "seed": seed, "faces": got, "want": want})
            if got is None or got == want or attempt == MAX_REROLLS:
                break
            print(f"   frame {c['n']:02d}: {got} faces, want {want} -> re-roll {attempt + 1}/{MAX_REROLLS}")
            png.unlink(missing_ok=True)
        _ff("-i", png, "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280", "-q:v", "3", dest)
        png.unlink(missing_ok=True)
        ok = got is None or got == want
        qc[str(c["n"])] = {"ok": ok, "tries": log, "check": "skipped (mock or no OpenCV)" if got is None else "faces"}
        flag = "" if ok else f"  !! still {got} faces (want {want}) - check this one"
        print(f"   frame {c['n']:02d} -> {dest.relative_to(config.ROOT) if dest.is_relative_to(config.ROOT) else dest}"
              f"  ({len(log)} tr{'y' if len(log) == 1 else 'ies'}){flag}")
        return dest

    with ThreadPoolExecutor(max_workers=config.PARALLEL_SHOTS) as pool:
        list(pool.map(one, todo))
    qc_file.write_text(_json.dumps(qc, indent=1) + "\n")
    if made:
        rerolls = len(made) - len(todo)
        print(f"   COST frames: {len(made)} images ({rerolls} re-rolls) = about ${len(made) * PRICE_FRAME:.2f}"
              + (" (mock: $0)" if config.MOCK else ""))
    bad = [n for n, q in qc.items() if not q["ok"]]
    if bad:
        print(f"   !! frames with the wrong face count after {MAX_REROLLS} re-rolls: {', '.join(bad)}")
    print("   (text on frames is not checked automatically: look at the review page before using them)")
    upload_frames(channel, bible, ep)
    return sorted(out_dir.glob("[0-9][0-9].jpg"))


def _repo():
    import os
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=config.ROOT, capture_output=True, text=True)
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", r.stdout.strip())
        repo = m.group(1) if m else ""
    return repo


PHONE_GUIDE = """**How to make the clips (phone):**
1. Open Flow with the account named in the section.
2. Choose New project → Frames to Video → {model}, {aspect}, 1 output.
3. For each clip: long-press the image → Save. Upload it as the start frame, copy the prompt, then Generate.
4. If a clip has an extra person, a changed face or text on screen, generate it again (it's free).
5. Download it, name it with the clip number (`1.mp4`), and upload it to `inbox/{channel}/`."""


def prompts_markdown(channel: str, bible: dict, ep: dict) -> str:
    f = bible.get("flow", {})
    n = len(ep["clips"])
    fdir = frames_dir(channel, ep["id"])
    local = {int(p.stem) for p in fdir.glob("[0-9][0-9].jpg")} if fdir.exists() else set()
    released = released_frames(bible, ep["id"])
    repo = _repo()
    rel_url = f"https://github.com/{repo}/releases/download/{frames_release(bible)}" if repo else ""
    out = [f"## {bible['show_title']} - {ep['id']}: {ep['title'].replace(' #shorts', '')}", "",
           PHONE_GUIDE.format(model=f.get("model", "Veo 3.1 Lite"), aspect=f.get("aspect", "9:16"), channel=channel), "",
           f"The film is assembled when all {n} clips are in `inbox/{channel}/` (1.mp4 to {n}.mp4). "
           "Don't add dialogue: the voices are added later and lip-synced. "
           "Generate before 14:00 UTC (the free tier is paused ~14:00-17:00 UTC).", ""]
    have = released | local
    if len(have) < n:
        out += [f"> ⚠️ Start frames missing ({len(have)}/{n}). In the Codespace: "
                f"`python -m pipeline.run flow-frames {channel} {ep['id']}` (about ${(n - len(have)) * PRICE_FRAME:.2f}).", ""]
    accts = ep.get("accounts") or {"": [c["n"] for c in ep["clips"]]}
    names = f.get("accounts", [])
    clips = _clips(ep)
    for k, (a, ns) in enumerate(accts.items()):
        label = names[k] if k < len(names) else a
        out += ["---", f"## Account {label}: clips {ns[0]}–{ns[-1]}", ""]
        for cn in ns:
            c = clips[cn]
            out.append(f"### Clip {cn} · scene {c['scene']} · {ep['scenes'][c['scene']]['title']}")
            if cn in released and rel_url:
                url = f"{rel_url}/{frame_asset(ep['id'], cn)}"
                out += [f'<img src="{url}" width="240">', "", f"[⬇️ Download start frame {cn}]({url})"]
            elif cn in local and repo:
                url = f"https://github.com/{repo}/blob/main/inbox/{channel}/frames/{ep['id']}/{cn:02d}.jpg"
                out.append(f"Start frame: [{cn:02d}.jpg]({url})")
            out += ["```", c["flow_prompt"], "```", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- 3. render (after the clips are in)

class ClipProblem(Exception):
    """A Flow clip must be regenerated. str(e) is the message for the issue; the clips stay in the inbox."""


def _voice_for(bible, ep, char, used) -> dict:
    cv = bible.get("cast_voices", {}).get(char)
    if cv:
        return cv if isinstance(cv, dict) else {"voice": cv}
    brief = ep.get("voices", {}).get(char, {}).get("brief", "").lower()
    pool = voice_pool(brief)
    return {"voice": next((v for v in pool if v not in used), pool[0])}


# more ElevenLabs premade voices of the same kind, so two similar characters get different candidates
WIDE_VOICES = {("f", "old"): ["Charlotte", "Aria"], ("f", "young"): ["Charlotte", "River"],
               ("m", "old"): ["Daniel", "Roger", "Callum"], ("m", "young"): ["Will", "Charlie", "Callum"]}


def voice_pool(brief: str, wide: bool = False) -> list:
    """The candidate ElevenLabs voices for a voice brief (sex + age read from the words)."""
    brief = brief.lower()
    sex = "f" if re.search(r"\b(woman|girl|female|mother|lady|she)\b", brief) else "m"
    m = re.search(r"(\d{2})", brief)
    old = bool(re.search(r"\b(older|old|mature|elderly)\b", brief)) or bool(m and int(m.group(1)) >= 45)
    key = (sex, "old" if old else "young")
    return AUTO_VOICES[key] + (WIDE_VOICES[key] if wide else [])


def voice_map(bible, ep) -> dict:
    used, out = [], {}
    for c in ep.get("voices", {}):
        out[c] = _voice_for(bible, ep, c, used)
        used.append(out[c]["voice"])
    return out


def _v3_text(ln):
    tags = "".join(f"[{t.strip()}]" for t in ln.get("tag", "").strip("[] ").split(",") if t.strip())
    return f"{tags} {ln['t']}".strip()


SPEND = {"tts_chars": 0, "lipsync_s": 0.0}     # what this run actually paid for (cached files are free)


def tts_line(bible, ln, voice: dict, dest: Path) -> Path:
    """Fixed-voice TTS for one line (cached), trimmed and levelled to -16 LUFS.
    ElevenLabs v3 gets the emotion tags; Turbo v2.5 gets plain text."""
    if dest.exists():
        return dest
    from . import fal_api
    from .narration import _audio_url, _mock_tts
    if config.MOCK:
        raw = _mock_tts(ln["t"], dest)
        SPEND["endpoint"] = voice.get("endpoint") or bible.get("tts", {}).get("endpoint", "mock")
    else:
        cfg = bible.get("tts", {})
        order = [voice.get("endpoint"), cfg.get("endpoint", "fal-ai/elevenlabs/tts/eleven-v3"),
                 cfg.get("fallback", "fal-ai/elevenlabs/tts/turbo-v2.5")]
        tries = [(e, _v3_text(ln) if "v3" in e else ln["t"]) for i, e in enumerate(order) if e and e not in order[:i]]
        raw, errors = None, []
        for endpoint, text in tries:
            try:
                res = fal_api.run(endpoint, {"text": text, "voice": voice["voice"]}, retries=1)
                url = _audio_url(res)
                if not url:
                    raise RuntimeError("no audio url in response")
                raw = fal_api.download(url, dest.with_suffix(".src" + Path(url.split("?")[0]).suffix))
                SPEND["tts_chars"] += len(text)
                SPEND["endpoint"] = endpoint
                break
            except Exception as e:
                errors.append(f"{endpoint}: {e}")
                print(f"   tts {endpoint} failed ({str(e)[:120]})")
        if raw is None:
            raise fal_api.GenerationError("all TTS endpoints failed -> " + " | ".join(errors))
    _ff("-i", raw, "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse,aresample=48000,"
        "loudnorm=I=-16:TP=-2:LRA=7,aresample=48000", "-ac", "2", dest)
    return dest


def fit_edit(ep: dict, speech: dict) -> tuple:
    """Fit every spoken line inside its cut: 1) start it earlier, 2) lengthen the cut (up to the clip end),
    3) speed it up (max 1.12x), 4) warn. speech = {(i, kind): TTS seconds}.
    Returns (edit copy with new `at`/`dur`, {(i, kind): tempo}, [notes])."""
    import copy
    edit = copy.deepcopy(ep["edit"])
    tempos, notes = {}, []
    for i, e in enumerate(edit):
        for kind in ("vo", "line"):
            ln = e.get(kind)
            if not ln or (i, kind) not in speech:
                continue
            need = speech[(i, kind)] + 0.1
            at, dur = float(ln.get("at", 0)), float(e["dur"])
            if at + need > dur:
                ln["at"] = round(max(0.1, dur - need), 2)
                if ln["at"] != at:
                    notes.append(f"cut {i + 1} {kind}: starts at {ln['at']:.2f}s (was {at:.2f}s)")
            at = float(ln.get("at", 0))
            if at + need > dur:
                new = round(min(CLIP_SECONDS - float(e["in"]), at + need), 2)
                if new > dur:
                    e["dur"] = new
                    notes.append(f"cut {i + 1}: lengthened {dur:.2f}s -> {new:.2f}s")
            dur = float(e["dur"])
            if at + need > dur:
                tempo = speech[(i, kind)] / max(dur - at - 0.1, 0.1)
                tempos[(i, kind)] = min(tempo, MAX_SPEEDUP)
                notes.append(f"cut {i + 1} {kind}: sped up x{min(tempo, MAX_SPEEDUP):.2f}")
                if tempo > MAX_SPEEDUP:
                    notes.append(f"!! cut {i + 1} {kind}: line is {speech[(i, kind)]:.1f}s and still does not fit "
                                 f"({dur - at:.1f}s) - shorten the line or pick a longer cut")
    return edit, tempos, notes


def _probe(path: Path) -> tuple:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        w, h = map(int, r.stdout.strip().split(",")[:2])
    except ValueError:
        w = h = 0
    return w, h


def face_check_on(bible) -> bool:
    import os
    env = os.environ.get("FACE_CHECK")
    if env is not None:
        return env == "1"
    return bible.get("face_check", True) and not config.MOCK


def check_clips(ep: dict, clips: dict, bible: dict) -> list:
    """Free checks before anything is paid for: ~8 s, vertical, has sound, and (OpenCV) the face count inside
    every cut that uses the clip (5 frames; a speaking cut needs exactly 1). Returns problem messages."""
    from . import assemble, faces
    problems = {}
    for n, p in clips.items():
        d, (w, h) = assemble.duration(p), _probe(p)
        if not 7.0 <= d <= 9.0:
            problems.setdefault(n, f"Clip {n}: it is {d:.1f} s long (should be 8 s), please regenerate clip {n}")
        elif h <= w:
            problems.setdefault(n, f"Clip {n}: it is not vertical ({w}x{h}), please regenerate clip {n} in 9:16")
        elif not assemble.has_audio(p):
            problems.setdefault(n, f"Clip {n}: it has no sound, please download it again with audio")
    if face_check_on(bible):
        cl = _clips(ep)
        for i, e in enumerate(ep["edit"]):
            n = e["clip"]
            if n in problems or n not in clips:
                continue
            a, d = float(e["in"]), float(e["dur"])
            counts = faces.count_video(clips[n], [a + d * (k + 0.5) / 5 for k in range(5)])
            if counts is None:
                print("   (face check skipped: OpenCV not installed)")
                break
            got = faces.typical(counts)
            want = 1 if e.get("line") else int(cl[n].get("faces", len(cl[n]["chars"])))
            print(f"   face check cut {i + 1} (clip {n}): {counts} -> {got}, want {want}")
            if got is not None and got != want:
                problems[n] = (f"Clip {n}: {got} face{'s' if got != 1 else ''} found (want {want}), "
                               f"please regenerate clip {n}")
    return [problems[n] for n in sorted(problems)]


def _segment(src: Path, e: dict, dest: Path) -> Path:
    if not dest.exists():
        _ff("-ss", f"{float(e['in']):.2f}", "-i", src, "-t", f"{float(e['dur']):.2f}", "-an",
            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", dest)
    return dest


LIPSYNC_MIN = 2.0     # Kling lip-sync needs 2-10 s of video


def _lipsync(bible, video: Path, audio: Path, dest: Path) -> Path:
    """Lip-sync one cut. Cuts under 2 s are padded (last frame held) and trimmed back after.
    Each result is re-checked (same length, still one face); a failed check moves on to the next endpoint."""
    if dest.exists():
        return dest
    from . import assemble, fal_api, faces
    want = assemble.duration(video)
    src_v, src_a = video, audio
    if want < LIPSYNC_MIN:
        src_v = dest.with_name(dest.stem + "_padv.mp4")
        src_a = dest.with_name(dest.stem + "_pada.wav")
        _ff("-i", video, "-vf", f"tpad=stop_mode=clone:stop_duration={LIPSYNC_MIN:.2f}", "-t", f"{LIPSYNC_MIN:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", src_v)
        _ff("-i", audio, "-af", "apad", "-t", f"{LIPSYNC_MIN:.2f}", src_a)
    tmp = dest.with_name(dest.stem + "_raw.mp4")
    if config.MOCK:
        tmp.write_bytes(src_v.read_bytes())
    else:
        ls = bible.get("lipsync", {})
        eps = [ls.get("endpoint", "fal-ai/kling-video/lipsync/audio-to-video"), *ls.get("fallbacks", [])]
        v_url, a_url, errors, ok = fal_api.upload(src_v), fal_api.upload(src_a), [], False
        for ep in eps:
            try:
                args = {"video_url": v_url, "audio_url": a_url}
                if "sync-lipsync" in ep:
                    args["sync_mode"] = "cut_off"
                res = fal_api.run(ep, args, retries=1)
                fal_api.download(res["video"]["url"], tmp)
                SPEND["lipsync_s"] += max(want, LIPSYNC_MIN)
                got_d = assemble.duration(tmp)
                if abs(got_d - assemble.duration(src_v)) > 0.25:
                    raise RuntimeError(f"length changed ({got_d:.2f}s)")
                if face_check_on(bible):
                    n = faces.typical(faces.count_video(tmp, [got_d * k / 4 for k in (1, 2, 3)]) or [])
                    if n not in (None, 1):
                        raise RuntimeError(f"{n} faces after lip-sync")
                ok = True
                break
            except Exception as e:
                errors.append(f"{ep}: {e}")
                print(f"   lip-sync {ep} failed on {video.name} ({str(e)[:120]})")
        if not ok:
            raise fal_api.GenerationError("all lip-sync endpoints failed -> " + " | ".join(errors))
    _ff("-i", tmp, "-t", f"{want:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", dest)
    for q in (tmp, src_v if src_v != video else None, src_a if src_a != audio else None):
        if q:
            q.unlink(missing_ok=True)
    return dest


MOVING = re.compile(r"dolly|push|pans?\b|panning|track|orbit|handheld|crane|tilt|zoom|follows?\b|whip", re.I)
PUSH_IN = 0.03


def _finish_segment(src: Path, clip: dict, dest: Path):
    """1080x1920, 30 fps, no audio; a very slow digital push-in (1.00 -> 1.03) when the camera hardly moves."""
    from .assemble import duration
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
    if not MOVING.search(clip.get("flow_prompt", "")):
        d = max(duration(src), 0.5)
        vf += (f",scale=w='2*trunc(540*(1+{PUSH_IN}*t/{d:.2f}))':h=-2:eval=frame,crop=1080:1920")
    _ff("-i", src, "-an", "-vf", vf + ",format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", dest)


def _sfx_names(text: str) -> list:
    t = (text or "").lower()
    return [f for k, f in SFX_FILES.items() if k in t]


JCUT = 0.5            # next scene's background sound starts this early (J-cut)
FOLEY_VOLUME = 0.5    # silent cuts keep their own Flow sound at -6 dB over the scene bed
WHOOSH_VOLUME = 0.45  # soft whoosh on dip / flash scene changes


def _soundtrack(ep, bible, clips: dict, edit_audio: list, starts: list, total: float, wd: Path) -> Path:
    """One story-length track: scene ambience (J-cuts) + Foley from silent cuts + dialogue + SFX
    + scene music ducked under the dialogue (sidechaincompress)."""
    from . import assemble
    inputs, chains = [], []
    groups = {"bed": [], "mus": [], "dlg": []}
    cl = _clips(ep)

    def add(path, filt, group, loop=False):
        k = inputs.count("-i")
        inputs.extend((["-stream_loop", "-1"] if loop else []) + ["-i", str(path)])
        chains.append(f"[{k}:a]{filt}[x{k}]")
        groups[group].append(f"[x{k}]")

    def delay(t):
        ms = int(max(t, 0) * 1000)
        return f"adelay={ms}|{ms}"

    ranges, order = {}, []
    for i, e in enumerate(ep["edit"]):
        sc = cl[e["clip"]]["scene"]
        a, b = ranges.get(sc, (starts[i], starts[i]))
        ranges[sc] = (min(a, starts[i]), starts[i] + seg_seconds(e))
        if sc not in order:
            order.append(sc)
    for k_sc, sc in enumerate(order):
        t0, t1 = ranges[sc]
        cfg = ep["scenes"][sc]
        # ambience bed: the scene's non-speaking clip looped with crossfades, else room tone; J-cut into the scene
        lead = JCUT if k_sc else 0.0
        a0, span = t0 - lead, (t1 - t0) + lead
        amb_n = cfg.get("ambience_clip")
        src = clips.get(amb_n)
        fade = f"afade=t=in:d={max(lead, 0.3):.2f},afade=t=out:st={max(span - 0.4, 0):.2f}:d=0.4"
        if src and not cl.get(amb_n, {}).get("speaks") and assemble.has_audio(src):
            d = max(assemble.duration(src) - 0.3, 1.0)
            reps = int(span // (d - 0.5)) + 1
            k = inputs.count("-i")
            for _ in range(reps + 1):
                inputs.extend(["-i", str(src)])
            parts = "".join(f"[{k + j}:a]atrim=0:{d:.2f},asetpts=PTS-STARTPTS,aresample=48000[l{k}_{j}];"
                            for j in range(reps + 1))
            xf, prev = "", f"[l{k}_0]"
            for j in range(1, reps + 1):
                nxt = f"[c{k}_{j}]"
                xf += f"{prev}[l{k}_{j}]acrossfade=d=0.5{nxt};"
                prev = nxt
            chains.append(parts + xf + f"{prev}atrim=0:{span:.2f},volume={AMBIENCE_VOLUME},{fade},{delay(a0)}[x{k}]")
            groups["bed"].append(f"[x{k}]")
        else:
            if amb_n:
                print(f"   scene {sc}: ambience clip {amb_n} has speech (or no audio) -> soft room tone instead")
            k = inputs.count("-i")
            inputs.extend(["-f", "lavfi", "-t", f"{span:.2f}", "-i", "anoisesrc=c=brown:a=0.02:r=48000"])
            chains.append(f"[{k}:a]lowpass=f=400,{fade},{delay(a0)}[x{k}]")
            groups["bed"].append(f"[x{k}]")
        # scene change: soft whoosh (dip / flash)
        whoosh = config.ROOT / "assets" / "sfx" / "whoosh.wav"
        last_i = max(i for i, e in enumerate(ep["edit"]) if cl[e["clip"]]["scene"] == sc)
        if cfg.get("out") in ("dip", "flash") and k_sc < len(order) - 1 and whoosh.exists() \
                and "whoosh" not in _sfx_names(ep["edit"][last_i].get("sfx_end", "") + ep["edit"][last_i].get("sfx", "")):
            add(whoosh, f"aresample=48000,volume={WHOOSH_VOLUME},{delay(t1 - 0.35)}", "bed")
        # music
        mood = cfg.get("music")
        level = cfg.get("music_level", "low")
        music = assemble.find_music(mood) if mood and level != "none" else None
        if music:
            span = t1 - t0
            vol = config.MUSIC_VOLUME * MUSIC_LEVELS.get(level, 1.0)
            end = span
            if level == "cut-on-last-line":       # music stops 0.2 s before the last line (the boom lands on it)
                last = [starts[i] + float(e[k2].get("at", 0)) for i, e in enumerate(ep["edit"])
                        for k2 in ("line", "vo") if e.get(k2) and cl[e["clip"]]["scene"] == sc]
                end = (max(last) - t0 - 0.2) if last else span
            if level == "rising":
                vf = f"volume='{vol * 0.5:.4f}+{vol * 1.5:.4f}*t/{span:.2f}':eval=frame"
                tail = f"afade=t=out:st={max(end - 0.08, 0):.2f}:d=0.08" if cfg.get("out") == "flash" else \
                    f"afade=t=out:st={max(end - 0.6, 0):.2f}:d=0.6"
            else:
                vf = f"volume={vol:.4f}"
                cut = level == "cut-on-last-line"
                tail = f"afade=t=out:st={max(end - (0.05 if cut else 0.6), 0):.2f}:d={0.05 if cut else 0.6}"
            add(music, f"atrim=0:{end:.2f},asetpts=PTS-STARTPTS,aresample=48000,{vf},afade=t=in:d=0.5,{tail},"
                       f"{delay(t0)}", "mus", loop=True)
    for i, e in enumerate(ep["edit"]):
        c = cl[e["clip"]]
        # Foley: a silent cut keeps its own Flow sound (speaking clips never: their Veo voices would leak)
        src = clips.get(e["clip"])
        if not e.get("line") and not c.get("speaks") and src and assemble.has_audio(src):
            d = float(e["dur"])
            add(src, f"atrim={float(e['in']):.2f}:{float(e['in']) + d:.2f},asetpts=PTS-STARTPTS,aresample=48000,"
                     f"volume={FOLEY_VOLUME},afade=t=in:d=0.08,afade=t=out:st={max(d - 0.12, 0):.2f}:d=0.12,"
                     f"{delay(starts[i])}", "bed")
        # dialogue (lines + voice-overs; a vo plays over the shot = L-cut)
        for kind in ("vo", "line"):
            p = edit_audio[i].get(kind)
            if p:
                add(p, f"aresample=48000,{delay(starts[i] + float(e[kind].get('at', 0)))}", "dlg")
        # sound effects
        for key, when in (("sfx_start", 0.0), ("sfx", None), ("sfx_end", None)):
            for name in _sfx_names(e.get(key, "")):
                f = config.ROOT / "assets" / "sfx" / f"{name}.wav"
                if not f.exists():
                    print(f"   (sfx {name}.wav missing: python tools/make_sfx.py)")
                    continue
                if key == "sfx_end":
                    t = starts[i] + float(e["dur"]) - min(assemble.duration(f), float(e["dur"]))
                elif key == "sfx" and name == "boom" and e.get("line"):
                    t = starts[i] + float(e["line"].get("at", 0))      # the boom lands on the line
                else:
                    t = starts[i] if when is None else starts[i] + when
                add(f, f"aresample=48000,volume={SFX_VOLUME},{delay(t)}", "bed")
    mix = []
    fc = ";".join(chains)
    for g in ("bed", "mus", "dlg"):
        if groups[g]:
            fc += f";{''.join(groups[g])}amix=inputs={len(groups[g])}:duration=longest:normalize=0[{g}]"
    if groups["dlg"] and groups["mus"]:
        fc += ";[dlg]asplit=2[dlg1][key];[mus][key]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[duck]"
        mix = ["[bed]" if groups["bed"] else "", "[duck]", "[dlg1]"]
    else:
        mix = [f"[{g}]" for g in ("bed", "mus", "dlg") if groups[g]]
    mix = [m for m in mix if m]
    fc += f";{''.join(mix)}amix=inputs={len(mix)}:duration=longest:normalize=0,apad[a]"
    dest = wd / "soundtrack.wav"
    _ff(*inputs, "-filter_complex", fc, "-map", "[a]", "-t", f"{total:.2f}", "-ar", "48000", "-ac", "2", dest)
    return dest


def small_copy(final: Path, dest: Path) -> Path:
    """A copy under 4 MB for review in chat (540 px wide)."""
    for crf in (30, 34, 38):
        _ff("-i", final, "-vf", "scale=540:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", dest)
        if dest.stat().st_size < 4 * 1024 * 1024:
            break
    return dest


def render(channel: str, ep: dict, clip_files: list, wd: Path, bible: dict, recap=None) -> Path:
    """clip_files[i] = Google Flow clip n=i+1. Returns final.mp4 (and clean.mp4) via assemble.assemble().
    Raises ClipProblem (before anything is paid for) when a clip must be regenerated."""
    from . import assemble
    ff = wd / "ff"
    ff.mkdir(parents=True, exist_ok=True)
    clips = {c["n"]: p for c, p in zip(ep["clips"], clip_files)}
    problems = check_clips(ep, clips, bible)
    if problems:
        raise ClipProblem("; ".join(problems))
    SPEND.update(tts_chars=0, lipsync_s=0.0)
    voices = voice_map(bible, ep)
    print(f"   voices: " + ", ".join(f"{c}={v['voice']}" for c, v in voices.items()))

    # TTS per line / voice-over, then fit every line inside its cut
    raw, speech = {}, {}
    for i, e in enumerate(ep["edit"]):
        for kind in ("vo", "line"):
            ln = e.get(kind)
            if ln:
                v = voices.get(ln["c"], {"voice": "Brian"})
                raw[(i, kind)] = tts_line(bible, ln, v, ff / f"e{i + 1:02d}_{kind}_{v['voice']}.wav")
                speech[(i, kind)] = assemble.duration(raw[(i, kind)])
    edit, tempos, notes = fit_edit(ep, speech)
    for nline in notes:
        print(f"   fit: {nline}")
    ep = {**ep, "edit": edit}
    edit_audio = [{} for _ in edit]
    for (i, kind), p in raw.items():
        t = tempos.get((i, kind), 1.0)
        if t > 1.0:
            q = p.with_name(p.stem + f"_x{t:.2f}.wav")
            if not q.exists():
                _ff("-i", p, "-af", f"atempo={t:.3f}", q)
            p, speech[(i, kind)] = q, speech[(i, kind)] / t
        edit_audio[i][kind] = p

    # video segments; lip-sync the visible speaker (only their own line drives it)
    def seg(i):
        e = edit[i]
        tag = f"{float(e['in']):.2f}_{float(e['dur']):.2f}"
        v = _segment(clips[e["clip"]], e, ff / f"seg{i + 1:02d}_{tag}.mp4")
        if not edit_audio[i].get("line"):
            return v
        at = float(e["line"].get("at", 0))
        drive = ff / f"seg{i + 1:02d}_{tag}_drive_{edit_audio[i]['line'].stem}_{at:.2f}.wav"
        if not drive.exists():
            ms = int(at * 1000)
            _ff("-i", edit_audio[i]["line"], "-af", f"adelay={ms}|{ms},apad", "-t", f"{float(e['dur']):.2f}",
                "-ar", "48000", "-ac", "2", drive)
        print(f"   lip-sync cut {i + 1} (clip {e['clip']}, {e['line']['c']})")
        return _lipsync(bible, v, drive, drive.with_name(drive.stem.replace("_drive_", "_lips_") + ".mp4"))

    with ThreadPoolExecutor(max_workers=config.PARALLEL_SHOTS) as pool:
        segs = list(pool.map(seg, range(len(edit))))
    cl = _clips(ep)
    silent = []
    for i, p in enumerate(segs):
        q = ff / f"cut{i + 1:02d}.mp4"
        _finish_segment(p, cl[edit[i]["clip"]], q)
        silent.append(q)

    starts, t = [], 0.0
    for e in edit:
        starts.append(t)
        t += seg_seconds(e)
    track = _soundtrack(ep, bible, clips, edit_audio, starts, t, ff)
    film = {**ep, "shots": pseudo_shots(ep, speech), "music": None}    # music is in the soundtrack
    final = assemble.assemble(film, silent, wd, {**bible, "clip_audio_volume": 0.0},
                              narration=[track] + [None] * (len(silent) - 1), recap=recap)
    small = small_copy(final, wd / f"{ep['id']}_small.mp4")
    tts_cost = SPEND["tts_chars"] / 1000 * PRICE_TTS_1K
    lip_cost = SPEND["lipsync_s"] * PRICE_LIPSYNC_SEC
    print(f"   {ep['id']}: {assemble.duration(final):.1f}s flow-film, {len(edit)} cuts, "
          f"small copy {small.stat().st_size / 1e6:.1f} MB")
    print(f"   COST {ep['id']}: TTS ${tts_cost:.2f} + lip-sync ${lip_cost:.2f} = ${tts_cost + lip_cost:.2f} this run"
          f" (start frames were paid when they were made){' (mock: $0)' if config.MOCK else ''}")
    return final


# ---------------------------------------------------------------- 2. voice casting (once per arc)

def _short(char_id: str) -> str:
    return char_id.split("_", 1)[-1].lower()


def _arc_episodes(channel, arc):
    from . import state
    return [e for e in state.episodes(channel) if is_flowfilm(e) and e.get("arc") == arc]


def voices_dir(channel, arc) -> Path:
    return config.OUTPUT / channel / "voices" / arc


def voice_samples(channel: str, arc: str) -> Path:
    """3 candidate voices per character, each speaking one of that character's real lines (paid, a few cents).
    -> output/<ch>/voices/<arc>/<short>_<k>.mp3 + samples.json. Then: voices <ch> <arc> pick "mama 2, tobi 1"."""
    import json as _json
    from . import generate
    bible = generate.load_bible(channel)
    eps = _arc_episodes(channel, arc)
    if not eps:
        raise SystemExit(f"no flow-film episodes for arc {arc} in {channel}")
    voices = {}
    for e in eps:
        for c, v in e.get("voices", {}).items():
            voices.setdefault(c, v)
    out = voices_dir(channel, arc)
    out.mkdir(parents=True, exist_ok=True)
    SPEND.update(tts_chars=0)
    data, used = {}, set()
    for c, v in voices.items():
        lines = [e2[k] for e in eps for e2 in e["edit"] for k in ("line", "vo") if e2.get(k) and e2[k]["c"] == c]
        ln = max(lines, key=lambda x: len(x["t"])) if lines else {"t": "This family will not be shamed.", "c": c}
        data[c] = {"short": _short(c), "brief": v.get("brief", ""), "line": ln["t"], "samples": []}
        pool = voice_pool(v.get("brief", ""), wide=True)
        pick = ([x for x in pool if x not in used] + pool)[:3]      # no two characters share a candidate
        used.update(pick)
        for k, name in enumerate(pick, 1):
            wav = tts_line(bible, ln, {"voice": name}, out / f"{_short(c)}_{k}_{name}.wav")
            mp3 = out / f"{_short(c)}_{k}.mp3"
            _ff("-i", wav, "-c:a", "libmp3lame", "-b:a", "128k", mp3)
            data[c]["samples"].append({"k": k, "voice": name, "endpoint": SPEND.get("endpoint", ""),
                                       "file": mp3.name})
            print(f"   {_short(c)} {k}: {name}  \"{ln['t']}\"")
    (out / "samples.json").write_text(_json.dumps(data, indent=1) + "\n")
    print(f"   COST voice samples: about ${SPEND['tts_chars'] / 1000 * PRICE_TTS_1K:.2f}"
          + (" (mock: $0)" if config.MOCK else ""))
    print(f"   -> {out}  then: python -m pipeline.run voices {channel} {arc} pick \"mama 2, tobi 1, ...\"")
    return out


def pick_voices(channel: str, arc: str, picks: str) -> dict:
    """Save "mama 2, tobi 1" into channel.json cast_voices as {voice, endpoint} (fixed for the whole arc)."""
    import json as _json
    data = _json.loads((voices_dir(channel, arc) / "samples.json").read_text())
    by_short = {d["short"]: c for c, d in data.items()}
    path = config.CHANNELS_DIR / channel / "channel.json"
    bible = _json.loads(path.read_text())
    cv = bible.setdefault("cast_voices", {})
    for name, k in re.findall(r"([A-Za-z][\w-]*)\s*[:=]?\s*(\d)", picks):
        c = by_short.get(name.lower())
        if not c:
            raise SystemExit(f"unknown character '{name}' (have: {', '.join(by_short)})")
        smp = next((x for x in data[c]["samples"] if x["k"] == int(k)), None)
        if not smp:
            raise SystemExit(f"{name} has no sample {k}")
        cv[c] = {"voice": smp["voice"], "endpoint": smp["endpoint"]}
        print(f"   {c} = {smp['voice']} ({smp['endpoint']})")
    missing = [d["short"] for c, d in data.items() if c not in cv]
    path.write_text(_json.dumps(bible, indent=2, ensure_ascii=False) + "\n")
    if missing:
        print(f"   still to pick: {', '.join(missing)}")
    return cv
