"""Facebook Page Stories + Instagram Stories via the Meta Graph API (standard library only).

Stories posted through the API go live immediately and are visible to everyone; no manual publishing.
Env per channel (prefix from META_PREFIX): <PREFIX>_FB_ID, <PREFIX>_IG_ID.
Token: <PREFIX>_TOKEN, else META_TOKEN (a System User token with pages_manage_posts, pages_read_engagement,
pages_show_list, instagram_basic, instagram_content_publish). The page's own token is fetched from it.
Stories max out at 60 s, so longer videos are split at shot boundaries into consecutive story frames.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{VERSION}"
RUPLOAD = "https://rupload.facebook.com"
MAX_STORY_SECONDS = 59.5
META_PREFIX = {"flat4b": "FLAT_4B", "coldhearts": "FRIDGE_HEARTS", "drizzlepudge": "DRIZZLE_AND_PUDGE"}
TOKEN_NAMES = ("META_TOKEN", "META_SYSTEM_USER_TOKEN", "SYSTEM_USER_TOKEN", "META_ACCESS_TOKEN")


class MetaError(RuntimeError):
    pass


def ids(channel):
    p = META_PREFIX.get(channel, channel.upper())
    token = os.environ.get(f"{p}_TOKEN") or next((os.environ[n] for n in TOKEN_NAMES if os.environ.get(n)), "")
    return os.environ.get(f"{p}_FB_ID", ""), os.environ.get(f"{p}_IG_ID", ""), token.strip()


def enabled(channel):
    fb, ig, token = ids(channel)
    return bool(token and (fb or ig))


def _call(method, url, params=None, data=None, headers=None, timeout=300):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise MetaError(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {e.read().decode(errors='replace')[:400]}") from e


def _post(path, token, **fields):
    body = urllib.parse.urlencode({**fields, "access_token": token}).encode()
    return _call("POST", f"{GRAPH}/{path}", data=body)


def _rupload(url, token, video: Path):
    return _call("POST", url, data=video.read_bytes(), timeout=600, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(video.stat().st_size)})


def page_token(fb_id, token):
    """System-user token -> the page's own access token (falls back to the given token)."""
    try:
        return _call("GET", f"{GRAPH}/{fb_id}", {"fields": "access_token", "access_token": token}).get("access_token") or token
    except MetaError:
        return token


def facebook_story(fb_id, token, video: Path) -> str:
    start = _post(f"{fb_id}/video_stories", token, upload_phase="start")
    _rupload(start["upload_url"], token, video)
    done = _post(f"{fb_id}/video_stories", token, upload_phase="finish", video_id=start["video_id"])
    if not done.get("success", True):
        raise MetaError(f"Facebook story not published: {done}")
    return str(done.get("post_id") or start["video_id"])


def instagram_story(ig_id, token, video: Path) -> str:
    box = _post(f"{ig_id}/media", token, media_type="STORIES", upload_type="resumable")
    _rupload(f"{RUPLOAD}/ig-api-upload/{VERSION}/{box['id']}", token, video)
    for _ in range(60):                      # processing usually takes 10-60 s
        st = _call("GET", f"{GRAPH}/{box['id']}", {"fields": "status_code,status", "access_token": token})
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise MetaError(f"Instagram processing failed: {st}")
        time.sleep(10)
    else:
        raise MetaError("Instagram processing timed out")
    return str(_post(f"{ig_id}/media_publish", token, creation_id=box["id"])["id"])


def story_parts(video: Path, episode: dict, total: float) -> list[Path]:
    """<= 60 s: the video itself. Longer: cut at the shot boundary closest to equal parts."""
    if total <= MAX_STORY_SECONDS:
        return [video]
    n = int(total // MAX_STORY_SECONDS) + 1
    bounds, t = [], 0.0
    for shot in episode["shots"][:-1]:
        t += shot["dur"]
        bounds.append(t)
    cuts, prev = [], 0.0
    for k in range(1, n):
        ok = [b for b in bounds if prev < b <= prev + MAX_STORY_SECONDS] or [prev + total / n]
        prev = min(ok, key=lambda b: abs(b - total * k / n))
        cuts.append(prev)
    edges, parts = [0.0, *cuts, total], []
    for i in range(len(edges) - 1):
        out = video.parent / f"story_{i + 1}.mp4"
        if not out.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{edges[i]:.3f}", "-to", f"{edges[i + 1]:.3f}",
                            "-i", str(video), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
        parts.append(out)
    return parts


def post_stories(channel, video: Path, episode: dict, total: float, done: dict) -> dict:
    """Posts to whichever of FB/IG isn't in `done` yet. Returns {"facebook": [...], "instagram": [...]}."""
    fb_id, ig_id, token = ids(channel)
    if not token:
        raise MetaError("No Meta token: set META_TOKEN (System User token) in .env / GitHub secrets")
    parts = story_parts(video, episode, total)
    ptoken = page_token(fb_id, token) if fb_id else token
    out, errors = dict(done), []
    for name, target, fn in (("facebook", fb_id, facebook_story), ("instagram", ig_id, instagram_story)):
        if not target or out.get(name):
            continue
        try:
            out[name] = [fn(target, ptoken, p) for p in parts]
            print(f"   {name} story posted ({len(parts)} part{'s' * (len(parts) > 1)})")
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        out["errors"] = errors
    return out
