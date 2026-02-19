# YouTube MCP Server

MCP server for managing YouTube channels via Claude Code. Supports video upload, channel management, analytics, comments, playlists, captions, and search.

## Prerequisites

- Python 3.10+
- A Google Cloud project with **YouTube Data API v3** and **YouTube Analytics API** enabled
- An OAuth 2.0 Client ID (Desktop / Installed app type)

## Setup

### 1. Create a virtual environment and install

```bash
python3 -m venv venv
venv/bin/pip install -e .
```

### 2. Add your OAuth client secret

Download your OAuth 2.0 client secret JSON from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and save it as:

```
credentials/client_secret.json
```

The file should look like:

```json
{
  "installed": {
    "client_id": "xxxxx.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "GOCSPX-xxxxx",
    "redirect_uris": ["http://localhost"]
  }
}
```

### 3. Authenticate

The included `auth_helper.py` provides a two-step, non-interactive OAuth flow suitable for headless/remote servers.

**Step 1 -- Generate the authorization URL:**

```bash
venv/bin/python3 auth_helper.py auth
```

This prints a URL. Open it in your local browser and sign in with the Google account that owns your YouTube channel.

**Step 2 -- After authorizing, Google redirects to `http://localhost/?code=...&scope=...`.**

The page will show a connection error (this is expected). Copy the **full URL** from the browser address bar, then run:

```bash
venv/bin/python3 auth_helper.py token "<paste the full redirect URL here>"
```

On success, the token is saved to `credentials/token.json`. The token auto-refreshes; you only need to do this once.

### 4. Verify (optional)

```bash
venv/bin/youtube-mcp
```

The server starts in stdio mode (no output = success). Press `Ctrl+C` to stop.

## Claude Code integration

Add the following to `~/.claude/settings.json` (adjust paths to match your setup):

```json
{
  "mcpServers": {
    "youtube-mcp": {
      "command": "<path-to-venv>/bin/youtube-mcp",
      "cwd": "<path-to-youtube-mcp>"
    }
  }
}
```

Restart Claude Code to load the new MCP server.

## Available tools

| Category | Tools |
|----------|-------|
| **Upload** | `youtube_upload_video`, `youtube_set_thumbnail` |
| **Manage** | `youtube_update_video`, `youtube_list_videos`, `youtube_get_video`, `youtube_delete_video`, `youtube_set_video_localization` |
| **Analytics** | `youtube_get_channel_stats`, `youtube_get_video_analytics`, `youtube_get_audience_retention`, `youtube_get_traffic_sources`, `youtube_get_demographics`, `youtube_get_top_videos`, `youtube_get_revenue_report`, `youtube_get_device_analytics`, `youtube_get_playback_locations`, `youtube_get_content_performance` |
| **Comments** | `youtube_list_comments`, `youtube_reply_to_comment`, `youtube_get_comment_replies`, `youtube_post_comment`, `youtube_moderate_comment`, `youtube_list_held_comments` |
| **Playlists** | `youtube_list_playlists`, `youtube_create_playlist`, `youtube_update_playlist`, `youtube_delete_playlist`, `youtube_list_playlist_items`, `youtube_add_to_playlist`, `youtube_remove_from_playlist` |
| **Captions** | `youtube_list_captions`, `youtube_upload_caption`, `youtube_update_caption`, `youtube_download_caption`, `youtube_delete_caption` |
| **Search** | `youtube_search` |

## OAuth scopes

This server requests the following scopes:

- `youtube.upload` -- Upload videos
- `youtube` -- Manage account
- `youtube.force-ssl` -- Read/write via SSL
- `youtube.readonly` -- Read-only access
- `yt-analytics.readonly` -- View analytics
- `yt-analytics-monetary.readonly` -- View monetary analytics

## Re-authentication

If your token expires or you need to change accounts:

```bash
venv/bin/python3 auth_helper.py auth
# Then follow the same two-step flow as initial setup
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Missing required parameter: redirect_uri` | Ensure `redirect_uris` in `client_secret.json` includes `"http://localhost"` |
| `No authorization code found in URL` | Make sure you copied the **full** redirect URL including `?code=...&scope=...` |
| Token refresh fails | Re-run `auth_helper.py auth` to get a new token |
| `ModuleNotFoundError` | Make sure you installed with `venv/bin/pip install -e .` |
| MCP server not showing in Claude Code | Restart Claude Code after editing `settings.json` |
