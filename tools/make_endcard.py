"""Draw a channel's end card PNG (1080x1920) from channel.json `end_card`.

    python tools/make_endcard.py elders

Needs Pillow locally (pip install pillow); the pipeline itself only uses the committed PNG + ffmpeg.
If assets/<channel>/logo.png exists it is placed at the top; colours come from end_card.colors
(set them to match the logo). Facebook / Instagram / YouTube icons are drawn as simple vectors.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1080, 1920
FONTS = [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]


def font(name, size):
    for d in FONTS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default(size)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


SHADOW = True   # set per channel from end_card.shadow (pastel cards look cleaner without it)


def centred(draw, y, text, f, fill, shadow=None):
    x = (W - draw.textlength(text, font=f)) / 2
    if SHADOW if shadow is None else shadow:
        draw.text((x + 4, y + 5), text, font=f, fill=(0, 0, 0, 150))
    draw.text((x, y), text, font=f, fill=fill)
    return y + f.size * 1.18


# ---------- platform icons (simple vector marks, 150 px) ----------

def icon_facebook(s):
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=(24, 119, 242))
    f = font("DejaVuSans-Bold.ttf", int(s * 0.78))
    d.text((s * 0.53, s * 0.56), "f", font=f, fill="white", anchor="mm")
    return im


def icon_instagram(s):
    grad = Image.new("RGBA", (s, s))
    g = ImageDraw.Draw(grad)
    stops = [(254, 218, 117), (250, 126, 30), (214, 41, 118), (150, 47, 191), (79, 91, 213)]
    for i in range(2 * s):           # diagonal gradient bottom-left -> top-right
        t = i / (2 * s - 1) * (len(stops) - 1)
        a, b = stops[int(t)], stops[min(int(t) + 1, len(stops) - 1)]
        c = tuple(int(x + (y - x) * (t - int(t))) for x, y in zip(a, b))
        g.line([(i - s, s), (i, 0)], fill=c, width=2)
    mask = Image.new("L", (s, s))
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.27), fill=255)
    im = Image.new("RGBA", (s, s))
    im.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(im)
    lw = max(int(s * 0.075), 3)
    m = s * 0.2
    d.rounded_rectangle([m, m, s - m, s - m], radius=int(s * 0.17), outline="white", width=lw)
    r = s * 0.15
    d.ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], outline="white", width=lw)
    dr = s * 0.04
    d.ellipse([s * 0.69 - dr, s * 0.31 - dr, s * 0.69 + dr, s * 0.31 + dr], fill="white")
    return im


def icon_youtube(s):
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    h = s * 0.7
    top = (s - h) / 2
    d.rounded_rectangle([0, top, s - 1, top + h], radius=int(s * 0.2), fill=(255, 0, 0))
    cx, cy, t = s * 0.52, s / 2, s * 0.17
    d.polygon([(cx - t * 0.8, cy - t), (cx - t * 0.8, cy + t), (cx + t * 1.0, cy)], fill="white")
    return im


def emblem(cfg, s, accent, ink):
    """Fallback when no logo.png exists yet: a ring with initials."""
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=accent)
    d.ellipse([12, 12, s - 13, s - 13], outline=ink, width=6)
    d.text((s / 2, s / 2), cfg.get("initials", "ATE"), font=font("DejaVuSerif-Bold.ttf", int(s * 0.3)),
           fill=ink, anchor="mm")
    return im


def build(channel):
    bible = json.loads((ROOT / "channels" / channel / "channel.json").read_text())
    cfg = bible["end_card"]
    global SHADOW
    SHADOW = cfg.get("shadow", True)
    col = {k: rgb(v) for k, v in cfg["colors"].items()}
    img = gradient(col["bg_top"], col["bg_bottom"]).convert("RGBA")

    logo_p = ROOT / cfg.get("logo", f"assets/{channel}/logo.png")
    # soft glow behind the placeholder emblem (a real logo brings its own background)
    glow = Image.new("RGBA", (W, H))
    ImageDraw.Draw(glow).ellipse([W / 2 - 330, 170, W / 2 + 330, 830], fill=col["accent"] + (70,))
    if not logo_p.exists():
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(110)))
    d = ImageDraw.Draw(img)

    # logo (top, inside the Shorts safe area)
    size = int(cfg.get("logo_size", 400))
    if logo_p.exists():
        logo = Image.open(logo_p).convert("RGBA")
        logo.thumbnail((size, size), Image.Resampling.LANCZOS)
        if logo.getchannel("A").getextrema()[0] == 255:   # opaque logo: feather the edges into the card
            m = Image.new("L", logo.size)
            pad = int(min(logo.size) * 0.03)
            ImageDraw.Draw(m).ellipse([pad, pad, logo.width - pad, logo.height - pad], fill=255)
            logo.putalpha(m.filter(ImageFilter.GaussianBlur(min(logo.size) * 0.06)))
    else:
        logo = emblem(cfg, size, col["accent"], col["bg_top"])
    logo_top = int(cfg.get("logo_top", 280))
    img.alpha_composite(logo, ((W - logo.width) // 2, logo_top + (size - logo.height) // 2))

    y = logo_top + size + 55
    f = font("DejaVuSans-Bold.ttf", 56)
    for ln in wrap(d, cfg["cta"], f, 900):
        y = centred(d, y, ln, f, col["accent"])
    y += 6
    for ln in wrap(d, cfg["name"], font("DejaVuSerif-Bold.ttf", 104), 940):
        y = centred(d, y, ln, font("DejaVuSerif-Bold.ttf", 104), col["text"])
    y += 22
    d.rounded_rectangle([W / 2 - 150, y, W / 2 + 150, y + 8], radius=4, fill=col["accent"])
    y += 44
    f = font("DejaVuSans-Bold.ttf", 52)
    for ln in wrap(d, cfg["sub"], f, 900):
        y = centred(d, y, ln, f, col["text"])

    # social row: three icons + handle
    s, gap = 150, 70
    x0 = (W - (3 * s + 2 * gap)) // 2
    iy = int(max(y + 60, 1380))
    for i, mk in enumerate((icon_facebook, icon_instagram, icon_youtube)):
        ic = mk(s)
        sh = Image.new("RGBA", (W, H))
        sh.paste((0, 0, 0, 150), (x0 + i * (s + gap) + 6, iy + 10), ic.getchannel("A"))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
        img.alpha_composite(ic, (x0 + i * (s + gap), iy))
    d = ImageDraw.Draw(img)
    centred(d, iy + s + 34, cfg.get("handle", cfg["name"]), font("DejaVuSans-Bold.ttf", 54), col["accent"])

    out = ROOT / cfg["image"]
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)} (logo: {'yes' if logo_p.exists() else 'placeholder emblem'})")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "elders")
