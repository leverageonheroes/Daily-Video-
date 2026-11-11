"""Growth on autopilot, for every channel (cheap API calls, no uploads):

  python -m pipeline.run engage [ch...]     # question comment + theme playlists on newly PUBLIC videos
  python -m pipeline.run insights [ch...]   # weekly: views per format/theme -> state/insights.json + reports/insights.md

Settings per channel: channels/<ch>/engage.json ("questions" by format, "playlists" with keyword rules).
State: state/engage.json (commented / playlisted video ids, playlist ids, daily action count).
Comments and playlists need the youtube.force-ssl login (tools/auth_youtube.py); channels still on the older
upload-only login are skipped with a note. Insights only need the read-only permission every login has.

Quota: all channels share one Google project (10,000 units/day, an upload = 1,600). Each comment or playlist
insert costs 50, so engage spends at most MAX_ACTIONS_PER_DAY * 50 = 1,000 units per Pacific day (all channels).
"""
import datetime as dt
import hashlib
import json
import re
import statistics
from pathlib import Path

from . import config, youtube

STATE = config.ROOT / "state" / ("engage.mock.json" if config.MOCK else "engage.json")
INSIGHTS = config.ROOT / "state" / "insights.json"
REPORT = config.ROOT / "reports" / "insights.md"
MAX_ACTIONS_PER_DAY = 20          # all channels together: 20 * 50 = 1,000 units (uploads keep the other 9,000)
COMMENT_MAX_AGE_DAYS = 10         # don't comment on old videos (a fresh question looks natural, a late one doesn't)


def pacific_day():
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


def _load(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def _save(p: Path, data):
    p.parent.mkdir(exist_ok=True)
    data["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def settings(ch):
    p = config.CHANNELS_DIR / ch / "engage.json"
    return json.loads(p.read_text()) if p.exists() else None


def bible(ch):
    return json.loads((config.CHANNELS_DIR / ch / "channel.json").read_text())


# ---------------------------------------------------------------- what each video is (format + theme)
def known_videos(ch) -> dict:
    """youtube_id -> {"format", "theme", "id"} from our own state files (main Shorts, carousels, extras)."""
    out = {}
    themes = {}
    for f in sorted((config.CHANNELS_DIR / ch / "episodes").glob("*.json")):
        for e in json.loads(f.read_text())["episodes"]:
            themes[e["id"]] = e.get("theme") or ""
    st = _load(config.ROOT / "state" / "state.json", {"channels": {}})
    for ep_id, rec in st["channels"].get(ch, {}).get("episodes", {}).items():
        if rec.get("youtube_id"):
            out[rec["youtube_id"]] = {"format": "main", "theme": themes.get(ep_id, ""), "id": ep_id}
    for kind, path in (("carousel", "carousel.json"), (None, "extras.json")):
        s = _load(config.ROOT / "state" / path, {"channels": {}})
        for key, cst in s["channels"].items():
            # carousel state is keyed by channel; extras by "<channel>:<format>"
            c, _, fmt = key.partition(":")
            if c != ch:
                continue
            for ep_id, rec in cst.get("done", {}).items():
                if rec.get("youtube_id"):
                    out[rec["youtube_id"]] = {"format": kind or fmt, "theme": rec.get("theme", ""), "id": ep_id}
    return out


def uploads(yt, limit=200):
    """Every video on the channel, newest first: [{id, title, privacy, published, views, likes, comments}]."""
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while len(ids) < limit:
        r = yt.playlistItems().list(part="contentDetails", playlistId=pl, maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    out = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,status,statistics", id=",".join(ids[i:i + 50])).execute()
        for it in r.get("items", []):
            stt = it.get("statistics", {})
            out.append({"id": it["id"], "title": it["snippet"]["title"], "privacy": it["status"]["privacyStatus"],
                        "published": it["snippet"]["publishedAt"], "views": int(stt.get("viewCount", 0)),
                        "likes": int(stt.get("likeCount", 0)), "comments": int(stt.get("commentCount", 0))})
    return out


def classify(cfg, video, known):
    k = known.get(video["id"])
    fmt = k["format"] if k else "other"
    for rule in cfg.get("formats_by_title", []):            # fallback for videos made before tracking
        if not k and re.search(rule["match"], video["title"], re.I):
            fmt = rule["format"]
            break
    theme = (k or {}).get("theme") or ""
    return fmt, theme


# ---------------------------------------------------------------- comments + playlists
def _pick(options, seed):
    return options[int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(options)]


def playlist_targets(cfg, video, fmt, theme):
    text = f"{video['title']} {theme} {fmt}".lower()
    names = []
    for p in cfg.get("playlists", []):
        if "formats" in p and fmt not in p["formats"]:
            continue
        if not p.get("match") or any(re.search(m, text) for m in p["match"]):
            names.append(p["name"])
    return names


def ensure_playlist(yt, st, name, desc, kids):
    if name in st["playlists"]:
        return st["playlists"][name]
    token = None
    while True:                      # reuse a playlist of that name if it already exists on the channel
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=token).execute()
        for it in r.get("items", []):
            if it["snippet"]["title"] == name:
                st["playlists"][name] = it["id"]
                return it["id"]
        token = r.get("nextPageToken")
        if not token:
            break
    body = {"snippet": {"title": name, "description": desc}, "status": {"privacyStatus": "public"}}
    pid = yt.playlists().insert(part="snippet,status", body=body).execute()["id"]
    st["playlists"][name] = pid
    print(f"   + playlist '{name}'")
    return pid


def engage_channel(s, ch):
    cfg = settings(ch)
    if not cfg:
        return
    if not youtube.can_manage(ch):
        print(f"   {ch}: login is upload-only - comments/playlists skipped (re-login: python tools/auth_youtube.py {ch})")
        return
    st = s["channels"].setdefault(ch, {"commented": [], "playlisted": [], "playlists": {}})
    if s.get("day") != pacific_day():
        s["day"], s["actions"] = pacific_day(), 0
    yt = youtube.service(ch)
    kids = bool(bible(ch).get("made_for_kids"))
    known = known_videos(ch)
    now = dt.datetime.now(dt.timezone.utc)
    vids = [v for v in uploads(yt, limit=100) if v["privacy"] == "public"]
    def capped():
        if s["actions"] >= MAX_ACTIONS_PER_DAY:
            print(f"   {ch}: daily cap reached ({MAX_ACTIONS_PER_DAY} comments/playlist adds) - rest tomorrow")
            return True
        return False

    # 1) question comment on fresh public videos, newest first (most valuable while the video is new)
    qs = cfg.get("questions", {})
    for v in vids:
        if v["id"] in st["commented"]:
            continue
        age = (now - dt.datetime.fromisoformat(v["published"].replace("Z", "+00:00"))).days
        fmt, theme = classify(cfg, v, known)
        q = qs.get(fmt) or qs.get("default")
        if kids or not q or fmt == "other" or age > COMMENT_MAX_AGE_DAYS:
            st["commented"].append(v["id"])       # never: kids channel / no questions / unknown video / too old
            continue
        if capped():
            break
        text = _pick(q, v["id"])
        try:
            yt.commentThreads().insert(part="snippet", body={"snippet": {
                "videoId": v["id"], "topLevelComment": {"snippet": {"textOriginal": text}}}}).execute()
            print(f"   {ch}: {v['id']} commented: {text}")
        except Exception as e:
            if youtube.is_quota_error(e):
                raise
            print(f"   {ch}: comment on {v['id']} failed: {str(e)[:150]}")
        s["actions"] += 1
        st["commented"].append(v["id"])
    # 2) theme playlists, oldest first so each playlist plays in upload order
    for v in reversed(vids):
        fmt, theme = classify(cfg, v, known)
        todo = [n for n in playlist_targets(cfg, v, fmt, theme) if f"{v['id']}|{n}" not in st["playlisted"]]
        if todo and capped():
            break
        for name in todo:
            key = f"{v['id']}|{name}"
            pid = ensure_playlist(yt, st, name, cfg.get("playlist_description", ""), kids)
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": v["id"]}}}).execute()
            s["actions"] += 1
            st["playlisted"].append(key)
            print(f"   {ch}: {v['id']} -> playlist '{name}'")
    st["commented"], st["playlisted"] = st["commented"][-500:], st["playlisted"][-1500:]


PRIORITY = ["elders", "cribcommittee", "coldhearts", "flat4b", "drizzlepudge"]   # who gets the daily cap first


def run_engage(argv):
    s = _load(STATE, {"channels": {}})
    failed = False
    for ch in argv or sorted(config.CHANNELS, key=lambda c: PRIORITY.index(c) if c in PRIORITY else 99):
        try:
            engage_channel(s, ch)
        except Exception as e:
            failed = True
            print(f"!! {ch}: engage failed: {str(e)[:300]}")
            if youtube.is_quota_error(e):
                print("!! YouTube quota used up for today - stopping (resumes after midnight Pacific)")
                _save(STATE, s)
                return False
        _save(STATE, s)
    return failed


# ---------------------------------------------------------------- weekly insights
def run_insights(argv):
    data = {"channels": {}}
    lines = [f"# What's working ({dt.date.today().isoformat()})", "",
             "Views per video type and theme. Videos younger than 2 days are left out. A score of 1.5 means a theme "
             "gets 1.5x the usual views for that video type. New carousels / extras pick the best-scoring theme "
             "from their next 5 scripts.", ""]
    now = dt.datetime.now(dt.timezone.utc)
    for ch in argv or config.CHANNELS:
        cfg = settings(ch) or {}
        try:
            vids = uploads(youtube.service(ch), limit=300)
        except Exception as e:
            print(f"!! {ch}: insights failed: {str(e)[:200]}")
            continue
        known = known_videos(ch)
        rows = []
        for v in vids:
            age = (now - dt.datetime.fromisoformat(v["published"].replace("Z", "+00:00"))).total_seconds() / 86400
            if v["privacy"] != "public" or age < 2:
                continue
            fmt, theme = classify(cfg, v, known)
            rows.append({**v, "format": fmt, "theme": theme, "age_days": round(age, 1)})
        med = {}
        for fmt in {r["format"] for r in rows}:
            med[fmt] = max(1.0, statistics.median(r["views"] for r in rows if r["format"] == fmt))
        themes = {}
        for r in rows:
            if r["theme"]:
                themes.setdefault(r["theme"], []).append(r["views"] / med[r["format"]])
        score = {t: round(sum(v) / len(v), 2) for t, v in themes.items() if len(v) >= 2}   # 1 video = luck
        fmts = {f: {"videos": sum(1 for r in rows if r["format"] == f), "median_views": med[f],
                    "total_views": sum(r["views"] for r in rows if r["format"] == f)} for f in med}
        data["channels"][ch] = {"theme_score": score, "formats": fmts,
                                "top": sorted(rows, key=lambda r: -r["views"])[:10]}
        lines += [f"## {ch}", "", "| type | videos | median views | total views |", "|---|---|---|---|"]
        lines += [f"| {f} | {v['videos']} | {v['median_views']:.0f} | {v['total_views']} |"
                  for f, v in sorted(fmts.items(), key=lambda x: -x[1]["median_views"])]
        best = sorted(score.items(), key=lambda x: -x[1])
        if best:
            lines += ["", "Best themes: " + ", ".join(f"{t} ({sc})" for t, sc in best[:6]),
                      "Weakest: " + ", ".join(f"{t} ({sc})" for t, sc in best[-3:])]
        lines += ["", "Top videos:"] + [f"- {r['views']} views: {r['title']} ({r['format']})"
                                        for r in data["channels"][ch]["top"][:5]] + [""]
        print(f"   {ch}: {len(rows)} videos analysed")
    _save(INSIGHTS, data)
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"   wrote {REPORT.relative_to(config.ROOT)}")
    return False


# ---------------------------------------------------------------- used by carousel / extras to pick the next script
def pick_episode(ch, episodes, used: set, window=5):
    """Index (0-based) of the next script to make: among the next `window` unused ones, the best-scoring theme."""
    free = [i for i in range(len(episodes)) if i not in used][:window]
    if not free:
        return None
    score = _load(INSIGHTS, {"channels": {}})["channels"].get(ch, {}).get("theme_score", {})
    return max(free, key=lambda i: (score.get(episodes[i].get("theme", ""), 1.0), -i))
