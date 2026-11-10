"""Facebook + Instagram via the Meta Graph API (standard library only): Stories, Reels and the feed.

Every episode goes to: Facebook Story, Facebook Reel (also shows on the Page feed; videos over 90 s, which
Facebook Reels reject, become a normal Page video post instead), Instagram Story and Instagram Reel with
share_to_feed (Instagram's API publishes feed videos as Reels, so this is the feed post too).
Everything goes live immediately and is visible to everyone; no manual publishing.
Env per channel (prefix from META_PREFIX): <PREFIX>_FB_ID, <PREFIX>_IG_ID.
Token: <PREFIX>_TOKEN, else META_TOKEN (a System User token with pages_manage_posts, pages_read_engagement,
pages_show_list, publish_video, instagram_basic, instagram_content_publish). The page's own token is fetched from it.
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

from . import seo

VERSION = os.environ.get("META_GRAPH_VERSION", "v23.0")
GRAPH = f"https://graph.facebook.com/{VERSION}"
RUPLOAD = "https://rupload.facebook.com"
MAX_STORY_SECONDS = 59.5
MAX_FB_REEL_SECONDS = 90
AI_DISCLOSURE = "Made with AI-generated animation."
META_PREFIX = {"flat4b": "FLAT_4B", "coldhearts": "FRIDGE_HEARTS", "drizzlepudge": "DRIZZLE_AND_PUDGE",
               "elders": "ELDERS", "cribcommittee": "CRIBCOMMITTEE"}
TOKEN_NAMES = ("META_TOKEN", "META_SYSTEM_USER_TOKEN", "SYSTEM_USER_TOKEN", "META_ACCESS_TOKEN")


class MetaError(RuntimeError):
    pass


def ids(channel):
    p = META_PREFIX.get(channel, channel.upper())
    token = os.environ.get(f"{p}_TOKEN") or next((os.environ[n] for n in TOKEN_NAMES if os.environ.get(n)), "")
    def get(kind):   # accepts <PREFIX>_FB_ID or FB_ID_<PREFIX> (e.g. ELDERS_FB_ID or FB_ID_ELDERS)
        return (os.environ.get(f"{p}_{kind}_ID") or os.environ.get(f"{kind}_ID_{p}") or "").strip()
    return get("FB"), get("IG"), token.strip()


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
    return _ig_publish(ig_id, token, video, media_type="STORIES")


def _encode(video: Path, out: Path, start=None, end=None) -> Path:
    """Re-encoded copy (Instagram rejects some original final.mp4 uploads with ProcessingFailedError)."""
    if not out.exists():
        cut = (["-ss", f"{start:.3f}", "-to", f"{end:.3f}"] if start is not None else [])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *cut, "-i", str(video), "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                        "-movflags", "+faststart", str(out)], check=True)
    return out


def _bible(channel) -> dict:
    p = Path(__file__).resolve().parents[1] / "channels" / channel / "channel.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def caption(video: Path, episode: dict, bible: dict | None = None) -> tuple[str, str]:
    """(title, caption) from the episode's metadata.json (same text as YouTube) with Instagram/Facebook hashtags."""
    meta = {}
    mf = video.parent / "metadata.json"
    if mf.exists():
        try:
            meta = json.loads(mf.read_text())
        except ValueError:
            meta = {}
    title = (meta.get("title") or episode.get("title") or "").replace("#shorts", "").strip()
    desc = meta.get("description") or (episode.get("description", "") + "\n\n" + AI_DISCLOSURE)
    desc = seo.strip_hashtag_lines(desc.replace("#shorts", ""))
    desc = f"{desc}\n\n{seo.hashtag_line(bible or {}, episode.get('tags') or meta.get('tags', []), 'meta')}"
    return title, f"{title}\n\n{desc}".strip()[:2200]


def facebook_reel(fb_id, token, video: Path, text: str) -> str:
    start = _post(f"{fb_id}/video_reels", token, upload_phase="start")
    _rupload(start["upload_url"], token, video)
    done = _post(f"{fb_id}/video_reels", token, upload_phase="finish", video_id=start["video_id"],
                 video_state="PUBLISHED", description=text)
    if not done.get("success", True):
        raise MetaError(f"Facebook reel not published: {done}")
    return str(done.get("post_id") or start["video_id"])


def facebook_video(fb_id, token, video: Path, title: str, text: str) -> str:
    """Normal Page video post (feed), for videos too long to be a Facebook Reel."""
    boundary = f"----shorts{int(time.time() * 1000)}"
    fields = {"title": title[:250], "description": text, "published": "true", "access_token": token}
    body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                    for k, v in fields.items())
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="source"; filename="{video.name}"\r\n'
             f"Content-Type: video/mp4\r\n\r\n").encode() + video.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    r = _call("POST", f"https://graph-video.facebook.com/{VERSION}/{fb_id}/videos", data=body, timeout=900,
              headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return str(r.get("id"))


def _ig_publish(ig_id, token, video: Path, **fields) -> str:
    box = _post(f"{ig_id}/media", token, upload_type="resumable", **fields)
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


def instagram_reel(ig_id, token, video: Path, text: str) -> str:
    return _ig_publish(ig_id, token, video, media_type="REELS", caption=text, share_to_feed="true")


def story_parts(video: Path, episode: dict, total: float) -> list[Path]:
    """<= 60 s: one re-encoded copy (Instagram rejects some original final.mp4 uploads with ProcessingFailedError).
    Longer: cut at the shot boundary closest to equal parts."""
    n = 1 if total <= MAX_STORY_SECONDS else int(total // MAX_STORY_SECONDS) + 1
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
        parts.append(_encode(video, video.parent / f"story_{i + 1}.mp4", edges[i], edges[i + 1]))
    return parts


def _retry_once(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print(f"   {fn.__name__} failed ({e}); retrying once in 30 s")
        time.sleep(30)
        return fn(*args)


PLACEMENTS = ("facebook", "instagram", "facebook_reel", "instagram_reel")   # facebook/instagram = Stories


def post_stories(channel, video: Path, episode: dict, total: float, done: dict, placements=PLACEMENTS) -> dict:
    """Posts every placement (of `placements`) not already in `done` (so reruns never double-post).
    Returns {"facebook": [story ids], "instagram": [story ids], "facebook_reel": id, "instagram_reel": id}."""
    fb_id, ig_id, token = ids(channel)
    if not token:
        raise MetaError("No Meta token: set META_TOKEN (System User token) in .env / GitHub secrets")
    ptoken = page_token(fb_id, token) if fb_id else token
    title, text = caption(video, episode, _bible(channel))
    full = None
    out, errors = dict(done), []
    for name in placements:
        target = fb_id if name.startswith("facebook") else ig_id
        if not target or out.get(name):
            continue
        try:
            if name in ("facebook", "instagram"):
                parts = story_parts(video, episode, total)
                fn = facebook_story if name == "facebook" else instagram_story
                out[name] = [_retry_once(fn, target, ptoken, p) for p in parts]
                print(f"   {name} story posted ({len(parts)} part{'s' * (len(parts) > 1)})")
                continue
            full = full or _encode(video, video.parent / "reel.mp4")
            if name == "instagram_reel":
                out[name] = _retry_once(instagram_reel, target, ptoken, full, text)
                print("   instagram reel posted (shared to feed)")
            elif total <= MAX_FB_REEL_SECONDS:
                out[name] = _retry_once(facebook_reel, target, ptoken, full, text)
                print("   facebook reel posted")
            else:
                out[name] = _retry_once(facebook_video, target, ptoken, full, title, text)
                print(f"   facebook feed video posted ({total:.0f} s is too long for a Facebook Reel)")
        except Exception as e:
            errors.append(f"{name}: {e}")
    if errors:
        out["errors"] = errors
    return out
