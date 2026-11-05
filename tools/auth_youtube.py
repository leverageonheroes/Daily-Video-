#!/usr/bin/env python3
"""One-time YouTube login per channel (Codespace-friendly, no local browser needed).

  python tools/auth_youtube.py all                      # print a login link for every channel
  python tools/auth_youtube.py flat4b                   # link for one channel (then paste interactively)
  python tools/auth_youtube.py flat4b "http://localhost:8765/?code=..."   # finish without a prompt

Open the link, PICK THE MATCHING CHANNEL, click Allow, and copy the http://localhost:8765/?... address from the
browser bar (the page itself won't load; that's fine). Saves secrets/youtube_<channel>.json and prints the value
for the GitHub secret YT_TOKEN_<CHANNEL>.
OAuth client: Codespace secrets YT_CLIENT_ID + YT_CLIENT_SECRET, or secrets/client_secret.json.
"""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")   # redirect is plain http://localhost
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google_auth_oauthlib.flow import Flow  # noqa: E402

from pipeline import config  # noqa: E402
from pipeline.youtube import SCOPES, channel_title  # noqa: E402

REDIRECT = "http://localhost:8765/"


def make_flow():
    cid, csecret = os.environ.get("YT_CLIENT_ID", "").strip(), os.environ.get("YT_CLIENT_SECRET", "").strip()
    kw = dict(scopes=SCOPES, redirect_uri=REDIRECT, autogenerate_code_verifier=False)  # stateless: 2 separate runs
    if cid and csecret:
        return Flow.from_client_config({"installed": {
            "client_id": cid, "client_secret": csecret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]}}, **kw)
    secret = ROOT / "secrets" / "client_secret.json"
    if not secret.exists():
        sys.exit("No OAuth client. Set Codespace secrets YT_CLIENT_ID/YT_CLIENT_SECRET or upload secrets/client_secret.json.")
    return Flow.from_client_secrets_file(str(secret), **kw)


def link(channel):
    url, _ = make_flow().authorization_url(access_type="offline", prompt="consent select_account", state=channel)
    return url


def finish(channel, pasted):
    code = parse_qs(urlparse(pasted.strip()).query).get("code", [pasted.strip()])[0]
    flow = make_flow()
    flow.fetch_token(code=code)
    token = flow.credentials.to_json()
    config.SECRETS.mkdir(exist_ok=True)
    out = config.SECRETS / f"youtube_{channel}.json"
    out.write_text(token)
    out.chmod(0o600)
    print(f"Saved {out.relative_to(ROOT)}")
    try:
        print(f"{channel} is connected to YouTube channel: {channel_title(channel)}")
    except Exception as e:
        print("(Could not read channel name:", e, ")")
    print(f"GitHub secret YT_TOKEN_{channel.upper()} = contents of {out.relative_to(ROOT)}")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "all":
        for ch in config.CHANNELS:
            print(f"\n{ch.upper()} -> sign in and pick the '{ch}' YouTube channel:\n{link(ch)}")
        print(f"\nThen finish each one with:  python tools/auth_youtube.py <channel> \"<localhost URL>\"")
        return
    channel = argv[0]
    if len(argv) > 1:
        return finish(channel, argv[1])
    print(f"\nOpen this link and PICK THE YOUTUBE CHANNEL for {channel.upper()}:\n\n{link(channel)}\n")
    finish(channel, input("Paste the http://localhost:8765/?... URL: "))


if __name__ == "__main__":
    main(sys.argv[1:])
