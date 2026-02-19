"""YouTube MCP Server - Main entry point."""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import upload, manage, analytics, comments, playlists, captions, search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("youtube-mcp")


def _result_to_text(result: Any) -> str:
    """Convert a result to JSON string."""
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    elif isinstance(result, list):
        return json.dumps(
            [item.model_dump() if hasattr(item, "model_dump") else item for item in result],
            indent=2,
            ensure_ascii=False,
        )
    elif isinstance(result, dict):
        return json.dumps(result, indent=2, ensure_ascii=False)
    else:
        return str(result)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available YouTube tools."""
    return [
        # Upload tools
        Tool(
            name="youtube_upload_video",
            description="Upload a video to YouTube. Supports large files with resumable upload.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the video file to upload",
                    },
                    "title": {
                        "type": "string",
                        "description": "Video title (max 100 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Video description (max 5000 characters)",
                        "default": "",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags for the video",
                        "default": [],
                    },
                    "privacy": {
                        "type": "string",
                        "enum": ["public", "private", "unlisted"],
                        "description": "Privacy status of the video",
                        "default": "private",
                    },
                    "category_id": {
                        "type": "string",
                        "description": "YouTube category ID (default: 22 = People & Blogs)",
                        "default": "22",
                    },
                    "thumbnail_path": {
                        "type": "string",
                        "description": "Optional path to thumbnail image",
                    },
                },
                "required": ["file_path", "title"],
            },
        ),
        Tool(
            name="youtube_set_thumbnail",
            description="Set a custom thumbnail for a video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "thumbnail_path": {
                        "type": "string",
                        "description": "Path to thumbnail image (JPG, PNG, or GIF, max 2MB)",
                    },
                },
                "required": ["video_id", "thumbnail_path"],
            },
        ),
        # Management tools
        Tool(
            name="youtube_get_video",
            description="Get detailed information about a specific video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_list_videos",
            description="List videos from the authenticated user's channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of videos to return (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "order": {
                        "type": "string",
                        "enum": ["date", "rating", "viewCount", "title"],
                        "description": "Sort order",
                        "default": "date",
                    },
                },
            },
        ),
        Tool(
            name="youtube_update_video",
            description="Update video metadata (title, description, tags, privacy).",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags (optional)",
                    },
                    "privacy": {
                        "type": "string",
                        "enum": ["public", "private", "unlisted"],
                        "description": "New privacy status (optional)",
                    },
                    "category_id": {
                        "type": "string",
                        "description": "New category ID (optional)",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_set_video_localization",
            description="Add or update a localized (translated) title and description for a video. Use this to make videos discoverable in other languages. Supports any BCP-47 language code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "language": {
                        "type": "string",
                        "description": "BCP-47 language code (e.g., 'es' for Spanish, 'fr' for French, 'de' for German, 'pt' for Portuguese, 'hi' for Hindi, 'ja' for Japanese, 'tl' for Tagalog)",
                    },
                    "localized_title": {
                        "type": "string",
                        "description": "Translated title (max 100 characters)",
                    },
                    "localized_description": {
                        "type": "string",
                        "description": "Translated description (max 5000 characters)",
                    },
                },
                "required": ["video_id", "language", "localized_title", "localized_description"],
            },
        ),
        Tool(
            name="youtube_delete_video",
            description="Delete a video from YouTube. This action cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID to delete",
                    },
                },
                "required": ["video_id"],
            },
        ),
        # Analytics tools
        Tool(
            name="youtube_channel_stats",
            description="Get channel statistics including subscriber count, total views, and video count.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="youtube_video_analytics",
            description="Get analytics for a specific video including views, watch time, likes, comments, and subscriber changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD), defaults to 28 days ago",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD), defaults to today",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_audience_retention",
            description="Get audience retention data for a video, showing how viewers engage throughout the video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD), defaults to 28 days ago",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD), defaults to today",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_traffic_sources",
            description="Get traffic source breakdown showing where viewers are coming from.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (optional, if omitted gets channel-wide data)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
            },
        ),
        Tool(
            name="youtube_demographics",
            description="Get audience demographics including age, gender, and geographic distribution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
            },
        ),
        Tool(
            name="youtube_top_videos",
            description="Get top performing videos ranked by a specific metric.",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["views", "watchTime", "likes", "comments"],
                        "description": "Metric to sort by",
                        "default": "views",
                    },
                    "period_days": {
                        "type": "integer",
                        "description": "Number of days to analyze",
                        "default": 28,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of videos to return",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="youtube_revenue_report",
            description="Get revenue report including estimated earnings, CPM, and RPM. Requires monetization enabled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
            },
        ),
        # Comments tools
        Tool(
            name="youtube_list_comments",
            description="List top-level comments on a video. Returns comment ID, author, text, likes, and reply count.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of comments to return (1-100)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "order": {
                        "type": "string",
                        "enum": ["time", "relevance"],
                        "description": "Sort order (time=newest, relevance=top)",
                        "default": "time",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_reply_to_comment",
            description="Reply to a YouTube comment. Use list_comments first to get the comment_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {
                        "type": "string",
                        "description": "The comment ID to reply to (from list_comments)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Reply text (max 10000 characters)",
                    },
                },
                "required": ["comment_id", "text"],
            },
        ),
        Tool(
            name="youtube_get_comment_replies",
            description="Get replies to a specific comment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {
                        "type": "string",
                        "description": "The parent comment ID",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of replies to return (1-100)",
                        "default": 20,
                    },
                },
                "required": ["comment_id"],
            },
        ),
        Tool(
            name="youtube_post_comment",
            description="Post a new top-level comment on a video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "text": {
                        "type": "string",
                        "description": "Comment text (max 10000 characters)",
                    },
                },
                "required": ["video_id", "text"],
            },
        ),
        Tool(
            name="youtube_moderate_comment",
            description="Set the moderation status of a comment (publish, hold for review, or reject).",
            inputSchema={
                "type": "object",
                "properties": {
                    "comment_id": {
                        "type": "string",
                        "description": "The comment ID to moderate",
                    },
                    "moderation_status": {
                        "type": "string",
                        "enum": ["published", "heldForReview", "rejected"],
                        "description": "New moderation status",
                        "default": "published",
                    },
                    "ban_author": {
                        "type": "boolean",
                        "description": "Also ban the comment author (only with 'rejected')",
                        "default": False,
                    },
                },
                "required": ["comment_id"],
            },
        ),
        Tool(
            name="youtube_list_held_comments",
            description="List comments held for review on a video or across the channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (optional, omit for all held comments)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of comments to return (1-100)",
                        "default": 20,
                    },
                },
            },
        ),
        # Playlist tools
        Tool(
            name="youtube_list_playlists",
            description="List playlists owned by the authenticated user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of playlists to return (1-50)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="youtube_create_playlist",
            description="Create a new playlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Playlist title (max 150 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Playlist description (max 5000 characters)",
                        "default": "",
                    },
                    "privacy": {
                        "type": "string",
                        "enum": ["public", "private", "unlisted"],
                        "description": "Privacy status",
                        "default": "private",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="youtube_update_playlist",
            description="Update a playlist's title, description, or privacy.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_id": {
                        "type": "string",
                        "description": "YouTube playlist ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description (optional)",
                    },
                    "privacy": {
                        "type": "string",
                        "enum": ["public", "private", "unlisted"],
                        "description": "New privacy status (optional)",
                    },
                },
                "required": ["playlist_id"],
            },
        ),
        Tool(
            name="youtube_delete_playlist",
            description="Delete a playlist. This action cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_id": {
                        "type": "string",
                        "description": "YouTube playlist ID",
                    },
                },
                "required": ["playlist_id"],
            },
        ),
        Tool(
            name="youtube_list_playlist_items",
            description="List items (videos) in a playlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_id": {
                        "type": "string",
                        "description": "YouTube playlist ID",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of items to return (1-50)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["playlist_id"],
            },
        ),
        Tool(
            name="youtube_add_to_playlist",
            description="Add a video to a playlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_id": {
                        "type": "string",
                        "description": "YouTube playlist ID",
                    },
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID to add",
                    },
                    "position": {
                        "type": "integer",
                        "description": "Position in playlist (0-based, optional — appends if omitted)",
                    },
                },
                "required": ["playlist_id", "video_id"],
            },
        ),
        Tool(
            name="youtube_remove_from_playlist",
            description="Remove an item from a playlist. Use list_playlist_items to get the playlist_item_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_item_id": {
                        "type": "string",
                        "description": "The playlist item ID (from list_playlist_items)",
                    },
                },
                "required": ["playlist_item_id"],
            },
        ),
        # Caption tools
        Tool(
            name="youtube_list_captions",
            description="List caption tracks for a video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                },
                "required": ["video_id"],
            },
        ),
        Tool(
            name="youtube_upload_caption",
            description="Upload a caption track for a video. Provide caption content via body (raw text) or file_path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID",
                    },
                    "language": {
                        "type": "string",
                        "description": "BCP-47 language code (e.g., 'en', 'es', 'fr')",
                    },
                    "name": {
                        "type": "string",
                        "description": "Caption track name (e.g., 'English CC')",
                        "default": "",
                    },
                    "body": {
                        "type": "string",
                        "description": "Caption content as string (SRT, SBV, or VTT format)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to caption file (alternative to body)",
                    },
                    "is_draft": {
                        "type": "boolean",
                        "description": "Whether the caption is a draft",
                        "default": False,
                    },
                },
                "required": ["video_id", "language"],
            },
        ),
        Tool(
            name="youtube_update_caption",
            description="Update an existing caption track's metadata or content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "caption_id": {
                        "type": "string",
                        "description": "Caption track ID",
                    },
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (for reference)",
                        "default": "",
                    },
                    "name": {
                        "type": "string",
                        "description": "New caption track name (optional)",
                    },
                    "is_draft": {
                        "type": "boolean",
                        "description": "New draft status (optional)",
                    },
                    "body": {
                        "type": "string",
                        "description": "New caption content (optional)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to new caption file (optional)",
                    },
                },
                "required": ["caption_id"],
            },
        ),
        Tool(
            name="youtube_download_caption",
            description="Download a caption track's content as text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "caption_id": {
                        "type": "string",
                        "description": "Caption track ID",
                    },
                    "fmt": {
                        "type": "string",
                        "enum": ["srt", "sbv", "vtt"],
                        "description": "Download format",
                        "default": "srt",
                    },
                },
                "required": ["caption_id"],
            },
        ),
        Tool(
            name="youtube_delete_caption",
            description="Delete a caption track.",
            inputSchema={
                "type": "object",
                "properties": {
                    "caption_id": {
                        "type": "string",
                        "description": "Caption track ID",
                    },
                },
                "required": ["caption_id"],
            },
        ),
        # Search tools
        Tool(
            name="youtube_search",
            description="Search YouTube for videos, channels, or playlists. Note: each call costs 100 API quota units.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["video", "channel", "playlist"],
                        "description": "Type of results to return",
                        "default": "video",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "order": {
                        "type": "string",
                        "enum": ["relevance", "date", "viewCount", "rating"],
                        "description": "Sort order",
                        "default": "relevance",
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "Restrict to a specific channel (optional)",
                    },
                    "published_after": {
                        "type": "string",
                        "description": "Filter by publish date (RFC 3339, e.g. '2024-01-01T00:00:00Z')",
                    },
                    "published_before": {
                        "type": "string",
                        "description": "Filter by publish date (RFC 3339)",
                    },
                },
                "required": ["query"],
            },
        ),
        # Extended analytics tools
        Tool(
            name="youtube_device_analytics",
            description="Get analytics breakdown by device type (mobile, desktop, tablet, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (optional, omit for channel-wide data)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
            },
        ),
        Tool(
            name="youtube_playback_locations",
            description="Get analytics by playback location (YouTube watch page, embedded, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID (optional, omit for channel-wide data)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
            },
        ),
        Tool(
            name="youtube_content_performance",
            description="Get detailed performance metrics (views, watch time, likes, comments, shares, subscribers) for each video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of videos to return (1-50)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        result = None

        # Upload tools
        if name == "youtube_upload_video":
            result = upload.upload_video(
                file_path=arguments["file_path"],
                title=arguments["title"],
                description=arguments.get("description", ""),
                tags=arguments.get("tags", []),
                privacy=arguments.get("privacy", "private"),
                category_id=arguments.get("category_id", "22"),
                thumbnail_path=arguments.get("thumbnail_path"),
            )
        elif name == "youtube_set_thumbnail":
            result = upload.set_thumbnail(
                video_id=arguments["video_id"],
                thumbnail_path=arguments["thumbnail_path"],
            )

        # Management tools
        elif name == "youtube_get_video":
            result = manage.get_video(video_id=arguments["video_id"])
        elif name == "youtube_list_videos":
            result = manage.list_videos(
                max_results=arguments.get("max_results", 10),
                order=arguments.get("order", "date"),
            )
        elif name == "youtube_update_video":
            result = manage.update_video(
                video_id=arguments["video_id"],
                title=arguments.get("title"),
                description=arguments.get("description"),
                tags=arguments.get("tags"),
                privacy=arguments.get("privacy"),
                category_id=arguments.get("category_id"),
            )
        elif name == "youtube_set_video_localization":
            result = manage.set_video_localization(
                video_id=arguments["video_id"],
                language=arguments["language"],
                localized_title=arguments["localized_title"],
                localized_description=arguments["localized_description"],
            )
        elif name == "youtube_delete_video":
            result = manage.delete_video(video_id=arguments["video_id"])

        # Analytics tools
        elif name == "youtube_channel_stats":
            result = analytics.get_channel_stats()
        elif name == "youtube_video_analytics":
            result = analytics.get_video_analytics(
                video_id=arguments["video_id"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_audience_retention":
            result = analytics.get_audience_retention(
                video_id=arguments["video_id"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_traffic_sources":
            result = analytics.get_traffic_sources(
                video_id=arguments.get("video_id"),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_demographics":
            result = analytics.get_demographics(
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_top_videos":
            result = analytics.get_top_videos(
                metric=arguments.get("metric", "views"),
                period_days=arguments.get("period_days", 28),
                limit=arguments.get("limit", 10),
            )
        elif name == "youtube_revenue_report":
            result = analytics.get_revenue_report(
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )

        # Comments tools
        elif name == "youtube_list_comments":
            result = comments.list_comments(
                video_id=arguments["video_id"],
                max_results=arguments.get("max_results", 20),
                order=arguments.get("order", "time"),
            )
        elif name == "youtube_reply_to_comment":
            result = comments.reply_to_comment(
                comment_id=arguments["comment_id"],
                text=arguments["text"],
            )
        elif name == "youtube_get_comment_replies":
            result = comments.get_comment_replies(
                comment_id=arguments["comment_id"],
                max_results=arguments.get("max_results", 20),
            )
        elif name == "youtube_post_comment":
            result = comments.post_comment(
                video_id=arguments["video_id"],
                text=arguments["text"],
            )
        elif name == "youtube_moderate_comment":
            result = comments.moderate_comment(
                comment_id=arguments["comment_id"],
                moderation_status=arguments.get("moderation_status", "published"),
                ban_author=arguments.get("ban_author", False),
            )
        elif name == "youtube_list_held_comments":
            result = comments.list_held_comments(
                video_id=arguments.get("video_id"),
                max_results=arguments.get("max_results", 20),
            )

        # Playlist tools
        elif name == "youtube_list_playlists":
            result = playlists.list_playlists(
                max_results=arguments.get("max_results", 25),
            )
        elif name == "youtube_create_playlist":
            result = playlists.create_playlist(
                title=arguments["title"],
                description=arguments.get("description", ""),
                privacy=arguments.get("privacy", "private"),
            )
        elif name == "youtube_update_playlist":
            result = playlists.update_playlist(
                playlist_id=arguments["playlist_id"],
                title=arguments.get("title"),
                description=arguments.get("description"),
                privacy=arguments.get("privacy"),
            )
        elif name == "youtube_delete_playlist":
            result = playlists.delete_playlist(
                playlist_id=arguments["playlist_id"],
            )
        elif name == "youtube_list_playlist_items":
            result = playlists.list_playlist_items(
                playlist_id=arguments["playlist_id"],
                max_results=arguments.get("max_results", 25),
            )
        elif name == "youtube_add_to_playlist":
            result = playlists.add_to_playlist(
                playlist_id=arguments["playlist_id"],
                video_id=arguments["video_id"],
                position=arguments.get("position"),
            )
        elif name == "youtube_remove_from_playlist":
            result = playlists.remove_from_playlist(
                playlist_item_id=arguments["playlist_item_id"],
            )

        # Caption tools
        elif name == "youtube_list_captions":
            result = captions.list_captions(
                video_id=arguments["video_id"],
            )
        elif name == "youtube_upload_caption":
            result = captions.upload_caption(
                video_id=arguments["video_id"],
                language=arguments["language"],
                name=arguments.get("name", ""),
                body=arguments.get("body", ""),
                file_path=arguments.get("file_path"),
                is_draft=arguments.get("is_draft", False),
            )
        elif name == "youtube_update_caption":
            result = captions.update_caption(
                caption_id=arguments["caption_id"],
                video_id=arguments.get("video_id", ""),
                name=arguments.get("name"),
                is_draft=arguments.get("is_draft"),
                body=arguments.get("body"),
                file_path=arguments.get("file_path"),
            )
        elif name == "youtube_download_caption":
            result = captions.download_caption(
                caption_id=arguments["caption_id"],
                fmt=arguments.get("fmt", "srt"),
            )
        elif name == "youtube_delete_caption":
            result = captions.delete_caption(
                caption_id=arguments["caption_id"],
            )

        # Search tools
        elif name == "youtube_search":
            result = search.search(
                query=arguments["query"],
                result_type=arguments.get("type", "video"),
                max_results=arguments.get("max_results", 10),
                order=arguments.get("order", "relevance"),
                channel_id=arguments.get("channel_id"),
                published_after=arguments.get("published_after"),
                published_before=arguments.get("published_before"),
            )

        # Extended analytics tools
        elif name == "youtube_device_analytics":
            result = analytics.get_device_analytics(
                video_id=arguments.get("video_id"),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_playback_locations":
            result = analytics.get_playback_locations(
                video_id=arguments.get("video_id"),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        elif name == "youtube_content_performance":
            result = analytics.get_content_performance(
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                max_results=arguments.get("max_results", 25),
            )
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        return [TextContent(type="text", text=_result_to_text(result))]

    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"File not found: {e}")]
    except ValueError as e:
        return [TextContent(type="text", text=f"Invalid value: {e}")]
    except Exception as e:
        logger.exception(f"Error calling tool {name}")
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


async def run():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Main entry point."""
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
