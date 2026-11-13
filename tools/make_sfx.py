#!/usr/bin/env python3
"""Self-made sound effects (synthesised with ffmpeg, so they are ours: no licence questions).

  python tools/make_sfx.py          # writes assets/sfx/{riser,boom,whoosh,heartbeat,footsteps}.wav

Used by the Moral Of The Story TV flow-film mix (pipeline/flowfilm.py). Replace any file with a CC0 sound of
the same name if you like it better.
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"

SFX = {
    # rising filtered noise + rising tone, 2 s
    "riser": ("anoisesrc=d=2:c=pink:a=0.5[n];sine=f=200:d=2[s];"
              "[s]volume=0.25,vibrato=f=6:d=0.2[s2];[n][s2]amix=inputs=2:normalize=0,"
              "highpass=f=300,afade=t=in:d=1.8:curve=exp,afade=t=out:st=1.92:d=0.08"),
    # deep sub hit with a noise transient, 2.5 s tail
    "boom": ("sine=f=48:d=2.5[s];anoisesrc=d=0.25:c=brown:a=0.9[n];"
             "[s]volume=1.6,afade=t=out:st=0.05:d=2.4:curve=exp[s2];[n]lowpass=f=160,afade=t=out:d=0.25[n2];"
             "[s2][n2]amix=inputs=2:normalize=0,alimiter=limit=0.9"),
    # short filtered noise swell, 0.6 s
    "whoosh": ("anoisesrc=d=0.6:c=pink:a=0.6,bandpass=f=1400:w=1800,"
               "afade=t=in:d=0.35:curve=qsin,afade=t=out:st=0.35:d=0.25:curve=qsin"),
    # lub-dub at ~66 bpm, 4 beats
    "heartbeat": ("sine=f=55:d=0.12,afade=t=out:d=0.12,volume=2.2,apad=pad_dur=0.13[a];"
                  "sine=f=48:d=0.14,afade=t=out:d=0.14,volume=1.8,apad=pad_dur=0.52[b];"
                  "[a][b]concat=n=2:v=0:a=1,aloop=loop=3:size=43200,lowpass=f=140"),
    # four heel steps walking away (each quieter)
    "footsteps": ";".join(
        f"anoisesrc=d=0.09:c=brown:a=0.8,lowpass=f=700,afade=t=out:d=0.09,volume={v},apad=pad_dur=0.46[f{i}]"
        for i, v in enumerate((1.0, 0.8, 0.6, 0.45))) + ";[f0][f1][f2][f3]concat=n=4:v=0:a=1",
}


def make(name: str, graph: str, dest: Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", f"{graph},aresample=48000[o]",
                    "-map", "[o]", "-ac", "1", str(dest)], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, graph in SFX.items():
        make(name, graph, OUT / f"{name}.wav")
        print("  ", OUT / f"{name}.wav")


if __name__ == "__main__":
    main()
