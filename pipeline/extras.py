"""Short daily "extra" formats for the Flow channels (free: Cloudflare images + our own music + ffmpeg).

  python -m pipeline.run extras [elders:finish cribcommittee:babymean ...]

  elders:finish            Finish the Elder's Sentence (~16 s)
  elders:thennow           Then vs Now, split screen (~24 s)
  cribcommittee:babymean   What Babies Really Mean (~22 s)

Content: channels/<ch>/extras.json (tools/generators/build_extras.py). Progress: state/extras.json, keyed
"<channel>:<format>". Text stays inside the Shorts safe zone (see pipeline/carousel.py).

QUOTA: every channel shares ONE Google project (about 6 uploads a day). Extras are the lowest priority, so the
scheduled run happens in the last two hours of the Pacific quota day (22:00-24:00 Los Angeles time), after the
main Shorts and carousels, and simply stops on "quotaExceeded" (the same script is tried again tomorrow).
Set EXTRAS_ANY_TIME=1 to skip the time window (manual tests).
"""
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

from . import assemble, carousel, config, engage, images, seo, youtube

W, H, FPS = carousel.W, carousel.H, carousel.FPS
STATE = config.ROOT / "state" / ("extras.mock.json" if config.MOCK else "extras.json")
CREAM = (255, 252, 245)


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"channels": {}}


def save_state(s):
    s["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n")


def load(ch):
    p = config.CHANNELS_DIR / ch / "extras.json"
    return json.loads(p.read_text()) if p.exists() else None


def jobs():
    """[(channel, format)]: each channel's priority list, taken in turns (elders first, then crib, then elders...)."""
    lists = []
    for p in sorted(config.CHANNELS_DIR.iterdir(), key=lambda p: (p.name != "elders", p.name)):
        cfg = load(p.name)
        if cfg:
            lists.append([(p.name, f) for f in cfg.get("priority", cfg["formats"])])
    out = []
    for i in range(max((len(x) for x in lists), default=0)):
        out += [x[i] for x in lists if i < len(x)]
    return out


# ---------------------------------------------------------------- drawing
def text_block(d, cfg, words, size, y, bold=True, width=carousel.WIN_W, line_gap=1.28):
    """Centred, wrapped, outlined text. words: list of (word, rgb). Returns the y below the block."""
    f = carousel._font(cfg, bold, size)
    lines, cur = [], []
    for w in words:
        trial = " ".join(x for x, _ in cur + [w])
        if cur and d.textlength(trial, font=f) > width:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    lh = int(size * line_gap)
    for ln in lines:
        x = (W - d.textlength(" ".join(w for w, _ in ln), font=f)) / 2
        for w, col in ln:
            d.text((x + 2, y + 4), w, font=f, fill=(0, 0, 0, 160))
            d.text((x, y), w, font=f, fill=col + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 210))
            x += d.textlength(w + " ", font=f)
        y += lh
    return y


def plain(text, col=CREAM):
    return [(w, col) for w in text.split()]


def save_layer(draw_fn, dest: Path):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    im.save(dest)
    return dest


def pill(d, cfg, text, x, y, fill):
    f = carousel._font(cfg, True, 44)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 48, y + 70], 35, fill=fill + (235,))
    d.text((x + 24, y + 9), text, font=f, fill=(20, 16, 24, 255))


# ---------------------------------------------------------------- video
def render(cfg, bg, layers, total, wd: Path, split=False):
    """bg: [(image, seconds)] full-screen Ken Burns with 0.8 s crossfades, or with split=True exactly two images
    stacked (top/bottom halves) for the whole video. layers: [(png, start, end)] full-frame RGBA overlays."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    fc = []
    if split:
        for p, _ in bg:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.2f}", "-i", str(p)]
        frames = int(total * FPS) + 2
        for j in range(2):
            fc.append(f"[{j}:v]scale=1600:1600,crop=1600:1422,zoompan=z='min(zoom+0.0005,1.1)':"
                      f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H // 2}:fps={FPS},setsar=1[h{j}]")
        fc.append("[h0][h1]vstack=inputs=2,format=yuv420p[bg]")
        k = 2
    else:
        segs = [s for _, s in bg]
        for (p, s) in bg:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{s:.3f}", "-i", str(p)]
        for j, (p, s) in enumerate(bg):
            zx = ["iw/2-(iw/zoom/2)", "0", "iw-iw/zoom"][j % 3]
            fc.append(f"[{j}:v]scale=2160:2160,crop=1215:2160,zoompan=z='min(zoom+0.0006,1.12)':x='{zx}':"
                      f"y='ih/2-(ih/zoom/2)':d={int(s * FPS)}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[s{j}]")
        last, off = "s0", 0.0
        for j in range(1, len(bg)):
            off += segs[j - 1] - 0.8
            fc.append(f"[{last}][s{j}]xfade=transition=fade:duration=0.8:offset={off:.3f}[x{j}]")
            last = f"x{j}"
        fc.append(f"[{last}]null[bg]")
        k = len(bg)
    cur = "bg"
    for i, (png, a, b) in enumerate(layers):
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(png)]
        fade = f",fade=t=in:st={a:.2f}:d=0.35:alpha=1" if a > 0 else ""
        fc.append(f"[{k + i}:v]format=rgba{fade}[l{i}]")
        fc.append(f"[{cur}][l{i}]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})':shortest=1[o{i}]")
        cur = f"o{i}"
    fc.append(f"[{cur}]format=yuv420p[v]")
    music = None
    for mood in cfg.get("music_moods", []) + ["default"]:
        music = assemble.find_music(mood)
        if music:
            break
    ai = k + len(layers)
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    fc.append(f"[{ai}:a]afade=t=in:st=0:d=0.8,afade=t=out:st={total - 1.5:.2f}:d=1.5,"
              f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11[a]")
    out = wd / "final.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("extras ffmpeg failed:\n" + r.stderr[-2000:])
    return out


def scrim(ccfg, fmt, subtitle, wd):
    lay = dict(ccfg, layout=dict(ccfg["layout"], header=fmt["header"]))
    return carousel.draw_base(lay, {"subtitle": subtitle, "theme": ""}, wd / "scrim.png")


def pool_images(ccfg, ch, key, n, count, st, wd):
    c = dict(ccfg, images_per_video=count)
    used = set(st.get("used_images", []))
    plan = carousel.image_prompts(c, f"{ch}-{key}", n, used)
    st["used_images"] = sorted(used)[-2000:]
    return [images.generate(p["prompt"], p["seed"], wd / f"img{j + 1}.jpg") for j, p in enumerate(plan)]


# ---------------------------------------------------------------- the three formats
def make_finish(ch, ccfg, fmt, ep, n, st, wd):
    acc = carousel._hex(ccfg["layout"]["accent"])
    total = float(fmt.get("duration", 16))
    img = pool_images(ccfg, ch, "finish", n, 1, st, wd)
    reveal = 9.0
    L = [(scrim(ccfg, fmt, fmt["subtitle"], wd), 0.0, total)]
    L.append((save_layer(lambda d: (text_block(d, ccfg, plain(ep["start"]), 64, 470),
                                    text_block(d, ccfg, [("_______", acc)], 64, 760)), wd / "q.png"), 0.4, reveal))
    for i, num in enumerate("321"):
        t = reveal - 3 + i
        L.append((save_layer(lambda d, num=num: text_block(d, ccfg, [(num, acc)], 150, 900), wd / f"c{num}.png"),
                  t, t + 0.95))
    words = plain(ep["start"]) + plain(ep["end"], acc)
    L.append((save_layer(lambda d: text_block(d, ccfg, words, 62, 470), wd / "a.png"), reveal, total))
    L.append((save_layer(lambda d: text_block(d, ccfg, plain(fmt["cta"], acc), 44, 1110, bold=False),
                         wd / "cta.png"), reveal + 2.0, total))
    return render(ccfg, [(img[0], total)], L, total, wd)


def make_babymean(ch, ccfg, fmt, ep, n, st, wd):
    acc = carousel._hex(ccfg["layout"]["accent"])
    imgs = pool_images(ccfg, ch, "babymean", n, 3, st, wd)
    segs = [7.6, 7.6, 8.4]
    total = sum(segs) - 0.8 * 2
    L = [(scrim(ccfg, fmt, ep["topic"], wd), 0.0, total)]
    t0 = 0.0
    for i, ((when, mean), seg) in enumerate(zip(ep["pairs"], segs)):
        start = t0 + (0.3 if i == 0 else 0.5)
        end = t0 + seg - 0.8 if i < 2 else total
        L.append((save_layer(lambda d, w=when: text_block(d, ccfg, plain(w), 60, 480), wd / f"w{i}.png"), start, end))
        L.append((save_layer(lambda d, m=mean: (text_block(d, ccfg, plain("I really mean:", acc), 44, 790, bold=False),
                                                text_block(d, ccfg, plain(m), 62, 860)), wd / f"m{i}.png"),
                  start + 2.4, end))
        t0 += seg - 0.8
    L.append((save_layer(lambda d: text_block(d, ccfg, plain(fmt["cta"], acc), 46, 1130), wd / "cta.png"),
              total - 3.2, total))
    return render(ccfg, list(zip(imgs, segs)), L, total, wd)


def make_thennow(ch, ccfg, fmt, ep, n, st, wd):
    acc = carousel._hex(ccfg["layout"]["accent"])
    total = float(fmt.get("duration", 24))
    then = images.generate(fmt["image_then"].format(scene=ep["then_img"]), 1000 + n, wd / "then.jpg")
    now = images.generate(fmt["image_now"].format(scene=ep["now_img"]), 2000 + n, wd / "now.jpg")

    def labels(d):
        pill(d, ccfg, "THEN", 150, 330, (232, 210, 170))
        pill(d, ccfg, "NOW", 150, 985, acc)
        d.line([(0, H // 2), (W, H // 2)], fill=(255, 255, 255, 230), width=6)
    L = [(scrim(ccfg, fmt, ep["topic"], wd), 0.0, total), (save_layer(labels, wd / "labels.png"), 0.0, total - 6)]
    for i, (a, b) in enumerate(ep["pairs"]):
        s, e = 0.5 + i * 6, 0.5 + (i + 1) * 6
        L.append((save_layer(lambda d, a=a: text_block(d, ccfg, plain(a), 54, 690), wd / f"t{i}.png"), s, e))
        L.append((save_layer(lambda d, b=b: text_block(d, ccfg, plain(b), 54, 1085), wd / f"n{i}.png"), s + 1.2, e))

    def lesson(d):
        d.rectangle([0, 0, W, H], fill=(8, 6, 12, 150))
        y = text_block(d, ccfg, plain("The lesson:", acc), 46, 560, bold=False)
        y = text_block(d, ccfg, plain(ep["lesson"]), 64, y + 20)
        text_block(d, ccfg, plain(fmt["cta"], acc), 44, max(y + 60, 1060), bold=False)
    L.append((save_layer(lesson, wd / "lesson.png"), total - 5.5, total))
    return render(ccfg, [(then, total), (now, total)], L, total, wd, split=True)


MAKERS = {"finish": make_finish, "babymean": make_babymean, "thennow": make_thennow}


# ---------------------------------------------------------------- metadata + run
def metadata(ch, fmt_name, fmt, ep, bible):
    title = fmt["title_template"].format(**ep)
    if len(title) > 100:
        title = title[:96].rsplit(" ", 1)[0] + "... #shorts"
    if fmt_name == "finish":
        body = f"\"{ep['start']} ...\"\n\nThe answer: \"{ep['start']} {ep['end']}\""
    elif fmt_name == "thennow":
        body = "\n".join(f"THEN: {a}  NOW: {b}" for a, b in ep["pairs"]) + f"\n\nThe lesson: {ep['lesson']}"
    else:
        body = "\n".join(f"{a} {b}" for a, b in ep["pairs"])
    tags = [ep["theme"]] + fmt.get("tags", [])
    ccfg = carousel.load_cfg(ch)
    desc = (f"{fmt.get('intro', '')}\n\n{body}\n\n{fmt.get('cta', '')}\n\n"
            + (f"{seo.about(bible)}\n\n" if seo.about(bible) else "")
            + f"{ccfg.get('ai_disclosure', bible.get('ai_disclosure', config.AI_DISCLOSURE))}\n\n"
            + seo.hashtag_line(bible, tags))
    return {"title": title, "description": desc[:4900], "tags": seo.youtube_tags(bible, tags), "topic_tags": tags,
            "made_for_kids": bool(bible.get("made_for_kids", False))}


def in_window():
    from zoneinfo import ZoneInfo
    return os.environ.get("EXTRAS_ANY_TIME") == "1" or \
        dt.datetime.now(ZoneInfo("America/Los_Angeles")).hour >= 22


def run_one(s, ch, fmt_name, upload=True):
    cfg = load(ch)
    if cfg is None:
        raise RuntimeError(f"{ch}: channels/{ch}/extras.json not found")
    fmt = cfg["formats"][fmt_name]
    key = f"{ch}:{fmt_name}"
    st = s["channels"].setdefault(key, {"done": {}, "used_images": []})
    day = engage.pacific_day()
    if upload and any(r.get("day") == day and r.get("youtube_id") for r in st["done"].values()):
        print(f"   {key}: already posted for quota day {day} - skipped")
        return None
    eps = fmt["episodes"]
    used = {int(k.split("-")[-1]) - 1 for k in st["done"]}
    idx = engage.pick_episode(ch, eps, used)
    if idx is None:
        print(f"!! {key}: all {len(eps)} scripts used - add more in tools/generators/build_extras.py")
        return None
    ep, n = eps[idx], idx + 1
    ep_id = f"{fmt['id_prefix']}-{n:03d}"
    wd = config.OUTPUT / "extras" / ch / ep_id
    wd.mkdir(parents=True, exist_ok=True)
    print(f"\n== Extra {key} {ep_id}: {ep['theme']}")
    ccfg = carousel.load_cfg(ch)
    bible = json.loads((config.CHANNELS_DIR / ch / "channel.json").read_text())
    final = MAKERS[fmt_name](ch, ccfg, fmt, ep, n, st, wd)
    meta = metadata(ch, fmt_name, fmt, ep, bible)
    (wd / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    rec = {"theme": ep["theme"], "day": day, "seconds": round(assemble.duration(final), 2),
           "rendered": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if not upload:
        print(f"   -> {final} (upload off)")
        return final
    meta["publish_at"] = carousel.publish_time(dict(publish_local=fmt["publish_local"],
                                                    timezone=ccfg.get("timezone", "Europe/London")))
    res = youtube.upload(ch, final, meta)          # quotaExceeded raises -> nothing recorded, retried tomorrow
    rec.update(res)
    print(f"   -> https://youtu.be/{res['youtube_id']} (public at {res['publish_at']})")
    rec["meta"] = carousel.post_meta(ch, final, meta)
    st["done"][ep_id] = rec
    left = len(eps) - len(st["done"])
    if left < 7:
        print(f"!! {key}: only {left} scripts left - write the next batch soon")
    return final


def run(argv):
    upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
    if upload and not in_window():
        print("   extras: outside the 22:00-24:00 Los Angeles window (the quota day's leftovers) - nothing to do")
        return False
    s = load_state()
    todo = [tuple(a.split(":", 1)) for a in argv] if argv else jobs()
    failed = False
    for ch, fmt in todo:
        try:
            run_one(s, ch, fmt, upload=upload)
        except Exception as e:
            save_state(s)
            if youtube.is_quota_error(e):
                print(f"   {ch}:{fmt}: YouTube quota for today is used up - stopping here, the rest tries tomorrow")
                return False
            import traceback
            traceback.print_exc()
            print(f"!! {ch}:{fmt}: extra failed: {e}")
            failed = True
        save_state(s)
    return failed
