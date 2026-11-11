"""Thin wrapper around fal.ai with retries, downloads, and a free MOCK mode for testing."""
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from . import config


class GenerationError(RuntimeError):
    pass


def _client():
    if not config.FAL_KEY:
        raise GenerationError("FAL_KEY is not set (add it to .env or GitHub secrets)")
    import fal_client  # imported lazily so MOCK mode needs no packages
    return fal_client


def upload(path: Path) -> str:
    """Upload a local file to fal storage and return its URL."""
    if config.MOCK:
        return f"file://{path}"
    return _client().upload_file(Path(path))


def run(endpoint: str, arguments: dict, retries: int = 2) -> dict:
    """Call a fal endpoint (queue + wait). Retries transient failures."""
    client = _client()  # fails fast (no retries) if FAL_KEY is missing
    last = None
    for attempt in range(retries + 1):
        try:
            return client.subscribe(endpoint, arguments=arguments, with_logs=False)
        except Exception as e:  # network blips, queue timeouts, 5xx
            last = e
            print(f"   fal error on {endpoint} (attempt {attempt + 1}): {e}")
            time.sleep(10 * (attempt + 1))
    raise GenerationError(f"{endpoint} failed: {last}")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if url.startswith("file://"):
        shutil.copy(url[7:], dest)
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "shorts-studio"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    return dest


# ---------------- MOCK generators (no network, no cost) ----------------

def _esc(text: str) -> str:
    return text.replace("\\", "").replace(":", " ").replace("'", "").replace("%", "pct")[:60]


def mock_image(dest: Path, label: str, color: str = "0x2b6777", size: str = "1080x1920"):
    dest.parent.mkdir(parents=True, exist_ok=True)
    words, lines, cur = label.split(), [], ""
    for w in words:
        if len(cur) + len(w) > 26:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    draws = ",".join(
        f"drawtext=text='{_esc(l)}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=h/3+{i * 70}"
        for i, l in enumerate(lines[:8])
    )
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s={size}",
                    "-vf", draws, "-frames:v", "1", str(dest)], check=True)
    return dest


def mock_clip(dest: Path, image: Path, seconds: int, freq: int = 330):
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(image),
                    "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=48000",
                    "-vf", "scale=1080:1920,zoompan=z='min(zoom+0.0008,1.08)':d=1:s=1080x1920:fps=25",
                    "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-af", "volume=0.05", "-c:a", "aac", "-shortest", str(dest)], check=True)
    return dest
