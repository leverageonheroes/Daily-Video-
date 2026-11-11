"""Write DOWNLOADS.md: a phone-friendly list of every finished Ask The Elders / Crib Committee Short
(Releases tiktok-<channel>) with a direct download link and the paste-ready TikTok caption.

Open it on the phone at https://github.com/<owner>/<repo>/blob/main/DOWNLOADS.md (no app needed).
The repo is public, so the release links download straight away, no login.

Usage: python tools/make_downloads_page.py   (needs `gh` with GH_TOKEN; flow-import runs it after every Short)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNELS = [("elders", "Ask The Elders"), ("cribcommittee", "The Crib Committee")]
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
           "Newest first. Updated automatically after every new Short.", ""]
    for ch, name in CHANNELS:
        tag = f"tiktok-{ch}"
        try:
            assets = json.loads(gh("release", "view", tag, "--json", "assets"))["assets"]
        except RuntimeError as e:
            print(f"!! {tag}: {e}", file=sys.stderr)
            continue
        by_name = {a["name"]: a for a in assets}
        vids = sorted((a for a in assets if a["name"].endswith(".mp4")), key=lambda a: a["name"], reverse=True)[:KEEP]
        out += [f"## {name}", ""]
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
