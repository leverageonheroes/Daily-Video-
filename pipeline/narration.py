"""Narrator voice (text-to-speech) for channels whose shots carry a "narration" field (e.g. One In A Thousand).

One consistent voice per channel: channel.json "narrator": {"voice": "...", "endpoint": "...", "speed": 1.0}.
Default endpoint = fal.ai ElevenLabs Turbo v2.5 (about $0.05 per 1,000 characters, so ~$0.05 per Short),
with Kokoro (about $0.02 per 1,000 characters) as automatic fallback. Every file is cached per shot.

Each shot's narration is fitted to the shot: if the speech runs longer than the shot, it is sped up
(max 1.25x); if it is still too long, validation should have caught it (keep <= 2.6 words per second).
"""
import subprocess
from pathlib import Path
from typing import Optional

from . import assemble, config, fal_api

FIT_MARGIN = 0.35        # seconds of air left at the end of each shot
MAX_SPEEDUP = 1.25


def _audio_url(res: dict) -> Optional[str]:
    a = res.get("audio") or res.get("audio_file") or res.get("output")
    if isinstance(a, dict):
        return a.get("url")
    if isinstance(a, str):
        return a
    raise fal_api.GenerationError(f"no audio in TTS result: {str(res)[:300]}")


def _tts(text: str, cfg: dict, dest: Path) -> Path:
    endpoints = [(cfg.get("endpoint") or config.TTS_ENDPOINT, cfg.get("voice") or config.TTS_VOICE)]
    fb = cfg.get("fallback_endpoint", config.TTS_FALLBACK)
    if fb:
        endpoints.append((fb, cfg.get("fallback_voice") or config.TTS_FALLBACK_VOICE))
    errors = []
    for ep, voice in endpoints:
        try:
            args = {"text": text}
            if voice:
                args["voice"] = voice
            if cfg.get("speed"):
                args["speed"] = cfg["speed"]
            res = fal_api.run(ep, args, retries=1)
            url = _audio_url(res)
            if not url:
                raise RuntimeError("no audio url in response")
            raw = dest.with_suffix(".src" + Path(url.split("?")[0]).suffix)
            fal_api.download(url, raw)
            return raw
        except Exception as e:
            errors.append(f"{ep}: {e}")
            print(f"   narrator: {ep} failed ({str(e)[:120]})")
    raise fal_api.GenerationError("all TTS endpoints failed -> " + " | ".join(errors))


def _mock_tts(text: str, dest: Path) -> Path:
    secs = max(1.0, len(text.split()) / 2.5)
    raw = dest.with_suffix(".src.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=520:sample_rate=48000:duration={secs:.2f}", "-af", "volume=0.4", str(raw)],
                   check=True)
    return raw


def render(channel: str, episode: dict, workdir: Path, bible: dict):
    """Returns one audio path (or None) per shot, each already fitted to its shot length."""
    if not any(s.get("narration") for s in episode["shots"]):
        return None
    cfg = bible.get("narrator", {})
    out: list[Optional[Path]] = []
    for shot in episode["shots"]:
        text = (shot.get("narration") or "").strip()
        if not text:
            out.append(None)
            continue
        dest = workdir / f"narr{shot['n']:02d}.wav"
        if not dest.exists():
            print(f"   narrator shot {shot['n']}")
            raw = _mock_tts(text, dest) if config.MOCK else _tts(text, cfg, dest)
            d = assemble.duration(raw)
            room = shot["dur"] - FIT_MARGIN
            tempo = min(MAX_SPEEDUP, d / room) if d > room else 1.0
            if d / max(tempo, 1e-6) > shot["dur"]:
                print(f"   !! shot {shot['n']}: narration {d:.1f}s is too long for {shot['dur']}s - it will be cut")
            af = f"atempo={tempo:.3f}," if tempo > 1.0 else ""
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
                            f"{af}aresample=48000,apad", "-t", str(shot["dur"]), "-ac", "2", str(dest)], check=True)
        out.append(dest)
    return out


def estimate_cost(episode: dict) -> float:
    chars = sum(len(s.get("narration", "")) for s in episode["shots"])
    return chars / 1000 * config.TTS_PRICE_PER_1K
