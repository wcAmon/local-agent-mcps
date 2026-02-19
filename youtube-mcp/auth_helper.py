#!/usr/bin/env python3
"""Non-interactive OAuth helper for youtube-mcp (two-step: auth / token)."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

CREDENTIALS_DIR = Path(__file__).parent / "credentials"
CLIENT_SECRET = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def cmd_auth():
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET), SCOPES, redirect_uri="http://localhost"
    )
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")
    print("After authorizing, copy the full URL from the browser address bar.")
    print(f'Then run: python3 auth_helper.py token "<URL>"')


def cmd_token(redirect_url):
    parsed = urlparse(redirect_url)
    code = parse_qs(parsed.query).get("code")
    if not code:
        print("[ERROR] No authorization code found in URL")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET), SCOPES, redirect_uri="http://localhost"
    )
    flow.fetch_token(code=code[0])
    creds = flow.credentials

    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    os.chmod(TOKEN_FILE, 0o600)

    print(f"[OK] Token saved to: {TOKEN_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 auth_helper.py auth")
        print('  python3 auth_helper.py token "<redirect_url>"')
        sys.exit(1)

    if sys.argv[1] == "auth":
        cmd_auth()
    elif sys.argv[1] == "token" and len(sys.argv) >= 3:
        cmd_token(sys.argv[2])
    else:
        print("[ERROR] Invalid command")
        sys.exit(1)
