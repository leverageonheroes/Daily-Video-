"""Hashtags and keywords for every platform, from the episode's own tags + channel.json `seo`.

channel.json "seo": {"about": "...keyword-rich sentence about the show...",
                     "hashtags": ["#core1", "#core2"],          # broad channel hashtags, after the topic ones
                     "keywords": ["..."]}                       # extra YouTube tags
Hashtag rules per platform (kept small on purpose: more than ~5 hurts reach or is ignored):
  YouTube  2 topic + 2 core + #shorts   (YouTube shows the first 3 above the title)
  Instagram/Facebook  2 topic + 2 core + #reels   (Instagram allows at most 5 hashtags)
  TikTok   2 topic + 2 core + #fyp
"""
import re

PLATFORM_TAG = {"youtube": "#shorts", "meta": "#reels", "tiktok": "#fyp"}
GENERIC = {"shorts", "short", "reels", "fyp", "ai animation", "animation"}


def _hashtag(t: str) -> str:
    return "#" + re.sub(r"[^\w]", "", t.lower().lstrip("#"))


def seo(bible: dict) -> dict:
    return (bible or {}).get("seo", {})


def hashtags(bible: dict, tags: list, platform: str = "youtube", topic: int = 2) -> list:
    show = _hashtag((bible or {}).get("show_title", ""))
    core = [_hashtag(h) for h in seo(bible).get("hashtags", [])]
    out: list[str] = []
    for t in tags or []:
        h = _hashtag(t)
        if len(out) >= topic:
            break
        if len(h) > 2 and t.lower().strip("#") not in GENERIC and h != show and h not in core and h not in out:
            out.append(h)
    out += [h for h in core[:2] if h not in out]
    out.append(PLATFORM_TAG[platform])
    return list(dict.fromkeys(out))


def hashtag_line(bible: dict, tags: list, platform: str = "youtube") -> str:
    return " ".join(hashtags(bible, tags, platform))


def youtube_tags(bible: dict, tags: list) -> list:
    """Episode tags first, then channel keywords + show title; within YouTube's 500-character tag limit."""
    out: list[str] = []
    size = 0
    for t in list(tags or []) + seo(bible).get("keywords", []) + [(bible or {}).get("show_title", "")]:
        t = t.strip().lstrip("#")
        if not t or t.lower() in GENERIC or t.lower() in {o.lower() for o in out}:
            continue
        cost = len(t) + (2 if " " in t else 0) + 1
        if size + cost > 480:
            break
        out.append(t)
        size += cost
    return out


def about(bible: dict) -> str:
    return seo(bible).get("about", "")


def strip_hashtag_lines(text: str) -> str:
    """Drop trailing lines made only of hashtags (so another platform's set can replace them)."""
    lines = text.rstrip().split("\n")
    while lines and lines[-1].strip() and all(w.startswith("#") for w in lines[-1].split()):
        lines.pop()
    return "\n".join(lines).rstrip()
