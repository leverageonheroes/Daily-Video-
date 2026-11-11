"""Google Veo 3.1 (Gemini API) image-to-video with native dialogue audio. Standard library only.

OPTIONAL provider. Google shut the Veo 3.1 *preview* IDs on the Gemini API on 22 Oct 2026, so Moral Of The Story
uses fal (fal-ai/veo3.1/lite) instead. Only use this with a VEO_MODEL id that Google currently lists.
Flow: POST models/<model>:predictLongRunning (prompt + first-frame image) -> poll the operation -> download.
Env: GEMINI_API_KEY (required), VEO_MODEL, VEO_RESOLUTION (720p), VEO_TIMEOUT_SECONDS.
Verify the request shape against https://ai.google.dev/gemini-api/docs/video before the first paid run.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://generativelanguage.googleapis.com/v1beta"


class VeoError(RuntimeError):
    pass


def _key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise VeoError("GEMINI_API_KEY is not set")
    return k


def _req(method, url, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"x-goog-api-key": _key(), "Content-Type": "application/json",
                                          "User-Agent": "shorts-studio"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise VeoError(f"HTTP {e.code}: {e.read()[:400]!r}")


def image_to_video(image: Path, prompt: str, seconds: int, dest: Path, negative: str = "") -> Path:
    model = os.environ.get("VEO_MODEL", "")
    if not model:
        raise VeoError("VEO_MODEL is not set (the old preview IDs were shut down)")
    secs = 8 if seconds > 6 else (6 if seconds > 4 else 4)          # Veo clips are 4, 6 or 8 s
    mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
    params = {"aspectRatio": "9:16", "resolution": os.environ.get("VEO_RESOLUTION", "720p"),
              "durationSeconds": secs, "personGeneration": "allow_adult"}
    if negative:
        params["negativePrompt"] = negative
    op = _req("POST", f"{BASE}/models/{model}:predictLongRunning", {
        "instances": [{"prompt": prompt[:3800],
                       "image": {"inlineData": {"data": base64.b64encode(image.read_bytes()).decode(),
                                 "mimeType": mime}}}],
        "parameters": params})
    name = op.get("name")
    if not name:
        raise VeoError(f"no operation returned: {str(op)[:300]}")
    deadline = time.time() + int(os.environ.get("VEO_TIMEOUT_SECONDS", "900"))
    while time.time() < deadline:
        time.sleep(10)
        st = _req("GET", f"{BASE}/{name}")
        if st.get("error"):
            raise VeoError(f"generation failed: {st['error']}")
        if st.get("done"):
            resp = st.get("response", {})
            samples = (resp.get("generateVideoResponse") or resp).get("generatedSamples") or \
                      (resp.get("generateVideoResponse") or resp).get("generatedVideos") or []
            if not samples:
                raise VeoError(f"no video in response (possibly blocked by safety filters): {str(st)[:400]}")
            uri = samples[0].get("video", {}).get("uri")
            if not uri:
                raise VeoError(f"no video uri: {str(samples[0])[:300]}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(uri, headers={"x-goog-api-key": _key(), "User-Agent": "shorts-studio"})
            with urllib.request.urlopen(req, timeout=300) as r:
                dest.write_bytes(r.read())
            return dest
    raise VeoError("timed out waiting for Veo")
