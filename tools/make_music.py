"""Synthesise original, royalty-free background tracks into music/ (no samples, no copyright).

    pip install numpy && python tools/make_music.py

Writes music/calm-piano.mp3 (Elders carousel) and music/gentle-lullaby.mp3 (Crib carousel): 64 s
loops, a soft chord progression with arpeggios, gentle bass and room reverb (ffmpeg aecho).
Real tracks from YouTube Studio's Audio Library can replace them at any time (same file names).
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "music"


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def piano(f, dur, vel=0.5):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    tone = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * k * 0.9)
               for k, a in [(1, 1.0), (2, 0.45), (3, 0.18), (4, 0.08), (5, 0.04)])
    return vel * env * tone


def bell(f, dur, vel=0.5):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 3.0) * (1 - np.exp(-t * 500))
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 4) \
        + 0.15 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6)
    return vel * env * tone


def pad(f, dur, vel=0.12):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return vel * env * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t))


def track(seconds, bpm, chords, voice, arp, seed, bass=True):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = beat * 4
    out = np.zeros(int(SR * (seconds + 6)))

    def add(sig, at):
        i = int(at * SR)
        out[i:i + len(sig)] += sig[:max(0, len(out) - i)]

    t, ci = 0.0, 0
    while t < seconds:
        root, notes = chords[ci % len(chords)]
        for n in notes:
            add(pad(hz(n), bar + 1.0), t)
        if bass:
            add(piano(hz(root - 12), bar * 1.2, 0.35), t)
        pattern = arp[ci % len(arp)]
        for step, idx in enumerate(pattern):
            if idx is None:
                continue
            note = notes[idx % len(notes)] + 12 * (idx // len(notes))
            add(voice(hz(note), 3.0, 0.22 + 0.06 * rng.random()), t + step * beat / 2)
        t += bar
        ci += 1
    out = out[:int(SR * seconds)]
    fade = int(SR * 2)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-9) * 0.8


def write(sig, name):
    OUT.mkdir(exist_ok=True)
    tmp = OUT / f".{name}.wav"
    st = np.stack([sig, np.roll(sig, int(SR * 0.012))], axis=1)    # slight stereo width
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    dest = OUT / f"{name}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-af", "aecho=0.8:0.7:60|140|260:0.35|0.25|0.15,lowpass=f=6000,loudnorm=I=-16:TP=-2",
                    "-c:a", "libmp3lame", "-b:a", "160k", str(dest)], check=True)
    tmp.unlink()
    print("wrote", dest.relative_to(ROOT))


def main():
    # C major: C - G/B - Am - F  |  F - C - G - Am   (MIDI note numbers, middle C = 60)
    calm = [(48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]), (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]),
            (41, [57, 60, 65, 72]), (48, [60, 64, 67, 72]), (43, [59, 62, 67, 74]), (45, [60, 64, 69, 72])]
    arp_calm = [[0, 1, 2, 3, 2, 1, None, None], [0, 2, 3, 5, 3, 2, 1, None]]
    write(track(64, 66, calm, piano, arp_calm, seed=1), "calm-piano")
    # lullaby: D major, 3/4-ish feel via sparse arps, music-box bells an octave up
    lull = [(50, [74, 78, 81, 86]), (45, [73, 76, 81, 85]), (47, [71, 74, 78, 83]), (43, [71, 74, 79, 83])]
    arp_lull = [[0, 2, 1, 3, 2, None, 1, None], [3, 2, 1, 0, None, 2, None, None]]
    write(track(64, 72, lull, bell, arp_lull, seed=2, bass=False), "gentle-lullaby")


if __name__ == "__main__":
    sys.exit(main())
