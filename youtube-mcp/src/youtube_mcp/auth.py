"""OAuth 2.0 authentication for YouTube API."""

import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow

# OAuth scopes for YouTube API
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

# Default paths (auth.py -> youtube_mcp -> src -> youtube-mcp -> credentials)
DEFAULT_CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "credentials"
DEFAULT_CLIENT_SECRET = DEFAULT_CREDENTIALS_DIR / "client_secret.json"
DEFAULT_TOKEN_FILE = DEFAULT_CREDENTIALS_DIR / "token.json"


class YouTubeAuth:
    """Handle YouTube API OAuth 2.0 authentication."""

    def __init__(
        self,
        client_secret_path: Optional[Path] = None,
        token_path: Optional[Path] = None,
    ):
        """Initialize authentication handler.

        Args:
            client_secret_path: Path to OAuth client secret JSON file
            token_path: Path to store/load token
        """
        self.client_secret_path = client_secret_path or DEFAULT_CLIENT_SECRET
        self.token_path = token_path or DEFAULT_TOKEN_FILE
        self._credentials: Optional[Credentials] = None

    def get_credentials(self) -> Credentials:
        """Get valid credentials, refreshing or re-authenticating if necessary.

        Returns:
            Valid Google OAuth credentials

        Raises:
            FileNotFoundError: If client_secret.json is not found
            RuntimeError: If authentication fails
        """
        if self._credentials and self._credentials.valid and self._has_required_scopes(self._credentials):
            return self._credentials

        # Try to load existing token
        if self.token_path.exists():
            self._credentials = self._load_token()

            if self._credentials and self._credentials.valid and self._has_required_scopes(self._credentials):
                return self._credentials

            # Try to refresh expired credentials
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                try:
                    self._credentials.refresh(Request())
                    self._save_token(self._credentials)
                    if self._has_required_scopes(self._credentials):
                        return self._credentials
                    # Token refreshed but missing scopes, need re-auth
                except Exception:
                    # Refresh failed, need to re-authenticate
                    pass

        # Need to authenticate from scratch
        self._credentials = self._authenticate()
        return self._credentials

    def _has_required_scopes(self, credentials: Credentials) -> bool:
        """Check if credentials have all required scopes.

        Returns:
            True if all SCOPES are present in credentials
        """
        if not credentials.scopes:
            return False
        return set(SCOPES).issubset(set(credentials.scopes))

    def _authenticate(self) -> Credentials:
        """Run OAuth flow to get new credentials.

        Returns:
            New OAuth credentials

        Raises:
            FileNotFoundError: If client_secret.json is not found
        """
        if not self.client_secret_path.exists():
            raise FileNotFoundError(
                f"OAuth client secret not found at {self.client_secret_path}. "
                "Please download it from Google Cloud Console and place it there."
            )

        # Detect credential type (web or installed)
        with open(self.client_secret_path, "r") as f:
            client_config = json.load(f)

        if "web" in client_config:
            # Web credentials - need to set redirect URI for local server
            flow = Flow.from_client_secrets_file(
                str(self.client_secret_path),
                scopes=SCOPES,
                redirect_uri="http://localhost:8080/",
            )
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(prompt="consent")
            print(f"\nPlease visit this URL to authorize:\n{auth_url}\n")

            # Start local server to receive callback
            import socket
            from urllib.parse import urlparse, parse_qs

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("localhost", 8080))
            sock.listen(1)

            print("Waiting for authorization...")
            conn, _ = sock.accept()
            data = conn.recv(4096).decode("utf-8")

            # Extract authorization code from request
            request_line = data.split("\r\n")[0]
            path = request_line.split(" ")[1]
            query = urlparse(path).query
            params = parse_qs(query)

            # Send response to browser
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>"
            conn.sendall(response.encode())
            conn.close()
            sock.close()

            if "code" in params:
                flow.fetch_token(code=params["code"][0])
                credentials = flow.credentials
            else:
                raise RuntimeError(f"Authorization failed: {params.get('error', ['Unknown error'])[0]}")
        else:
            # Installed (desktop) credentials - use manual code entry for remote/headless
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secret_path),
                scopes=SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob",
            )

            auth_url, _ = flow.authorization_url(prompt="consent")
            print("\n" + "=" * 60)
            print("YouTube MCP Authentication")
            print("=" * 60)
            print("\n1. Open this URL in your browser:\n")
            print(auth_url)
            print("\n2. Authorize the application")
            print("3. Copy the authorization code and paste it below\n")

            code = input("Enter authorization code: ").strip()
            flow.fetch_token(code=code)
            credentials = flow.credentials

        self._save_token(credentials)
        return credentials

    def _load_token(self) -> Optional[Credentials]:
        """Load credentials from token file.

        Returns:
            Loaded credentials or None if file doesn't exist/is invalid
        """
        try:
            with open(self.token_path, "r") as f:
                token_data = json.load(f)

            return Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def _save_token(self, credentials: Credentials) -> None:
        """Save credentials to token file.

        Args:
            credentials: Credentials to save
        """
        # Ensure directory exists
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open(self.token_path, "w") as f:
            json.dump(token_data, f, indent=2)

        # Set restrictive permissions
        os.chmod(self.token_path, 0o600)

    def revoke(self) -> bool:
        """Revoke current credentials.

        Returns:
            True if revocation was successful
        """
        if not self._credentials:
            return False

        try:
            import requests
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": self._credentials.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )

            # Remove token file
            if self.token_path.exists():
                self.token_path.unlink()

            self._credentials = None
            return True
        except Exception:
            return False

    def is_authenticated(self) -> bool:
        """Check if we have valid credentials.

        Returns:
            True if authenticated with valid credentials
        """
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False


# Global auth instance
_auth_instance: Optional[YouTubeAuth] = None


def get_auth() -> YouTubeAuth:
    """Get global auth instance."""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = YouTubeAuth()
    return _auth_instance


def get_credentials() -> Credentials:
    """Get valid credentials from global auth instance."""
    return get_auth().get_credentials()
