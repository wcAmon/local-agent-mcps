#!/usr/bin/env python3
"""Run YouTube OAuth authentication flow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from youtube_mcp.auth import get_credentials, DEFAULT_TOKEN_FILE

print("=" * 50)
print("YouTube MCP Server - Authentication")
print("=" * 50)
print()
print("A URL will be displayed below.")
print("Copy and open it in your browser to authorize.")
print()

try:
    creds = get_credentials()
    print()
    print("=" * 50)
    print("Authentication successful!")
    print(f"Token saved to: {DEFAULT_TOKEN_FILE}")
    print("=" * 50)
except KeyboardInterrupt:
    print("\nAuthentication cancelled.")
    sys.exit(1)
except Exception as e:
    print(f"\nAuthentication failed: {e}")
    sys.exit(1)
