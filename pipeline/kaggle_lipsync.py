"""Hard Truths lip-sync on a FREE Kaggle GPU (hardtruths.json "lipsync": "kaggle").

GitHub's free runners have no graphics card, so SadTalker there takes hours. Kaggle gives every phone-verified
account ~30 free GPU hours a week. Each run:
  1. uploads the padded portrait + 16 kHz voice to the public GitHub Release `hardtruths-kaggle`,
  2. pushes tools/kaggle/sadtalker_kernel.py (URLs filled in) as the private Kaggle script `<user>/hard-truths-lipsync`
     with GPU + internet on, which runs SadTalker with the GFPGAN face enhancer,
  3. waits for it, downloads talking_raw.mp4, deletes the two inputs from the release.
Credentials (GitHub secrets): KAGGLE_USERNAME + KAGGLE_KEY (from kaggle.json), or KAGGLE_USERNAME + KAGGLE_API_TOKEN.
Never paid: Kaggle has no billing for this. Any failure raises; pipeline/hardtruths.py then falls back to the CPU run.
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KERNEL_SRC = ROOT / "tools" / "kaggle" / "sadtalker_kernel.py"
REQS = ROOT / "tools" / "sadtalker_requirements.txt"
SETUP = ROOT / "tools" / "setup_sadtalker.sh"
TAG = "hardtruths-kaggle"
SLUG = "hard-truths-lipsync"


def _user():
    return os.environ.get("KAGGLE_USERNAME", "").strip()


def available() -> bool:
    return bool(shutil.which("kaggle") and _user()
                and (os.environ.get("KAGGLE_KEY") or os.environ.get("KAGGLE_API_TOKEN")))


def _kaggle(*args, check=True, timeout=600):
    env = {k: v for k, v in os.environ.items() if not (k.startswith("KAGGLE_") and not v.strip())}  # unset secrets
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"kaggle {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[-800:]}")
    return r


def _gpu_reqs() -> str:
    """Same pins as the CPU install, but PyPI torch 2.1.2 (CUDA 12.1 build) instead of the +cpu wheels."""
    out = []
    for line in REQS.read_text().splitlines():
        if line.startswith("--extra-index-url") or line.startswith("#"):
            continue
        out.append(line.replace("+cpu", ""))
    return "\n".join(out) + "\n"


def _commit() -> str:
    m = re.search(r"^COMMIT=(\w+)", SETUP.read_text(), re.M)
    return m.group(1)


def _status(kid: str) -> str:
    r = _kaggle("kernels", "status", kid, check=False, timeout=120)
    txt = (r.stdout + r.stderr).lower()
    m = re.search(r'status "(?:kernelworkerstatus\.)?(\w+)"', txt)
    return m.group(1) if m else ("unknown: " + txt.strip()[-200:])


def run(img: Path, voice16k: Path, wd: Path, cfg: dict, ep_id: str = "HT") -> Path:
    """Returns the raw SadTalker mp4 (padded framing, like the CPU path). Raises on any failure."""
    from . import storage
    if not available():
        raise RuntimeError("Kaggle not set up (needs KAGGLE_USERNAME + KAGGLE_KEY secrets)")
    repo = os.environ.get("GITHUB_REPOSITORY", "leverageonheroes/Daily-Video-")
    stamp = time.strftime("%Y%m%d%H%M%S")
    names = {"img": f"{ep_id}-{stamp}-src.png", "aud": f"{ep_id}-{stamp}-voice.wav"}
    up = wd / "kaggle_up"
    shutil.rmtree(up, ignore_errors=True)
    up.mkdir(parents=True)
    shutil.copy(img, up / names["img"])
    shutil.copy(voice16k, up / names["aud"])
    storage._upload(TAG, "Hard Truths Kaggle inputs", [up / names["img"], up / names["aud"]])
    base = f"https://github.com/{repo}/releases/download/{TAG}/"
    try:
        kdir = wd / "kaggle_kernel"
        shutil.rmtree(kdir, ignore_errors=True)
        kdir.mkdir()
        src = KERNEL_SRC.read_text()
        for k, v in {"__IMG_URL__": base + names["img"], "__AUD_URL__": base + names["aud"],
                     "__COMMIT__": _commit(), "__SIZE__": str(cfg.get("kaggle_size", 256)),
                     "__ENHANCER__": cfg.get("kaggle_enhancer", "gfpgan"),
                     "__EXPRESSION__": os.environ.get("SADTALKER_EXPRESSION", "1.1"),
                     "__REQS__": _gpu_reqs()}.items():
            src = src.replace(k, v)
        (kdir / "kernel.py").write_text(src)
        kid = f"{_user()}/{SLUG}"
        (kdir / "kernel-metadata.json").write_text(json.dumps({
            "id": kid, "title": SLUG, "code_file": "kernel.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": []}, indent=1))
        print(f"   lip-sync: Kaggle GPU ({kid}, enhancer={cfg.get('kaggle_enhancer', 'gfpgan')})")
        r = _kaggle("kernels", "push", "-p", str(kdir))
        print("   " + r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "   pushed")
        time.sleep(20)
        t0 = time.time()
        limit = 60 * int(cfg.get("kaggle_timeout_min", 75))
        st = ""
        while time.time() - t0 < limit:
            st = _status(kid)
            if st in ("complete", "error", "cancelacknowledged", "cancelrequested"):
                break
            time.sleep(30)
        mins = int(time.time() - t0) // 60
        print(f"   Kaggle status: {st} after {mins} min")
        out = wd / "kaggle_out"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir()
        _kaggle("kernels", "output", kid, "-p", str(out), check=False, timeout=900)
        mp4 = out / "talking_raw.mp4"
        if st != "complete" or not mp4.exists() or mp4.stat().st_size < 10000:
            logs = sorted(out.glob("*.log"))
            tail = logs[0].read_text(errors="ignore")[-2500:] if logs else ""
            raise RuntimeError(f"Kaggle run ended '{st}' without a video.\n{tail}")
        return mp4
    finally:
        for n in names.values():
            subprocess.run(["gh", "release", "delete-asset", TAG, n, "-y"], capture_output=True)
