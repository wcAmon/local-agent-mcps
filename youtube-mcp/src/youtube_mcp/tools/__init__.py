"""YouTube MCP tools."""

from .upload import upload_video, set_thumbnail
from .manage import (
    update_video,
    list_videos,
    get_video,
    delete_video,
    set_video_localization,
)
from .analytics import (
    get_channel_stats,
    get_video_analytics,
    get_audience_retention,
    get_traffic_sources,
    get_demographics,
    get_top_videos,
    get_revenue_report,
    get_device_analytics,
    get_playback_locations,
    get_content_performance,
)
from .comments import (
    list_comments,
    reply_to_comment,
    get_comment_replies,
    post_comment,
    moderate_comment,
    list_held_comments,
)
from .playlists import (
    list_playlists,
    create_playlist,
    update_playlist,
    delete_playlist,
    list_playlist_items,
    add_to_playlist,
    remove_from_playlist,
)
from .captions import (
    list_captions,
    upload_caption,
    update_caption,
    download_caption,
    delete_caption,
)
from .search import search

__all__ = [
    # Upload
    "upload_video",
    "set_thumbnail",
    # Manage
    "update_video",
    "list_videos",
    "get_video",
    "delete_video",
    "set_video_localization",
    # Analytics
    "get_channel_stats",
    "get_video_analytics",
    "get_audience_retention",
    "get_traffic_sources",
    "get_demographics",
    "get_top_videos",
    "get_revenue_report",
    "get_device_analytics",
    "get_playback_locations",
    "get_content_performance",
    # Comments
    "list_comments",
    "reply_to_comment",
    "get_comment_replies",
    "post_comment",
    "moderate_comment",
    "list_held_comments",
    # Playlists
    "list_playlists",
    "create_playlist",
    "update_playlist",
    "delete_playlist",
    "list_playlist_items",
    "add_to_playlist",
    "remove_from_playlist",
    # Captions
    "list_captions",
    "upload_caption",
    "update_caption",
    "download_caption",
    "delete_caption",
    # Search
    "search",
]
