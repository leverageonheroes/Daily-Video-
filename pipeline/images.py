"""Free text-to-image providers, tried in order (env IMAGE_PROVIDERS, default "cloudflare,together,pollinations").

  cloudflare   Cloudflare Workers AI, FLUX.1 [schnell]. Free 10,000 neurons/day (dozens of images), resets 00:00 UTC.
               env: CF_ACCOUNT_ID, CF_API_TOKEN (token permission: "Workers AI - Read")
  together     Together AI free FLUX.1-schnell-Free endpoint (rate-limited).   env: TOGETHER_API_KEY
  pollinations image.pollinations.ai (no key needed, throttled; optional POLLINATIONS_TOKEN removes limits/logo)
  gemini       Gemini 2.5 Flash Image, only if GEMINI_API_KEY is set (free tier availability changes often)

Standard library only. Every image is cached on disk, so reruns never regenerate.
"""
import base64
import json
import re
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

UA = {"User-Agent": "shorts-studio"}


class ImageError(RuntimeError):
    pass



def _env(*names):
    """First non-empty env var among names (secrets are often saved under slightly different names)."""
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return None

def _post(url, body, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={**UA, "Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ImageError(f"HTTP {e.code}: {e.read()[:300]!r}")


CF_ACCOUNT_NAMES = ("CF_ACCOUNT_ID", "CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT", "CLOUDFLARE_ACCOUNT", "CLOUDFLARE_ID",
                    "CF_ID", "CLOUDFLARE_ACC_ID", "CF_ACC_ID", "CLOUDFLARE_ACCOUNTID", "CF_ACCOUNTID", "ACCOUNT_ID",
                    "CLOUDFLARE_ACCOUNT_ACCOUNT_", "CLOUDFLARE_ACCOUNT_ACCOUNT", "CLOUDFLARE_CCOUNT_", "CLOUDFLARE_CCOUNT", "CLOUDFLARE_ACCOUNT_", "CLOUDFLARE_CCOUNT_ID", "CLOUDFLARE_ACCOUNT_ACCOUNT_ID")
CF_TOKEN_NAMES = ("CF_API_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_KEY", "CLOUDFLARE_API_KEY", "CLOUDFLARE_API",
                  "CF_API", "CLOUDFLARE_TOKEN", "CF_TOKEN", "CLOUDFLARE_KEY", "CF_KEY")
_CF_ACCT: dict = {}


def _cf_account_scan():
    """Account id saved under an unexpected name (or as a GitHub Variable): look at every env var, plus the
    ALL_SECRETS / ALL_VARS JSON the workflow passes, for a Cloudflare-ish name holding a 32-hex id."""
    pools = [dict(os.environ)]
    for k in ("ALL_SECRETS", "ALL_VARS"):
        try:
            pools.append(json.loads(os.environ.get(k) or "{}") or {})
        except ValueError:
            pass
    for pool in pools:
        for name, v in pool.items():
            n = name.upper()
            v = str(v or "").strip()
            if ("CF" in n or "CLOUDFLARE" in n or "ACCOUNT" in n) and re.fullmatch(r"[0-9a-fA-F]{32}", v):
                print(f"   cloudflare: account id found in {name}")
                return v
    return None


def _cf_account(tok):
    """No account-id secret found: ask Cloudflare which account this API token belongs to."""
    if tok in _CF_ACCT:
        return _CF_ACCT[tok]
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/accounts?per_page=5",
                                 headers={"Authorization": f"Bearer {tok}", "User-Agent": "shorts-studio"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            accts = json.loads(r.read()).get("result") or []
    except urllib.error.HTTPError as e:
        raise ImageError(f"no CF account id secret, and /accounts lookup failed: HTTP {e.code} {e.read()[:200]!r}")
    if not accts:
        raise ImageError("no CF account id secret, and the token sees no accounts (add CF_ACCOUNT_ID)")
    _CF_ACCT[tok] = accts[0]["id"]
    print(f"   cloudflare: using account from token ({len(accts)} found)")
    return _CF_ACCT[tok]


def cloudflare(prompt, seed, dest: Path):
    tok = _env(*CF_TOKEN_NAMES)
    if not tok:
        raise ImageError("CF_API_TOKEN not set")
    acct = _env(*CF_ACCOUNT_NAMES) or _cf_account_scan() or _cf_account(tok)
    model = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    res = _post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}",
                {"prompt": prompt, "steps": 8}, {"Authorization": f"Bearer {tok}"})
    img = (res.get("result") or {}).get("image")
    if not img:
        raise ImageError(f"no image: {str(res)[:300]}")
    dest.write_bytes(base64.b64decode(img))
    return dest


def together(prompt, seed, dest: Path):
    key = os.environ.get("TOGETHER_API_KEY")
    if not key:
        raise ImageError("TOGETHER_API_KEY not set")
    res = _post("https://api.together.xyz/v1/images/generations",
                {"model": os.environ.get("TOGETHER_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell-Free"),
                 "prompt": prompt, "width": 1024, "height": 1024, "steps": 4, "n": 1, "seed": seed,
                 "response_format": "b64_json"}, {"Authorization": f"Bearer {key}"})
    dest.write_bytes(base64.b64decode(res["data"][0]["b64_json"]))
    return dest


def pollinations(prompt, seed, dest: Path):
    q = {"width": 1024, "height": 1024, "seed": seed, "nologo": "true", "model": "flux"}
    if os.environ.get("POLLINATIONS_TOKEN"):
        q["token"] = os.environ["POLLINATIONS_TOKEN"]
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=240) as r:
        data = r.read()
    if len(data) < 10_000:
        raise ImageError("pollinations returned no image")
    dest.write_bytes(data)
    return dest


def gemini(prompt, seed, dest: Path):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ImageError("GEMINI_API_KEY not set")
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    res = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                {"contents": [{"parts": [{"text": prompt + " Square 1:1 image."}]}]}, {})
    for part in res.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
        if data:
            dest.write_bytes(base64.b64decode(data))
            return dest
    raise ImageError(f"no image: {str(res)[:300]}")


def mock(prompt, seed, dest: Path):
    from PIL import Image, ImageDraw
    import random
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(40, 200) for _ in range(3))
    c2 = tuple(rnd.randint(40, 200) for _ in range(3))
    im = Image.new("RGB", (1024, 1024))
    d = ImageDraw.Draw(im)
    for y in range(1024):
        t = y / 1023
        d.line([(0, y), (1024, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    d.text((40, 480), prompt[:60], fill="white")
    im.save(dest, "JPEG", quality=90)
    return dest


PROVIDERS = {"cloudflare": cloudflare, "together": together, "pollinations": pollinations,
             "gemini": gemini, "mock": mock}


def generate(prompt: str, seed: int, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    order = ["mock"] if config.MOCK else [p.strip() for p in
                                          os.environ.get("IMAGE_PROVIDERS", "cloudflare,together,pollinations").split(",")
                                          if p.strip()]
    errors = []
    for name in order:
        for attempt in range(2):
            try:
                out = PROVIDERS[name](prompt, seed, dest)
                from PIL import Image
                with Image.open(out) as im:      # normalise: RGB JPEG
                    im.convert("RGB").save(out, "JPEG", quality=92)
                return out
            except Exception as e:
                errors.append(f"{name}: {str(e)[:160]}")
                if "not set" in str(e):
                    break
                time.sleep(6 * (attempt + 1))
    raise ImageError("all image providers failed -> " + " | ".join(errors))
