"""Production state (state/state.json). Lets any session or scheduled run resume where the last one stopped.

Statuses in order: scripted -> rendered -> uploaded -> published   (or failed)
  rendered  = final.mp4 exists in output/<channel>/<id>/
  uploaded  = on YouTube as private (scheduled to auto-publish after the review window)
  published = confirmed public (set by `python -m pipeline.run sync-youtube`)
"""
import datetime as dt
import json

from .config import CHANNELS_DIR, MOCK, ROOT

# mock runs keep their own state file, so testing never changes real progress
STATE = ROOT / "state" / ("state.mock.json" if MOCK else "state.json")
ORDER = ["scripted", "rendered", "uploaded", "published"]
BUFFER_MIN = 7


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load():
    s = json.loads(STATE.read_text()) if STATE.exists() else {"channels": {}}
    return sync(s)


def save(s):
    # Only touch the timestamp when something really changed: a bare timestamp bump makes parallel
    # workflow runs conflict on state.json when they push.
    if STATE.exists():
        old = json.loads(STATE.read_text())
        if {k: v for k, v in old.items() if k != "updated"} == {k: v for k, v in s.items() if k != "updated"}:
            return
    s["updated"] = now()
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2) + "\n")


def episodes(channel):
    eps = []
    for f in sorted((CHANNELS_DIR / channel / "episodes").glob("*.json")):
        eps += json.loads(f.read_text())["episodes"]
    return eps


def get_episode(channel, ep_id):
    for e in episodes(channel):
        if e["id"] == ep_id:
            return e
    raise KeyError(ep_id)


def sync(s):
    for ch_dir in sorted(CHANNELS_DIR.iterdir()):
        ch = s["channels"].setdefault(ch_dir.name, {"episodes": {}})
        ids = [e["id"] for e in episodes(ch_dir.name)]
        gone = [k for k in ch["episodes"] if k not in set(ids)]
        if gone and ids:
            # scripts were replaced (new format): keep the old records out of the way, and restart the
            # compilation trackers if the episode numbering restarted with a new id prefix
            arch = ch.setdefault("archived", {})
            for k in gone:
                arch[k] = ch["episodes"].pop(k)
            new_prefix = ids[0].split("-")[0]
            if all(k.split("-")[0] != new_prefix for k in gone):
                for t in ("last_compiled", "last_compiled_weekly"):
                    if ch.get(t):
                        ch.setdefault("archived_trackers", {})[t] = ch[t]
                        ch[t] = 0
        for ep_id in ids:
            rec = ch["episodes"].setdefault(ep_id, {"status": "scripted", "history": []})
            rec.setdefault("attempts", 0)
            if rec["status"] == "approved":   # legacy status from the first version
                rec["status"] = "rendered"
        ch["last_scripted"] = ids[-1] if ids else None
    return s


def mark(s, channel, ep_id, status, note="", **extra):
    if status not in ORDER + ["failed"]:
        raise ValueError(status)
    rec = s["channels"][channel]["episodes"][ep_id]
    rec["status"] = status
    rec.update(extra)
    rec["history"].append({"status": status, "at": now(), "note": note})


def next_episode(s, channel, wanted=("scripted", "failed"), max_attempts=3):
    for ep_id, rec in s["channels"][channel]["episodes"].items():
        if rec["status"] in wanted and rec.get("attempts", 0) < max_attempts:
            return ep_id
    return None


def counts(s, channel):
    c = {k: 0 for k in ORDER + ["failed"]}
    for rec in s["channels"][channel]["episodes"].values():
        c[rec["status"]] += 1
    return c


def buffer_low(s, channel):
    return counts(s, channel)["scripted"] < BUFFER_MIN
