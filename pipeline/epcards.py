"""Story-arc episode cards (Moral Of The Story TV): free, made with Pillow + ffmpeg from the episode's own clips.

  thumbnail.jpg  1080x1920 poster: show badge, EPISODE N, arc title, part title, hook line (also the first frame)
  title card     the thumbnail as a 2.5 s opening clip (slow push-in, whoosh)
  brief card     part 1 only: "THE STORY" - arc logline + the cast (faces cut from the clips)
  next card      end of the Short: NEXT · EPISODE N+1 + its hook, then LIKE / SHARE / SUBSCRIBE pop in
                 (finale: "THE FULL MOVIE · IN 24 HOURS")

channel.json "episode_cards": {"title_seconds": 2.5, "brief_seconds": 6.5, "next_seconds": 5.0, "brief_parts": [1]}
An episode can pick its pictures: "cards": {"thumb_clip": 2, "brief_clip": 1, "next_clip": 15}.
Order in final.mp4: title -> brief (part 1) or PREVIOUSLY recap (parts 2+) -> story -> next card.
clean.mp4 (movies / compilations) never has cards.
"""
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config, state

W, H, FPS = 1080, 1920, 30
FONTS = config.ROOT / "assets" / "fonts"
GOLD = (236, 190, 92)
GOLD_DK = (160, 112, 38)
RED = (214, 32, 39)
WHITE = (255, 255, 255)


def font(name: str, size: int, weight: int | None = None):
    for p in (FONTS / name, Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
        if p.exists():
            f = ImageFont.truetype(str(p), size)
            if weight:
                try:
                    f.set_variation_by_axes([weight])
                except Exception:
                    pass
            return f
    return ImageFont.load_default()


def anton(size):
    return font("Anton-Regular.ttf", size)


def oswald(size, weight=600):
    return font("Oswald.ttf", size, weight)


def playfair(size, weight=700):
    return font("PlayfairDisplay.ttf", size, weight)


def _ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


# ---------------------------------------------------------------- pictures

def grab(clip: Path, dest: Path, at: float | None = None) -> Image.Image:
    """A frame of a clip (default: 40 % in). Cached as PNG."""
    if not dest.exists():
        if at is None:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(clip)], capture_output=True, text=True).stdout.strip()
            at = max(float(out or 2) * 0.4, 0)
        _ff("-ss", f"{at:.2f}", "-i", clip, "-frames:v", "1", dest)
    return Image.open(dest).convert("RGB")


def cover(img: Image.Image, w=W, h=H, focus_y=0.4) -> Image.Image:
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = int(max(min((img.height - h) * focus_y, img.height - h), 0))
    return img.crop((x, y, x + w, y + h))


def grade(img: Image.Image, dark=0.0) -> Image.Image:
    """Warm/teal film grade + vignette, optionally darkened."""
    from PIL import ImageEnhance
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.08)
    vig = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(vig)
    d.ellipse((-img.width * 0.35, -img.height * 0.2, img.width * 1.35, img.height * 1.2), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(img.width // 5))
    black = Image.new("RGB", img.size, (0, 0, 0))
    img = Image.composite(img, black, vig.point(lambda v: int(v * (1 - dark) + 255 * 0.0)))
    return img


def gradient(img: Image.Image, top: float, bottom: float, start=0.45, top_end=0.18) -> Image.Image:
    """Dark gradient from `start` (fraction of height) down to the bottom, and a light one at the top."""
    ov = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(ov)
    for y in range(img.height):
        f = y / img.height
        a = 0.0
        if f > start:
            a = bottom * min((f - start) / (1 - start) * 1.6, 1.0)
        if f < top_end:
            a = max(a, top * (1 - f / top_end))
        d.line([(0, y), (img.width, y)], fill=int(a * 255))
    return Image.composite(Image.new("RGB", img.size, (6, 4, 3)), img, ov)


def face_box(img: Image.Image):
    """Biggest face (x, y, w, h) via YuNet, or None."""
    try:
        import cv2
        import numpy as np
        from .faces import MODEL
        if not MODEL.exists():
            return None
        a = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        det = cv2.FaceDetectorYN.create(str(MODEL), "", (a.shape[1], a.shape[0]), 0.7, 0.3, 5000)
        _, found = det.detect(a)
        if found is None or not len(found):
            return None
        f = max(found, key=lambda r: r[2] * r[3])
        return tuple(int(v) for v in f[:4])
    except Exception:
        return None


def portrait(img: Image.Image, size: int) -> Image.Image:
    """Round head-and-shoulders crop with a gold ring."""
    b = face_box(img)
    if b:
        x, y, w, h = b
        cx, cy, side = x + w / 2, y + h * 0.55, max(w, h) * 2.1
    else:
        cx, cy, side = img.width / 2, img.height * 0.35, img.width * 0.6
    side = min(side, img.width, img.height)
    l = min(max(cx - side / 2, 0), img.width - side)
    t = min(max(cy - side / 2, 0), img.height - side)
    face = img.crop((int(l), int(t), int(l + side), int(t + side))).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    ring = size + 16
    out = Image.new("RGBA", (ring, ring), (0, 0, 0, 0))
    big = Image.new("L", (ring * 4, ring * 4), 0)
    ImageDraw.Draw(big).ellipse((0, 0, ring * 4 - 1, ring * 4 - 1), fill=255)
    out.paste(Image.new("RGBA", (ring, ring), GOLD + (255,)), (0, 0), big.resize((ring, ring), Image.LANCZOS))
    out.paste(face, (8, 8), mask)
    return out


# ---------------------------------------------------------------- text helpers

def tw(d, text, f):
    b = d.textbbox((0, 0), text, font=f)
    return b[2] - b[0], b[3] - b[1], b[1]


def fit(d, text, maker, start, max_w, min_size=40):
    size = start
    while size > min_size and tw(d, text, maker(size))[0] > max_w:
        size -= 4
    return maker(size)


def centred(d, y, text, f, fill, shadow=True, stroke=0, stroke_fill=(0, 0, 0), spacing=0):
    if spacing:
        text = (" " * 0).join(text)
    w, h, off = tw(d, text, f)
    x = (W - w) / 2
    if shadow:
        d.text((x + 4, y + 6 - off), text, font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
    d.text((x, y - off), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return y + h


def tracked(d, y, text, f, fill, track=8):
    """Letter-spaced line, centred."""
    widths = [tw(d, ch, f)[0] if ch != " " else tw(d, "n", f)[0] for ch in text]
    total = sum(widths) + track * (len(text) - 1)
    x = (W - total) / 2
    h = tw(d, "H", f)[1]
    off = tw(d, "H", f)[2]
    for ch, w in zip(text, widths):
        d.text((x, y - off), ch, font=f, fill=fill)
        x += w + track
    return y + h


def gold_text(base: Image.Image, y, text, f, stroke=3):
    """Big title with a vertical gold gradient fill, dark stroke and drop shadow."""
    d = ImageDraw.Draw(base)
    w, h, off = tw(d, text, f)
    x = int((W - w) / 2)
    pad = 40
    mask = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    ImageDraw.Draw(mask).text((pad, pad - off), text, font=f, fill=255)
    shadow = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.9)))
    base.paste(shadow, (x - pad + 6, y - pad + 10), shadow)
    d.text((x, y - off), text, font=f, fill=(0, 0, 0), stroke_width=stroke + 3, stroke_fill=(20, 10, 0))
    grad = Image.new("RGB", mask.size)
    gd = ImageDraw.Draw(grad)
    for yy in range(mask.height):
        t = yy / mask.height
        c = tuple(int(a + (b - a) * t) for a, b in zip((255, 236, 170), GOLD_DK))
        if 0.45 < t < 0.52:
            c = tuple(min(v + 30, 255) for v in c)
        gd.line([(0, yy), (mask.width, yy)], fill=c)
    base.paste(grad, (x - pad, y - pad), mask)
    return y + h


def pill(d, cx, cy, text, f, bg, fg=WHITE, padx=44, h=104, icon=None):
    w, th, off = tw(d, text, f)
    iw = 70 if icon else 0
    total = w + padx * 2 + iw
    x0, y0 = cx - total / 2, cy - h / 2
    d.rounded_rectangle((x0 + 4, y0 + 8, x0 + total + 4, y0 + h + 8), radius=h / 2, fill=(0, 0, 0))
    d.rounded_rectangle((x0, y0, x0 + total, y0 + h), radius=h / 2, fill=bg)
    if icon:
        icon(d, x0 + padx + 24, cy, fg)
    d.text((x0 + padx + iw, cy - th / 2 - off), text, font=f, fill=fg)


def icon_thumb(d, cx, cy, c):
    d.rounded_rectangle((cx - 26, cy - 6, cx - 14, cy + 26), radius=3, fill=c)          # cuff
    d.rounded_rectangle((cx - 10, cy - 6, cx + 26, cy + 26), radius=8, fill=c)          # hand
    d.polygon([(cx - 8, cy - 4), (cx + 2, cy - 30), (cx + 12, cy - 28), (cx + 10, cy - 4)], fill=c)  # thumb


def icon_share(d, cx, cy, c):
    d.polygon([(cx + 4, cy - 26), (cx + 30, cy), (cx + 4, cy + 26), (cx + 4, cy + 12),
               (cx - 22, cy + 14), (cx - 28, cy + 24), (cx - 28, cy + 8), (cx - 14, cy - 10), (cx + 4, cy - 12)], fill=c)


def icon_bell(d, cx, cy, c):
    d.pieslice((cx - 22, cy - 26, cx + 22, cy + 18), 180, 360, fill=c)
    d.rectangle((cx - 22, cy - 4, cx + 22, cy + 16), fill=c)
    d.polygon([(cx - 30, cy + 20), (cx + 30, cy + 20), (cx + 22, cy + 10), (cx - 22, cy + 10)], fill=c)
    d.ellipse((cx - 7, cy + 20, cx + 7, cy + 32), fill=c)


# ---------------------------------------------------------------- the three cards

def _badge(img, show):
    d = ImageDraw.Draw(img)
    f = oswald(40, 600)
    y = 150
    tracked(d, y, show.upper(), f, GOLD, track=7)
    d.line((W / 2 - 220, y + 66, W / 2 + 220, y + 66), fill=GOLD, width=3)
    d.polygon([(W / 2, y + 58), (W / 2 + 9, y + 66), (W / 2, y + 74), (W / 2 - 9, y + 66)], fill=GOLD)


def thumbnail(ep: dict, bg: Image.Image, show: str) -> Image.Image:
    img = gradient(grade(cover(bg, focus_y=0.25)), top=0.75, bottom=0.97, start=0.36, top_end=0.2)
    _badge(img, show)
    d = ImageDraw.Draw(img)
    y = 1015
    pill(d, W / 2, y + 52, f"EPISODE {ep.get('part', ep['number'])}", anton(66), RED, padx=56, h=118)
    y += 150
    title = ep.get("arc_title", ep["title"]).upper()
    words = title.split()
    lines = [title] if len(words) < 3 else [" ".join(words[:len(words) // 2]), " ".join(words[len(words) // 2:])]
    for ln in lines:
        y = gold_text(img, y, ln, fit(d, ln, anton, 200, W - 110)) + 26
    d = ImageDraw.Draw(img)
    if ep.get("part_title"):
        y = tracked(d, y + 14, f"PART {ep.get('part')} · {ep['part_title'].upper()}", oswald(42, 500), WHITE, 5) + 40
    hook = f"“{ep['hook_text'].strip()}”"
    f = playfair(58, 700)
    for ln in textwrap.wrap(hook, 24):
        y = centred(d, y, ln, f, (255, 244, 225)) + 16
    return img


def brief(ep: dict, bg: Image.Image, cast: list, show: str) -> Image.Image:
    img = cover(bg).filter(ImageFilter.GaussianBlur(18))
    img = Image.blend(img, Image.new("RGB", img.size, (8, 6, 4)), 0.72)
    img = grade(img)
    _badge(img, show)
    d = ImageDraw.Draw(img)
    y = 380
    y = tracked(d, y, "THE STORY", oswald(46, 600), GOLD, 12) + 40
    t = ep.get("arc_title", "").upper()
    y = gold_text(img, y, t, fit(d, t, anton, 150, W - 120)) + 60
    d = ImageDraw.Draw(img)
    f = playfair(54, 500)
    for ln in textwrap.wrap(ep.get("arc_logline", ep["logline"]), 30):
        y = centred(d, y, ln, f, (250, 242, 228)) + 18
    if cast:
        y += 60
        y = tracked(d, y, "MEET THE FAMILY", oswald(38, 600), GOLD, 9) + 40
        size = 190 if len(cast) <= 4 else 168
        n = len(cast)
        rows = [cast[:3], cast[3:]] if n > 4 else [cast]
        for row in rows:
            step = (size + 16) + 40
            x0 = W / 2 - (len(row) * step - 40) / 2
            for k, (name, pic) in enumerate(row):
                p = portrait(pic, size)
                x = int(x0 + k * step)
                img.paste(p, (x, int(y)), p)
                nf = fit(d, name, lambda s: oswald(s, 600), 38, size + 30, 24)
                w, _, off = tw(d, name, nf)
                d.text((x + (size + 16 - w) / 2, y + size + 30 - off), name, font=nf, fill=WHITE)
            y += size + 100
    d.text((0, 0), "", font=f)
    parts = ep.get("parts_total", 6)
    tracked(d, 1690, f"{parts} PARTS · FULL MOVIE AFTER THE FINALE", oswald(38, 500), (225, 215, 200), 5)
    return img


def next_card(ep: dict, nxt: dict | None, bg: Image.Image, show: str, stage: int) -> Image.Image:
    """stage 0: next-episode teaser only; 1..3: + LIKE, + SHARE, + SUBSCRIBE."""
    img = cover(bg).filter(ImageFilter.GaussianBlur(10))
    img = Image.blend(img, Image.new("RGB", img.size, (8, 6, 4)), 0.62)
    img = grade(img)
    _badge(img, show)
    d = ImageDraw.Draw(img)
    y = 420
    if nxt:
        pill(d, W / 2, y + 50, f"NEXT · EPISODE {nxt.get('part', nxt['number'])}", anton(60), RED, padx=52, h=112)
        y += 170
        t = (nxt.get("part_title") or "").upper()
        if t:
            y = gold_text(img, y, t, fit(d, t, anton, 170, W - 120)) + 50
            d = ImageDraw.Draw(img)
        for ln in textwrap.wrap(f"“{nxt['hook_text'].strip()}”", 26):
            y = centred(d, y, ln, playfair(64, 700), (255, 244, 225)) + 18
        y = tracked(d, y + 30, "COMING SOON", oswald(48, 600), GOLD, 14)
    else:
        pill(d, W / 2, y + 50, "THE FINALE IS DONE", anton(60), RED, padx=52, h=112)
        y += 170
        y = gold_text(img, y, "THE FULL MOVIE", anton(150)) + 50
        d = ImageDraw.Draw(img)
        y = tracked(d, y, "IN 24 HOURS", oswald(52, 600), GOLD, 14)
    ys = [1180, 1320, 1460]
    btns = [("LIKE", (40, 40, 44), icon_thumb), ("SHARE", (40, 40, 44), icon_share), ("SUBSCRIBE", RED, icon_bell)]
    for k in range(min(stage, 3)):
        label, colr, ic = btns[k]
        pill(d, W / 2, ys[k], label, anton(58), colr, padx=60, h=112, icon=ic)
    return img


def explainer_card(bg: Image.Image, label: str, text: str, show: str) -> Image.Image:
    """Story explainer between scenes: the next scene, blurred and darkened, with a gold label and the
    narrator's sentence in the middle of the Shorts safe zone (y 380-1240)."""
    img = cover(bg).filter(ImageFilter.GaussianBlur(14))
    img = Image.blend(img, Image.new("RGB", img.size, (8, 6, 4)), 0.6)
    img = grade(img)
    _badge(img, show)
    d = ImageDraw.Draw(img)
    f = playfair(68, 600)
    lines = textwrap.wrap(text, 24)
    lh = tw(d, "Hg", f)[1] + 26
    y = 820 - (len(lines) * lh + (110 if label else 0)) / 2
    if label:
        lf = oswald(44, 600)
        lab = label.upper()
        bottom = tracked(d, y, lab, lf, GOLD, 10)
        half = (sum(tw(d, ch, lf)[0] for ch in lab) + 10 * len(lab)) / 2
        mid = (y + bottom) / 2
        for x0, x1 in ((W / 2 - half - 110, W / 2 - half - 30), (W / 2 + half + 30, W / 2 + half + 110)):
            d.line((x0, mid, x1, mid), fill=GOLD, width=3)
        y = bottom + 80
    for ln in lines:
        y = centred(d, y, ln, f, (255, 246, 230)) + 26
    return img


def explainer_clip(clip: Path, e: dict, show: str, stem: Path) -> Path:
    """The explainer card as a silent clip of the cut's length (cached)."""
    dest = stem.with_name(stem.name + ".mp4")       # not with_suffix: the stem ends in "5.75" (the cut length)
    if not dest.exists():
        x = e["explain"]
        bg = grab(clip, stem.with_name(stem.name + "_bg.png"), float(e["in"]))
        png = stem.with_name(stem.name + ".png")
        explainer_card(bg, x.get("label", ""), x["t"], show).save(png)
        _still(png, dest, float(e["dur"]), zoom=False, fade_in=0.15)
    return dest


# ---------------------------------------------------------------- clips

def _still(png: Path, dest: Path, secs: float, zoom=True, fade_in=0.0, fade_out=0.0, audio=None, audio_start=0.0,
           vol=1.0):
    vf = [f"scale={W * 2}:{H * 2}"]
    if zoom:
        frames = int(secs * FPS)
        vf.append(f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}")
    else:
        vf.append(f"scale={W}:{H},fps={FPS}")
    if fade_in:
        vf.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out:
        vf.append(f"fade=t=out:st={secs - fade_out:.2f}:d={fade_out}")
    vf.append("setsar=1,format=yuv420p")
    a_in = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    af = f"volume=0"
    if audio and Path(audio).exists():
        a_in = ["-ss", f"{audio_start:.2f}", "-i", str(audio)]
        af = f"volume={vol},afade=t=in:st=0:d=0.05,afade=t=out:st={max(secs - 0.6, 0):.2f}:d=0.6,apad"
    _ff("-loop", "1", "-framerate", FPS, "-i", png, *a_in, "-vf", ",".join(vf), "-af", af,
        "-map", "0:v", "-map", "1:a", "-t", f"{secs:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-r", FPS, "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", dest)
    return dest


def _concat(parts: list, dest: Path):
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    _ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dest)
    lst.unlink(missing_ok=True)
    return dest


def _music(name: str):
    for ext in ("mp3", "m4a", "wav"):
        p = config.MUSIC / f"{name}.{ext}"
        if p.exists():
            return p
    return None


def _sfx(name):
    p = config.ROOT / "assets" / "sfx" / f"{name}.wav"
    return p if p.exists() else None


def _arc_parts(channel, ep):
    eps = [e for e in state.episodes(channel) if e.get("arc") == ep.get("arc")]
    return sorted(eps, key=lambda e: e.get("part", 0))


def _pick_clip(ep, key, default):
    return int((ep.get("cards") or {}).get(key, default))


def _auto_thumb(ep) -> int:
    """First clip whose speaker is alone on screen (a strong single face)."""
    clips = {c["n"]: c for c in ep.get("clips", [])}
    for e in ep.get("edit", []):
        c = clips.get(e["clip"], {})
        if e.get("line") and len(c.get("chars", [])) == 1:
            return e["clip"]
    return 1


def make(channel: str, ep: dict, bible: dict, clips: dict, wd: Path) -> dict:
    """clips = {clip number: Path}. Returns {"intro": [mp4...], "outro": [mp4...], "thumbnail": jpg}
    (empty when channel.json has no "episode_cards")."""
    cfg = bible.get("episode_cards")
    if not cfg:
        return {}
    cd = wd / "cards"
    cd.mkdir(parents=True, exist_ok=True)
    show = bible.get("show_title", channel)
    parts = _arc_parts(channel, ep)
    ep = {**ep, "parts_total": len(parts) or 6}
    nxt = next((e for e in parts if e.get("part") == ep.get("part", 0) + 1), None)

    def frame(n, at=None, tag=""):
        n = n if n in clips else min(clips)
        return grab(clips[n], cd / f"clip{n:02d}{tag}.png", at)

    # thumbnail / title card
    thumb = thumbnail(ep, frame(_pick_clip(ep, "thumb_clip", _auto_thumb(ep))), show)
    thumb.save(cd / "title.png")
    jpg = wd / "thumbnail.jpg"
    thumb.save(jpg, quality=90)
    out = {"thumbnail": jpg, "intro": [], "outro": []}
    sting = _music((ep.get("scenes", {}).get("A", {}).get("music") or "tension drums").replace(" ", "-"))
    t_sec = float(cfg.get("title_seconds", 2.5))
    out["intro"].append(_still(cd / "title.png", cd / "title.mp4", t_sec, fade_out=0.25,
                               audio=_sfx("riser") or sting, vol=0.9))

    # story brief (part 1 of each arc)
    if ep.get("part", 1) in cfg.get("brief_parts", [1]):
        cast = []
        guests = ep.get("guests", {})
        for cid, g in guests.items():
            n = next((c["n"] for c in ep.get("clips", []) if c.get("chars") == [cid]), None)
            if n and n in clips:
                cast.append((g.get("name", cid).replace("Mrs ", "Mrs. ").replace("Mr ", "Mr. "), frame(n)))
        b = brief(ep, frame(_pick_clip(ep, "brief_clip", 1)), cast[:5], show)
        b.save(cd / "brief.png")
        out["intro"].append(_still(cd / "brief.png", cd / "brief.mp4", float(cfg.get("brief_seconds", 6.5)),
                                   fade_in=0.25, fade_out=0.3, audio=sting, audio_start=2.0, vol=0.55))

    # next-episode teaser + like / share / subscribe
    last = ep["edit"][-1]["clip"] if ep.get("edit") else max(clips)
    bg = frame(_pick_clip(ep, "next_clip", last), at=None, tag="_next")
    n_sec = float(cfg.get("next_seconds", 5.0))
    steps = [n_sec * 0.36, n_sec * 0.16, n_sec * 0.16, n_sec * 0.32]
    segs = []
    tail = _music("nollywood-suspense")
    for k, s in enumerate(steps):
        png = cd / f"next{k}.png"
        next_card(ep, nxt, bg, show, k).save(png)
        segs.append(_still(png, cd / f"next{k}.mp4", s, zoom=False, fade_in=0.3 if k == 0 else 0,
                           fade_out=0.4 if k == len(steps) - 1 else 0,
                           audio=(_sfx("whoosh") if k else tail), vol=0.8 if k else 0.5))
    out["outro"].append(_concat(segs, cd / "next.mp4"))
    return out
