"""Lightricks LTX API (api.ltx.io) - direct, cheapest route for LTX-2.3 (720p: $0.03/s Fast, $0.04/s Pro).

Flow (per docs.ltx.io): POST /v1/upload -> PUT image to upload_url -> POST /v2/image-to-video with
image_uri=ltx://... -> poll GET /v2/image-to-video/{id} (pending -> processing -> completed|failed)
-> download result.video_url (URLs expire, so download immediately).
Uses only the standard library, so no extra packages are needed.
"""
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config


class LTXError(RuntimeError):
    pass


def _req(method, url, body=None, headers=None, timeout=120, raw=None):
    h = {"Authorization": f"Bearer {config.LTX_API_KEY}", "User-Agent": "shorts-studio"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    if raw is not None:
        data = raw
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read()
            return json.loads(txt) if txt and r.headers.get_content_type() == "application/json" else txt
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise LTXError(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {detail}") from e


def _with_retries(fn, what, tries=3):
    last = None
    for i in range(tries):
        try:
            return fn()
        except LTXError as e:
            last = e
            msg = str(e)
            if any(f"HTTP {c}" in msg for c in ("400", "401", "402", "413", "422")):
                raise  # bad request / bad key / no credit: retrying won't help
            wait = 15 * (i + 1) if "HTTP 429" in msg else 6 * (i + 1)
            print(f"   LTX {what} failed (attempt {i + 1}): {msg[:160]} - retrying in {wait}s")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(6 * (i + 1))
    raise LTXError(f"{what} failed after {tries} attempts: {last}")


def upload(path: Path) -> str:
    """Upload a local image, return its ltx:// storage URI (kept by LTX for 24 h)."""
    base = config.LTX_BASE_URL

    def go():
        info = _req("POST", f"{base}/v1/upload", body={})
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        put = urllib.request.Request(info["upload_url"], data=path.read_bytes(), method="PUT",
                                     headers={**info.get("required_headers", {}), "Content-Type": mime})
        try:
            with urllib.request.urlopen(put, timeout=300):
                pass
        except urllib.error.HTTPError as e:
            raise LTXError(f"PUT upload -> HTTP {e.code}: {e.read()[:300]!r}") from e
        return info["storage_uri"]

    return _with_retries(go, "upload")


def _find_video_url(result) -> str | None:
    if isinstance(result, dict):
        for k in ("video_url", "url", "video"):
            v = result.get(k)
            if isinstance(v, str) and v.startswith("http"):
                return v
            if isinstance(v, dict):
                found = _find_video_url(v)
                if found:
                    return found
        for v in result.values():
            found = _find_video_url(v)
            if found:
                return found
    return None


def image_to_video(image: Path, prompt: str, seconds: int, dest: Path) -> Path:
    base = config.LTX_BASE_URL
    image_uri = upload(image)
    body = {
        "image_uri": image_uri,
        "prompt": prompt[:5000],
        "model": config.LTX_MODEL,
        "duration": seconds,
        "resolution": config.LTX_RESOLUTION,
        "fps": config.VIDEO_FPS,
        "generate_audio": config.GENERATE_AUDIO,
    }
    job = _with_retries(lambda: _req("POST", f"{base}/v2/image-to-video", body=body), "submit")
    job_id = job["id"]
    deadline = time.time() + config.LTX_TIMEOUT_SECONDS
    while True:
        time.sleep(5 + random.random())  # docs: poll no faster than every ~5 s, with jitter
        st = _with_retries(lambda: _req("GET", f"{base}/v2/image-to-video/{job_id}"), "status")
        status = st.get("status")
        if status == "completed":
            url = _find_video_url(st.get("result") or st)
            if not url:
                raise LTXError(f"job {job_id} completed but no video URL in response: {str(st)[:300]}")
            break
        if status == "failed":
            raise LTXError(f"job {job_id} failed: {str(st.get('error') or st)[:300]}")
        if time.time() > deadline:
            raise LTXError(f"job {job_id} timed out after {config.LTX_TIMEOUT_SECONDS}s (last status {status})")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "shorts-studio"}),
                                timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest
