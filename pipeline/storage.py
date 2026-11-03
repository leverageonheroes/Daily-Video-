"""Long-term storage of rendered episodes in GitHub Releases (free, survives the ephemeral Actions runner).

One release per channel, tag `episodes-<channel>`, one asset per episode: <EPISODE_ID>.mp4 (the clean copy,
without the hook text). Used by the monthly compilation. Enabled with STORE_RELEASES=1 (set in the workflows).
Needs the `gh` CLI with GH_TOKEN (GitHub Actions and Codespaces provide both).
"""
import os
import shutil
import subprocess
from pathlib import Path

from . import config

ENABLED = os.environ.get("STORE_RELEASES", "0") == "1" and not config.MOCK


def _tag(channel):
    return f"episodes-{channel}"


def _gh(*args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def save_episode(channel: str, ep_id: str, clean_mp4: Path):
    if not ENABLED:
        return False
    tag = _tag(channel)
    if _gh("release", "view", tag, check=False).returncode != 0:
        _gh("release", "create", tag, "--title", f"{channel} episodes",
            "--notes", "Rendered episodes kept for monthly compilations. Managed by the pipeline.")
    asset = clean_mp4.parent / f"{ep_id}.mp4"
    shutil.copy(clean_mp4, asset)
    _gh("release", "upload", tag, str(asset), "--clobber")
    asset.unlink()
    print(f"   stored {ep_id} in release {tag}")
    return True


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
