"""Long-term storage of rendered episodes in GitHub Releases (free, survives the ephemeral Actions runner).

One release per channel, tag `episodes-<channel>`, one asset per episode: <EPISODE_ID>.mp4 (the clean copy,
without the hook text). Used by the monthly compilation. Enabled with STORE_RELEASES=1 (set in the workflows).
Needs the `gh` CLI with GH_TOKEN (GitHub Actions and Codespaces provide both).
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from . import config, seo

ENABLED = os.environ.get("STORE_RELEASES", "0") == "1" and not config.MOCK


def _tag(channel):
    return f"episodes-{channel}"


def _gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def _ensure_release(tag, channel):
    if _gh("release", "view", tag, check=False).returncode == 0:
        return
    r = _gh("release", "create", tag, "--title", f"{channel} episodes",
            "--notes", "Rendered episodes kept for monthly compilations. Managed by the pipeline.", check=False)
    if r.returncode != 0 and _gh("release", "view", tag, check=False).returncode != 0:
        raise RuntimeError(f"could not create release {tag}: {(r.stderr or r.stdout).strip()[:300]}")


def _upload(tag, channel, files):
    _ensure_release(tag, channel)
    err = ""
    for attempt in range(3):
        r = _gh("release", "upload", tag, *map(str, files), "--clobber", check=False)
        if r.returncode == 0:
            return
        err = (r.stderr or r.stdout).strip()[:300]
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"upload to release {tag} failed: {err}")


def save_episode(channel: str, ep_id: str, clean_mp4: Path):
    if not ENABLED:
        return False
    tag = _tag(channel)
    asset = clean_mp4.parent / f"{ep_id}.mp4"
    shutil.copy(clean_mp4, asset)
    try:
        _upload(tag, channel, [asset])
    finally:
        asset.unlink()
    print(f"   stored {ep_id} in release {tag}")
    return True


TIKTOK_NOTES = ("Videos for manual TikTok posting. Each episode: <ID>.mp4 (upload this) + <ID>.txt (paste as the "
                "caption). When posting, switch ON 'AI-generated content' (More options). Managed by the pipeline.")


def tiktok_caption(episode: dict, bible: dict | None = None) -> str:
    """Paste-ready TikTok caption: title without #shorts + TikTok-style hashtags (max 5, under 2200 chars)."""
    import re
    title = re.sub(r"\s*#shorts\b", "", episode["title"], flags=re.I).strip()
    tags = seo.hashtags(bible or {}, episode.get("tags", []), "tiktok")
    return f"{title}\n\n{episode.get('description', '').strip()}\n\n{' '.join(tags)}\n"[:2200]


def save_tiktok(channel: str, ep_id: str, video: Path, episode: dict):
    """Keep the upload-ready video + caption permanently in release `tiktok-<channel>` for manual posting."""
    if not ENABLED:
        return False
    tag = f"tiktok-{channel}"
    if _gh("release", "view", tag, check=False).returncode != 0:
        _gh("release", "create", tag, "--title", f"TikTok - {channel}", "--notes", TIKTOK_NOTES, check=False)
    mp4, txt = video.parent / f"{ep_id}.mp4", video.parent / f"{ep_id}.txt"
    shutil.copy(video, mp4)
    try:
        bible = json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())
    except (OSError, ValueError):
        bible = {}
    txt.write_text(tiktok_caption(episode, bible), encoding="utf-8")
    try:
        _upload(tag, channel, [mp4, txt])
    finally:
        mp4.unlink(missing_ok=True)
        txt.unlink(missing_ok=True)
    print(f"   stored {ep_id} for TikTok in release {tag}")
    return True


def save_final(channel: str, ep_id: str, workdir: Path):
    """Keep the upload-ready final.mp4 + metadata.json so a failed upload can be retried on a later
    (fresh) runner without paying to render again. Removed from the release once uploaded."""
    if not ENABLED:
        return False
    files = []
    for name in ("final.mp4", "metadata.json"):
        dst = workdir / f"{ep_id}.{name}"
        shutil.copy(workdir / name, dst)
        files.append(dst)
    try:
        _upload(_tag(channel), channel, files)
    finally:
        for f in files:
            f.unlink()
    return True


def fetch_final(channel: str, ep_id: str, workdir: Path) -> bool:
    """Restore final.mp4 + metadata.json into workdir from the release. True if both are there."""
    if (workdir / "final.mp4").exists() and (workdir / "metadata.json").exists():
        return True
    if not ENABLED:
        return False
    workdir.mkdir(parents=True, exist_ok=True)
    for name in ("final.mp4", "metadata.json"):
        r = _gh("release", "download", _tag(channel), "--pattern", f"{ep_id}.{name}", "--dir", str(workdir),
                "--clobber", check=False)
        got = workdir / f"{ep_id}.{name}"
        if r.returncode != 0 or not got.exists():
            return False
        got.replace(workdir / name)
    return True


def drop_final(channel: str, ep_id: str):
    """Delete the stored final.mp4 + metadata.json once the episode is uploaded (clean copy stays)."""
    if not ENABLED:
        return
    for name in ("final.mp4", "metadata.json"):
        _gh("release", "delete-asset", _tag(channel), f"{ep_id}.{name}", "--yes", check=False)


def fetch_episode(channel: str, ep_id: str, dest: Path) -> Path:
    """Local copy if it exists (Codespace / mock), otherwise download from the release."""
    local = config.OUTPUT / channel / ep_id / "clean.mp4"
    if local.exists():
        return local
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = _gh("release", "download", _tag(channel), "--pattern", f"{ep_id}.mp4", "--dir", str(dest.parent),
            "--clobber", check=False)
    got = dest.parent / f"{ep_id}.mp4"
    if r.returncode != 0 or not got.exists():
        raise FileNotFoundError(f"{ep_id} not found locally or in release {_tag(channel)}: {r.stderr.strip()}")
    return got
