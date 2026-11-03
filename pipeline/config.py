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
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def env(name, default=None):
    return os.environ.get(name, default)


MOCK = env("MOCK", "0") == "1"          # MOCK=1 -> no API calls, placeholder images/clips (free testing)
FAL_KEY = env("FAL_KEY")

# --- fal.ai endpoints (swap models here with one line) ---
IMAGE_T2I = env("IMAGE_T2I", "fal-ai/nano-banana")           # character reference sheets
IMAGE_EDIT = env("IMAGE_EDIT", "fal-ai/nano-banana/edit")    # shot keyframes built from the reference images
VIDEO_I2V = env("VIDEO_I2V", "fal-ai/ltx-2.3/image-to-video/fast")
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
    return 0.06   # fal.ai LTX-2.3 Fast i2v @1080p


# --- cost guard (USD). Rough estimate per episode is checked before rendering. ---
PRICE_PER_VIDEO_SECOND = float(env("PRICE_PER_VIDEO_SECOND", "") or _default_price())
PRICE_PER_IMAGE = float(env("PRICE_PER_IMAGE", "0.04"))                 # nano-banana edit
DAILY_BUDGET_USD = float(env("DAILY_BUDGET_USD", "15"))
MAX_ATTEMPTS = int(env("MAX_ATTEMPTS", "3"))
PARALLEL_SHOTS = int(env("PARALLEL_SHOTS", "4"))   # shots generated at the same time

# --- output ---
OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30
CAPTION_FONT = env("CAPTION_FONT", "DejaVu Sans")
MUSIC_VOLUME = float(env("MUSIC_VOLUME", "0.12"))
TARGET_LUFS = env("TARGET_LUFS", "-14")

# --- YouTube ---
CHANNELS = [c.strip() for c in env("CHANNELS", "flat4b,coldhearts,drizzlepudge").split(",") if c.strip()]
REVIEW_HOURS = float(env("REVIEW_HOURS", "10"))   # upload private, auto-publish after N hours (0 = stay private)
YT_CATEGORY = {"flat4b": "23", "coldhearts": "24", "drizzlepudge": "1"}  # fallback; channel.json youtube_category wins
AI_DISCLOSURE = "Made with AI-generated animation."

OUTPUT = ROOT / ("output_mock" if MOCK else "output")
ASSETS = OUTPUT / "assets" if MOCK else ROOT / "assets"   # mock never touches real reference images
MUSIC = ROOT / "music"
SECRETS = ROOT / "secrets"
CHANNELS_DIR = ROOT / "channels"
