#!/usr/bin/env python3
"""Make background-music beds with fal Lyria 2 (~30 s each, $0.10; the pipeline loops them).
  python tools/make_music_ai.py            # only moods whose music/<slug>.mp3 is missing
Never overwrites an existing file."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config, fal_api  # noqa: E402

NEG = "vocals, singing, lyrics, speech, low quality, distortion, abrupt ending"
TRACKS = {
    "nollywood-suspense": "Cinematic African drama suspense underscore, slow talking drum and shekere pulse, low "
                          "strings drone, sparse kora plucks, tense and mysterious, steady loopable groove, instrumental",
    "tender-strings": "Tender emotional film score, warm string ensemble and soft piano, gentle kora melody, "
                      "bittersweet family drama, slow tempo, loopable, instrumental",
    "tension-drums": "Driving cinematic tension, deep African percussion and djembe, pulsing low synth bass, rising "
                     "string ostinato, confrontation scene, loopable, instrumental",
}

for slug, prompt in TRACKS.items():
    out = config.MUSIC / f"{slug}.mp3"
    if out.exists():
        print(f"   {slug}: exists, skipped")
        continue
    res = fal_api.run("fal-ai/lyria2", {"prompt": prompt, "negative_prompt": NEG})
    url = res["audio"]["url"]
    raw = out.with_suffix(".src" + Path(url.split("?")[0]).suffix)
    fal_api.download(url, raw)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-b:a", "192k", str(out)], check=True)
    raw.unlink()
    print(f"   {slug}: {out}")
