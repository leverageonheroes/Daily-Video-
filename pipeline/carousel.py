"""Second daily video per Flow channel: an image carousel with gently scrolling words + music + hook ending.

  python -m pipeline.run carousel [elders cribcommittee]

Content lives in channels/<ch>/carousel.json (series look, image prompt pools, 30 episodes of lines + hook).
Progress lives in state/carousel.json (separate from state/state.json, so the Railway worker and GitHub
Actions never edit the same file). Images come from free providers (pipeline/images.py).

Layout (1080x1920): full-screen images (slow Ken Burns, soft crossfades) under a dark scrim; header (series +
theme) at the top; the lines scroll up over the images inside the YouTube Shorts SAFE ZONE (y 380-1240,
x 150-930), clear of the title/channel/buttons that cover the bottom ~35% and the right edge; hook card last.
"""
import datetime as dt
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path

from . import assemble, config, engage, images, seo

W, H, FPS = 1080, 1920, 30
WIN_X, WIN_Y, WIN_W, WIN_H = 150, 380, 780, 860       # Shorts safe zone: nothing here is covered by the app UI
STATE = config.ROOT / "state" / ("carousel.mock.json" if config.MOCK else "carousel.json")
FONTS = {
    "serif": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    "sans": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
}
TRANSITIONS = ["fade", "dissolve", "smoothleft", "fade", "smoothup", "dissolve", "fade", "smoothright"]


# ---------------------------------------------------------------- state / content
def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"channels": {}}


def save_state(s):
    s["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2) + "\n")


def load_cfg(ch):
    return json.loads((config.CHANNELS_DIR / ch / "carousel.json").read_text())


def channels():
    env = os.environ.get("CAROUSEL_CHANNELS")
    if env:
        return [c.strip() for c in env.split(",") if c.strip()]
    return [p.name for p in sorted(config.CHANNELS_DIR.iterdir()) if (p / "carousel.json").exists()]


# ---------------------------------------------------------------- image prompts
def image_prompts(cfg, ch, n, used: set):
    ip = cfg["image_prompt"]
    pools, uniq = ip["pools"], set(ip.get("unique_per_video", []))
    out: list[dict] = []
    taken: dict[str, set] = {k: set() for k in uniq}
    for k in range(cfg.get("images_per_video", 8)):
        pick: dict = {}
        prompt = h = ""
        for attempt in range(50):
            rnd = random.Random(f"{ch}-{n}-{k}-{attempt}")
            pick = {}
            for key, vals in pools.items():
                choices = [v for v in vals if v not in taken.get(key, ())] or vals
                pick[key] = rnd.choice(choices)
            prompt = ip["template"].format(**pick)
            h = hashlib.sha1(prompt.encode()).hexdigest()[:12]
            if h not in used:
                break
        for key in uniq:
            taken[key].add(pick[key])
        used.add(h)
        out.append({"prompt": prompt, "hash": h, "seed": int(h[:7], 16)})
    return out


# ---------------------------------------------------------------- drawing (Pillow)
def _font(cfg, bold, size):
    from PIL import ImageFont
    reg, bld = FONTS.get(cfg["layout"].get("font", "serif"), FONTS["serif"])
    return ImageFont.truetype(bld if bold else reg, size)


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def draw_base(cfg, ep, dest: Path):
    """Transparent overlay: dark scrim (stronger at the top and behind the text zone) + header + divider."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    lay = cfg["layout"]
    shade = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(shade)
    for y in range(H):
        a = 95                                                   # whole frame ~37% darker
        if y < 420:
            a += int(120 * (1 - y / 420))                        # header readable
        if y > 1500:
            a += int(90 * (y - 1500) / (H - 1500))               # app UI readable
        d.line([(0, y), (W, y)], fill=min(a, 235))
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).rounded_rectangle([WIN_X - 40, WIN_Y - 30, WIN_X + WIN_W + 40, WIN_Y + WIN_H + 30],
                                           60, fill=70)
    band = band.filter(ImageFilter.GaussianBlur(40))
    alpha = ImageChops.add(shade, band)                          # extra darkening behind the scrolling words
    im = Image.new("RGBA", (W, H), (8, 6, 12, 0))
    im.putalpha(alpha)
    d = ImageDraw.Draw(im)
    acc = _hex(lay["accent"])
    f1, f2 = _font(cfg, True, 40), _font(cfg, True, 74)
    head = lay["header"]
    sub = ep.get("subtitle") or f"on {ep['theme'].title()}"
    for text, f, y, col in ((head, f1, 150, acc), (sub, f2, 202, (250, 246, 238))):
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=col + (255,),
               stroke_width=3, stroke_fill=(0, 0, 0, 170))
    d.line([(W / 2 - 90, WIN_Y - 40), (W / 2 + 90, WIN_Y - 40)], fill=acc + (255,), width=3)
    im.save(dest)
    return dest


def draw_text_strip(cfg, ep, dest: Path):
    """Tall transparent PNG with every line, wrapped, separated by a small accent dot."""
    from PIL import Image, ImageDraw
    f = _font(cfg, cfg["layout"].get("lines_bold", False), cfg["layout"].get("line_size", 50))
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    blocks, lh, gap = [], int(f.size * 1.32), int(f.size * 1.6)
    for line in ep["lines"]:
        blocks.append(_wrap(probe, line, f, WIN_W - 40))
    height = sum(len(b) * lh for b in blocks) + gap * (len(blocks) - 1) + 20
    im = Image.new("RGBA", (WIN_W, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    acc = _hex(cfg["layout"]["accent"])
    y = 0
    for i, b in enumerate(blocks):
        for ln in b:
            x = (WIN_W - d.textlength(ln, font=f)) / 2
            d.text((x + 2, y + 4), ln, font=f, fill=(0, 0, 0, 170))      # soft shadow
            d.text((x, y), ln, font=f, fill=(255, 252, 245, 255), stroke_width=3, stroke_fill=(0, 0, 0, 200))
            y += lh
        if i < len(blocks) - 1:
            cy = y + (gap - lh) // 2 + lh // 2 - 6
            d.ellipse([WIN_W / 2 - 6, cy - 6, WIN_W / 2 + 6, cy + 6], fill=acc + (255,))
            y += gap
    im.save(dest)
    return dest, height


def draw_hook(cfg, ep, dest: Path):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    big, small = _font(cfg, True, 62), _font(cfg, False, 44)
    acc = _hex(cfg["layout"]["accent"])
    lines = _wrap(d, ep["hook"], big, WIN_W - 20)
    cta = _wrap(d, cfg.get("cta", ""), small, WIN_W - 20)
    total = len(lines) * 78 + (len(cta) * 58 + 30 if cta else 0)
    y = WIN_Y + (WIN_H - total) / 2
    for ln in lines:
        d.text(((W - d.textlength(ln, font=big)) / 2, y), ln, font=big, fill=(255, 252, 245, 255),
               stroke_width=3, stroke_fill=(0, 0, 0, 200))
        y += 78
    y += 30
    for ln in cta:
        d.text(((W - d.textlength(ln, font=small)) / 2, y), ln, font=small, fill=acc + (255,),
               stroke_width=2, stroke_fill=(0, 0, 0, 200))
        y += 58
    im.save(dest)
    return dest


def draw_masks(workdir: Path):
    from PIL import Image, ImageDraw
    g = Image.new("L", (WIN_W, WIN_H), 255)
    dg = ImageDraw.Draw(g)
    edge = 90
    for i in range(edge):
        v = int(255 * i / edge)
        dg.line([(0, i), (WIN_W, i)], fill=v)
        dg.line([(0, WIN_H - 1 - i), (WIN_W, WIN_H - 1 - i)], fill=v)
    g.save(workdir / "mask_fade.png")


# ---------------------------------------------------------------- video
def render(cfg, ep, imgs: list, workdir: Path) -> Path:
    total = float(cfg.get("duration", 66))
    hook_s = float(cfg.get("hook_seconds", 8))
    scroll_s = total - hook_s
    n = len(imgs)
    seg = (total + (n - 1)) / n                 # 1 s crossfades
    base = draw_base(cfg, ep, workdir / "base.png")
    strip, sh = draw_text_strip(cfg, ep, workdir / "text.png")
    hook = draw_hook(cfg, ep, workdir / "hook.png")
    draw_masks(workdir)
    speed = (WIN_H + sh) / (scroll_s - 0.5)

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(base)]
    for p in imgs:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{seg:.3f}", "-i", str(p)]
    k = n + 1
    cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(strip),
            "-loop", "1", "-framerate", str(FPS), "-i", str(hook),
            "-loop", "1", "-framerate", str(FPS), "-i", str(workdir / "mask_fade.png")]
    i_txt, i_hook, i_fade = k, k + 1, k + 2
    frames = int(seg * FPS)
    fc = []
    for j in range(n):
        zx = ["iw/2-(iw/zoom/2)", "0", "iw-iw/zoom", "iw/2-(iw/zoom/2)"][j % 4]
        zy = ["ih/2-(ih/zoom/2)", "ih/2-(ih/zoom/2)", "ih/2-(ih/zoom/2)", "0"][j % 4]
        # square source -> fill the whole 9:16 frame (centre crop), then slow Ken Burns
        fc.append(f"[{j + 1}:v]scale=2160:2160,crop=1215:2160,zoompan=z='min(zoom+0.0006,1.12)':x='{zx}':y='{zy}':"
                  f"d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[s{j}]")
    last = "s0"
    for j in range(1, n):
        off = j * (seg - 1)
        tr = TRANSITIONS[(j - 1) % len(TRANSITIONS)]
        fc.append(f"[{last}][s{j}]xfade=transition={tr}:duration=1:offset={off:.3f}[x{j}]")
        last = f"x{j}"
    fc.append(f"[0:v]format=rgba[scrim];[{last}][scrim]overlay=0:0:shortest=1[v1]")
    # scroll the (transparent) text layer itself: pad it with empty space, slide a window down it over time,
    # then fade its alpha at the window's top and bottom edges
    fc.append(f"[{i_txt}:v]format=rgba,pad={WIN_W}:ih+{2 * WIN_H}:0:{WIN_H}:color=black@0,"
              f"crop={WIN_W}:{WIN_H}:0:'min(t*{speed:.3f},ih-{WIN_H})'[tw]")
    fc.append(f"[tw]split[tc][ta];[ta]alphaextract[a1];[{i_fade}:v]format=gray,scale={WIN_W}:{WIN_H}[fm];"
              f"[a1][fm]blend=all_mode=multiply[a2];[tc][a2]alphamerge[tf]")
    fc.append(f"[v1][tf]overlay={WIN_X}:{WIN_Y}:enable='lt(t,{scroll_s + 0.5:.2f})'[v2]")
    fc.append(f"[{i_hook}:v]format=rgba,fade=t=in:st={scroll_s:.2f}:d=0.9:alpha=1[hk]")
    fc.append(f"[v2][hk]overlay=0:0:enable='gte(t,{scroll_s - 0.1:.2f})',format=yuv420p[v]")

    music = None
    for mood in cfg.get("music_moods", []) + ["default"]:
        music = assemble.find_music(mood)
        if music:
            break
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music.resolve())]
        af = f"[{i_fade + 1}:a]"
    else:   # fallback: a soft major-chord pad so the video is never silent
        print("   (no music file found in music/ - using a soft synthesised pad; add real tracks!)")
        cmd += ["-f", "lavfi", "-i",
                "aevalsrc='0.06*sin(2*PI*196*t)+0.05*sin(2*PI*246.94*t)+0.05*sin(2*PI*293.66*t)"
                "+0.03*sin(2*PI*392*t)':s=48000:c=stereo"]
        af = f"[{i_fade + 1}:a]tremolo=f=0.25:d=0.35,lowpass=f=1800,"
    af += (f"afade=t=in:st=0:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5,"
           f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11[a]")
    fc.append(af)
    out = workdir / "final.mp4"
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("carousel ffmpeg failed:\n" + r.stderr[-2000:])
    return out


def add_end_card(final: Path, bible: dict, wd: Path) -> Path:
    """Append the channel's end card (channel.json end_card image, same as the main Shorts) to the carousel."""
    card, sec = assemble.end_card(bible, wd)
    if not card:
        return final
    tmp = wd / "final_card.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-i", str(card), "-filter_complex",
                    f"[0:v]fps={FPS},setsar=1[v0];[1:v]scale={W}:{H},fps={FPS},setsar=1[v1];"
                    "[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
                    "[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
                    "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(final)
    print(f"   end card added ({sec:.0f} s)")
    return final


def post_meta(ch, final: Path, meta: dict) -> dict:
    """Facebook + Instagram Stories and Reels (feed) for the carousel too. Never blocks the YouTube upload."""
    from . import meta as fbig
    if not fbig.enabled(ch):
        print(f"   (no Meta token/page IDs for {ch}: Facebook/Instagram skipped)")
        return {}
    try:
        ep = {"title": meta["title"], "description": meta["description"], "shots": [],
              "tags": meta.get("topic_tags") or meta.get("tags", [])}
        res = fbig.post_stories(ch, final, ep, assemble.duration(final), {})
    except Exception as e:
        print(f"!! {ch}: Facebook/Instagram failed: {e}")
        return {"errors": [str(e)[:300]]}
    for err in res.get("errors", []):
        print(f"!! {ch}: {err}")
    return res


# ---------------------------------------------------------------- publishing
def publish_time(cfg) -> str:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(cfg.get("timezone", "Europe/London"))
    hh, mm = (int(x) for x in cfg.get("publish_local", "13:30").split(":"))
    now = dt.datetime.now(tz)
    when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if when < now + dt.timedelta(minutes=45):
        when += dt.timedelta(days=1)
    return when.astimezone(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def metadata(cfg, ep, bible):
    title = cfg["title_template"].format(theme=ep["theme"].title(), title=ep.get("title", ""))[:100]
    body = "\n".join(f"• {l}" for l in ep["lines"])
    tags = ep.get("tags", []) + cfg.get("tags", [])
    desc = (f"{cfg.get('intro', '')} {ep['theme'].title()}.\n\n{body}\n\n{ep['hook']} {cfg.get('cta', '')}\n\n"
            + (f"{seo.about(bible)}\n\n" if seo.about(bible) else "")
            + f"{cfg.get('ai_disclosure', bible.get('ai_disclosure', config.AI_DISCLOSURE))}\n\n"
            + seo.hashtag_line(bible, tags))
    return {"title": title, "description": desc[:4900], "tags": seo.youtube_tags(bible, tags), "topic_tags": tags,
            "made_for_kids": bool(bible.get("made_for_kids", False))}


def run_channel(s, ch, upload=True):
    cfg = load_cfg(ch)
    bible = json.loads((config.CHANNELS_DIR / ch / "channel.json").read_text())
    st = s["channels"].setdefault(ch, {"next": 1, "done": {}, "used_images": []})
    eps = cfg["episodes"]
    used = {int(k.split("-")[-1]) - 1 for k in st["done"]}
    idx = engage.pick_episode(ch, eps, used)       # best-performing theme among the next 5 unused scripts
    if idx is None:
        print(f"!! {ch}: all {len(eps)} carousel episodes are used - write the next batch (CLAUDE.md)")
        return None
    n = idx + 1
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if upload and os.environ.get("YT_PUBLISH_NOW") != "1" and \
            any(r.get("rendered", "").startswith(today) and r.get("youtube_id") for r in st["done"].values()):
        # guard: two schedulers (GitHub + an old Railway cron) must never post the same channel twice a day
        print(f"   {ch}: a carousel was already uploaded today ({today}) - skipped")
        return None
    ep = eps[n - 1]
    ep_id = f"{cfg['id_prefix']}-{n:03d}"
    wd = config.OUTPUT / "carousel" / ch / ep_id
    wd.mkdir(parents=True, exist_ok=True)
    print(f"\n== Carousel {ch} {ep_id}: {ep['theme']}")
    used = set(st.get("used_images", []))
    plan = image_prompts(cfg, ch, n, used)
    paths = []
    for j, p in enumerate(plan):
        print(f"   image {j + 1}/{len(plan)}")
        paths.append(images.generate(p["prompt"], p["seed"], wd / f"img{j + 1:02d}.jpg"))
    final = add_end_card(render(cfg, ep, paths, wd), bible, wd)
    meta = metadata(cfg, ep, bible)
    (wd / "metadata.json").write_text(json.dumps(meta, indent=2))
    (wd / "prompts.json").write_text(json.dumps(plan, indent=2))
    rec = {"theme": ep["theme"], "rendered": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "seconds": round(assemble.duration(final), 2)}
    if upload:
        from . import youtube
        if os.environ.get("YT_PUBLISH_NOW") != "1":      # YT_PUBLISH_NOW=1: public straight away (catch-up runs)
            meta["publish_at"] = publish_time(cfg)
        res = youtube.upload(ch, final, meta)
        rec.update(res)
        print(f"   -> https://youtu.be/{res['youtube_id']} (public at {res['publish_at']})")
        rec["meta"] = post_meta(ch, final, meta)
    else:
        print(f"   -> {final} (upload off)")
    st["done"][ep_id] = rec
    st["used_images"] = sorted(used)[-2000:]
    st["next"] = len(st["done"]) + 1
    left = len(eps) - len(st["done"])
    if left < 7:
        print(f"!! {ch}: only {left} carousel episodes left - write the next batch soon")
    return final


def run(argv):
    upload = os.environ.get("YT_UPLOAD", "1") == "1" and not config.MOCK
    s = load_state()
    failed = False
    for ch in argv or channels():
        try:
            run_channel(s, ch, upload=upload)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"!! {ch}: carousel failed: {e}")
            failed = True
        save_state(s)
    return failed
