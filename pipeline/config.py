"""Central settings. Everything can be overridden with environment variables (or a .env file)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if not os.environ.get(k.strip()):   # empty env vars (unset Codespace/Actions secrets) don't block .env
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _expand_bundles():
    """A secret may hold a whole KEY=VALUE block (e.g. META_TOKEN_FACEBOOK_INSTAGRAM with the token and all
    page ids). Unpack it so each key works as if it were its own secret; real individual values win."""
    import re
    for name in ("META_TOKEN_FACEBOOK_INSTAGRAM", "FACEBOOK_INSTAGRAM_PAGE_IDS", "FACEBOOK_INSTAGRAM_PAGE_IDS_CRIB",
                 "FACEBOOK_INSTAGRAM_PAGE_IDS_ELDERS", "META_BUNDLE"):
        raw = os.environ.get(name, "").strip()
        # accepts KEY=VALUE or KEY: VALUE, separated by newlines, spaces, commas or semicolons
        for k, v in re.findall(r"([A-Z][A-Z0-9_]*)\s*[=:]\s*['\"]?([^\s,;'\"]+)", raw):
            if not os.environ.get(k):
                os.environ[k] = v


# Per-channel page-id secrets for the Google Flow channels -> env prefix used by pipeline/meta.py
CHANNEL_ID_SECRETS = {"FACEBOOK_INSTAGRAM_PAGE_IDS_CRIB": "CRIBCOMMITTEE",
                      "FACEBOOK_INSTAGRAM_PAGE_IDS_ELDERS": "ELDERS"}


def _expand_channel_ids():
    """FACEBOOK_INSTAGRAM_PAGE_IDS_CRIB / _ELDERS hold one channel's ids in any loose form: <PREFIX>_FB_ID=..,
    FB_ID=.., Facebook: .., Instagram: .., or just two numbers (Facebook first, then Instagram)."""
    import re
    for secret, prefix in CHANNEL_ID_SECRETS.items():
        raw = os.environ.get(secret, "").strip()
        if not raw:
            continue
        found = {}
        for k, v in re.findall(r"([A-Za-z][A-Za-z0-9_ ]*?)\s*[=:]\s*['\"]?(\d{5,})", raw):
            k = k.upper()
            kind = "IG" if ("IG" in k or "INSTA" in k) else "FB" if ("FB" in k or "FACEBOOK" in k or "PAGE" in k) else None
            if kind:
                found.setdefault(kind, v)
        if not found:
            nums = re.findall(r"\d{5,}", raw)
            found = dict(zip(("FB", "IG"), nums))
        for kind, v in found.items():
            if not os.environ.get(f"{prefix}_{kind}_ID"):
                os.environ[f"{prefix}_{kind}_ID"] = v


_load_dotenv()
_expand_bundles()
_expand_channel_ids()


def env(name, default=None):
    return os.environ.get(name, default)


MOCK = env("MOCK", "0") == "1"          # MOCK=1 -> no API calls, placeholder images/clips (free testing)
FAL_KEY = env("FAL_KEY")

# --- fal.ai endpoints (swap models here with one line) ---
# Cheapest models that still keep the characters consistent (tested side by side, Nov 2026):
#   references: nano-banana ($0.04/image, made once per character and reused forever)
#   keyframes:  flux-2 flash edit (~$0.015/keyframe at 720x1280 vs $0.04 for nano-banana/edit)
#   fal video fallback: LTX-2 19B distilled (~$0.02/s at 720p vs $0.06/s for ltx-2.3 fast, which is 1080p minimum)
IMAGE_T2I = env("IMAGE_T2I", "fal-ai/nano-banana")                 # character reference sheets (one-off)
IMAGE_EDIT = env("IMAGE_EDIT", "fal-ai/flux-2/flash/edit")         # shot keyframes built from the reference images
IMAGE_KEY_T2I = env("IMAGE_KEY_T2I", "fal-ai/flux-2/flash")        # keyframes for shots with no characters
KEYFRAME_SIZE = {"width": 720, "height": 1280}                     # video is 720p anyway; output is upscaled
VIDEO_I2V = env("VIDEO_I2V", "fal-ai/ltx-2-19b/distilled/image-to-video")
VIDEO_RESOLUTION = env("VIDEO_RESOLUTION", "1080p")
VIDEO_FPS = int(env("VIDEO_FPS", "25"))
GENERATE_AUDIO = env("GENERATE_AUDIO", "1") == "1"

# --- video provider: "ltx" = Lightricks' own API (cheapest), "fal" = fal.ai. Falls back to fal on failure. ---
VIDEO_PROVIDER = env("VIDEO_PROVIDER", "ltx")
VIDEO_FALLBACK = env("VIDEO_FALLBACK", "fal")          # "" to disable the fallback
LTX_API_KEY = env("LTX_API_KEY")
LTX_BASE_URL = env("LTX_BASE_URL", "https://api.ltx.io").rstrip("/")
LTX_MODEL = env("LTX_MODEL", "ltx-2-3-fast")           # or ltx-2-3-pro (sharper, $0.04/s at 720p)
LTX_RESOLUTION = env("LTX_RESOLUTION", "720x1280")     # 9:16 portrait; 1080x1920 doubles the price
LTX_TIMEOUT_SECONDS = int(env("LTX_TIMEOUT_SECONDS", "900"))

# Published per-second prices (docs.ltx.io/pricing, fal.ai model page), used for the cost guard.
_PRICES = {("ltx", "ltx-2-3-fast", "720"): 0.03, ("ltx", "ltx-2-3-fast", "1080"): 0.06,
           ("ltx", "ltx-2-3-pro", "720"): 0.04, ("ltx", "ltx-2-3-pro", "1080"): 0.08}


def _default_price():
    if VIDEO_PROVIDER == "ltx" and LTX_API_KEY:
        short = LTX_RESOLUTION.lower().split("x")
        tier = "720" if min(int(x) for x in short) <= 720 else "1080"
        return _PRICES.get(("ltx", LTX_MODEL, tier), 0.06)
    if "ltx-2-19b" in VIDEO_I2V:
        return 0.02   # $0.0008 per output megapixel: 736x1280 x 25 fps ~= $0.019/s
    return 0.06   # fal.ai LTX-2.3 Fast i2v @1080p


# --- cost guard (USD). Rough estimate per episode is checked before rendering. ---
PRICE_PER_VIDEO_SECOND = float(env("PRICE_PER_VIDEO_SECOND", "") or _default_price())
PRICE_PER_IMAGE = float(env("PRICE_PER_IMAGE", "0.015"))                # flux-2 flash edit keyframe
DAILY_BUDGET_USD = float(env("DAILY_BUDGET_USD", "15"))
MAX_ATTEMPTS = int(env("MAX_ATTEMPTS", "3"))
PARALLEL_SHOTS = int(env("PARALLEL_SHOTS", "4"))   # shots generated at the same time

# --- output ---
OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
CAPTION_FONT = env("CAPTION_FONT", "DejaVu Sans")
MUSIC_VOLUME = float(env("MUSIC_VOLUME", "0.12"))
TARGET_LUFS = env("TARGET_LUFS", "-14")

# --- YouTube ---
CHANNELS = [c.strip() for c in env("CHANNELS", "flat4b,coldhearts,drizzlepudge,elders,cribcommittee").split(",") if c.strip()]
REVIEW_HOURS = float(env("REVIEW_HOURS", "10"))   # upload private, auto-publish after N hours (0 = stay private)
YT_CATEGORY = {"flat4b": "23", "coldhearts": "24", "drizzlepudge": "1", "elders": "22", "cribcommittee": "22"}  # fallback; channel.json youtube_category wins
AI_DISCLOSURE = "Made with AI-generated animation."

OUTPUT = ROOT / ("output_mock" if MOCK else "output")
ASSETS = OUTPUT / "assets" if MOCK else ROOT / "assets"   # mock never touches real reference images
MUSIC = ROOT / "music"
SECRETS = ROOT / "secrets"
CHANNELS_DIR = ROOT / "channels"
INBOX = (OUTPUT / "inbox") if MOCK else (ROOT / "inbox")   # Google Flow clips uploaded by hand (channels with "source": "flow")
