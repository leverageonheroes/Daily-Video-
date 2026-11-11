"""YouTube upload. One OAuth token per channel, from env YT_TOKEN_<CHANNEL> (JSON) or secrets/youtube_<channel>.json."""
import datetime as dt
import json
import os

from . import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def credentials(channel: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    raw = os.environ.get(f"YT_TOKEN_{channel.upper()}") or (os.environ.get("YT_TOKEN_CRIB") if channel == "cribcommittee" else None)
    path = config.SECRETS / f"youtube_{channel}.json"
    if not raw and path.exists():
        raw = path.read_text()
    if not raw:
        raise RuntimeError(f"No YouTube token for {channel}. Run: python tools/auth_youtube.py {channel}")
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return creds


def service(channel: str):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=credentials(channel), cache_discovery=False)


def _category(channel: str) -> str:
    try:
        bible = json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())
        return str(bible.get("youtube_category") or config.YT_CATEGORY.get(channel, "24"))
    except FileNotFoundError:
        return config.YT_CATEGORY.get(channel, "24")


def _review_hours(channel: str) -> float:
    """channel.json "review_hours" wins (staggers publish times between channels), else REVIEW_HOURS."""
    try:
        bible = json.loads((config.CHANNELS_DIR / channel / "channel.json").read_text())
        if bible.get("review_hours") is not None:
            return float(bible["review_hours"])
    except (FileNotFoundError, ValueError):
        pass
    return config.REVIEW_HOURS


def upload(channel: str, video_path, meta: dict) -> dict:
    from googleapiclient.http import MediaFileUpload

    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
        "containsSyntheticMedia": True,
    }
    publish_at = None
    if meta.get("publish_at"):          # fixed publish time (e.g. carousel videos)
        publish_at = meta["publish_at"]
        status["publishAt"] = publish_at
    elif os.environ.get("YT_PUBLISH_NOW") == "1":      # public straight away, no review window
        status["privacyStatus"] = "public"
    elif _review_hours(channel) > 0:
        when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=_review_hours(channel))
        publish_at = when.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": _category(channel),
        },
        "status": status,
    }
    req = service(channel).videos().insert(
        part="snippet,status", body=body, notifySubscribers=True,
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return {"youtube_id": resp["id"], "publish_at": publish_at}


def privacy(channel: str, video_ids: list) -> dict:
    out = {}
    yt = service(channel)
    for i in range(0, len(video_ids), 50):
        r = yt.videos().list(part="status", id=",".join(video_ids[i:i + 50])).execute()
        for item in r.get("items", []):
            out[item["id"]] = item["status"]["privacyStatus"]
    return out


def channel_title(channel: str) -> str:
    r = service(channel).channels().list(part="snippet", mine=True).execute()
    items = r.get("items", [])
    return items[0]["snippet"]["title"] if items else "(no channel found)"
