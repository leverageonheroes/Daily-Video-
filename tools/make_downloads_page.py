"""Write DOWNLOADS.md: a phone-friendly list of every finished Short of all 5 channels
(Releases tiktok-<channel>) with a direct download link and the paste-ready TikTok caption.

Open it on the phone at https://github.com/<owner>/<repo>/blob/main/DOWNLOADS.md (no app needed).
The repo is public, so the release links download straight away, no login.

Usage: python tools/make_downloads_page.py   (needs `gh` with GH_TOKEN; flow-import and daily run it after every Short)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# (folder, show name, id prefix of the current show: old archived shows in the same release are hidden)
CHANNELS = [("elders", "Ask The Elders", "ELD-"), ("cribcommittee", "The Crib Committee", "CC-"),
            ("coldhearts", "Fridge Hearts", "CH-"), ("flat4b", "One In A Thousand", "OIT-"),
            ("drizzlepudge", "Moral Of The Story TV", "MOS-")]
KEEP = 14  # newest Shorts per channel shown on the page (older ones stay in the release)


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def repo():
    return os.environ.get("GITHUB_REPOSITORY") or json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]


def caption(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "30", url], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def main():
    rp = repo()
    out = ["# 📱 Daily downloads for TikTok", "",
           "Tap **⬇️ Download video**, then copy the caption (tap the copy icon on the grey box) and post on TikTok.",
           "Newest first. Updated automatically after every new Short.", "",
           "Jump to: " + " · ".join(f"[{n}](#{n.lower().replace(' ', '-')})" for _, n, _ in CHANNELS), ""]
    for ch, name, prefix in CHANNELS:
        tag = f"tiktok-{ch}"
        try:
            assets = json.loads(gh("release", "view", tag, "--json", "assets"))["assets"]
        except RuntimeError as e:
            print(f"!! {tag}: {e}", file=sys.stderr)
            assets = []
        by_name = {a["name"]: a for a in assets}
        vids = sorted((a for a in assets if a["name"].endswith(".mp4") and a["name"].startswith(prefix)), key=lambda a: a["name"], reverse=True)[:KEEP]
        out += [f"## {name}", ""]
        if not vids:
            out += ["_No videos yet._", ""]
        for a in vids:
            ep = a["name"][:-4]
            date = (a.get("createdAt") or a.get("updatedAt") or "")[:10]
            mb = a.get("size", 0) / 1e6
            url = f"https://github.com/{rp}/releases/download/{tag}/{a['name']}"
            txt = by_name.get(f"{ep}.txt")
            cap = caption(f"https://github.com/{rp}/releases/download/{tag}/{ep}.txt") if txt else ""
            out += [f"### {ep}  ·  {date}", "", f"**[⬇️ Download video]({url})** ({mb:.0f} MB)", ""]
            if cap:
                out += ["```text", cap.replace("```", "'''"), "```", ""]
        out += ["---", ""]
    (ROOT / "DOWNLOADS.md").write_text("\n".join(out), encoding="utf-8")
    print("wrote DOWNLOADS.md")


if __name__ == "__main__":
    main()
