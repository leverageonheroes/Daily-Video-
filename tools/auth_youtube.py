#!/usr/bin/env python3
"""One-time YouTube login for a channel. Works inside a Codespace (copy/paste flow, no browser needed here).

  python tools/auth_youtube.py flat4b
  python tools/auth_youtube.py coldhearts

Needs secrets/client_secret.json (Google Cloud -> OAuth client ID -> Desktop app -> Download JSON).
Saves secrets/youtube_<channel>.json and prints the value to paste into the GitHub secret YT_TOKEN_<CHANNEL>.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # redirect is plain http://localhost

from google_auth_oauthlib.flow import Flow  # noqa: E402

from pipeline.youtube import SCOPES, channel_title  # noqa: E402

REDIRECT = "http://localhost:8765/"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    channel = sys.argv[1]
    secret = ROOT / "secrets" / "client_secret.json"
    if not secret.exists():
        sys.exit(f"Missing {secret}. See SETUP.md step 3.")
    flow = Flow.from_client_secrets_file(str(secret), scopes=SCOPES, redirect_uri=REDIRECT)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent select_account")
    print("\n1) Open this link, sign in, and PICK THE YOUTUBE CHANNEL for", channel.upper(), ":\n")
    print(url)
    print("\n2) After you click Allow, the browser goes to a localhost page that may not load. That's fine.")
    print("   Copy the FULL address from the browser's address bar and paste it here.\n")
    resp = input("Paste the localhost URL: ").strip()
    flow.fetch_token(authorization_response=resp)
    token = flow.credentials.to_json()
    out = ROOT / "secrets" / f"youtube_{channel}.json"
    out.write_text(token)
    print(f"\nSaved {out}")
    try:
        print("Connected to YouTube channel:", channel_title(channel))
    except Exception as e:
        print("(Could not read channel name:", e, ")")
    print(f"\nFor GitHub Actions, create a repository secret named YT_TOKEN_{channel.upper()} with this value:\n")
    print(token)


if __name__ == "__main__":
    main()
